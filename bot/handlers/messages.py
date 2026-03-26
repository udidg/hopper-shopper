"""Message handler — auto-detect grocery lists and understand natural language."""

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.services.formatter import (
    format_help,
    format_items_added,
    format_items_removed,
    format_plain_list,
    format_sorted_list,
)
from bot.services.list_manager import (
    add_items,
    add_items_structured,
    add_items_structured_with_duplicates,
    add_items_with_duplicates,
    clear_list,
    get_list_items,
    get_or_create_active_list,
    get_or_create_user,
    items_to_dicts,
    mark_item_done,
    remove_items,
)
from bot.services.parser import looks_like_grocery_list, parse_items_text
from bot.utils.db import db_session_with_retry

logger = logging.getLogger(__name__)

DB_ERROR_MSG = "❌ שגיאה בגישה למסד הנתונים. נסו שוב."


async def _send_typing(update: Update) -> None:
    """Send typing indicator to show the bot is processing."""
    try:
        if update.effective_chat:
            await update.effective_chat.send_action(ChatAction.TYPING)
    except Exception:
        pass  # Non-critical — don't fail if typing indicator fails


async def _try_intent_understanding(text: str, update: Update) -> dict | None:
    """Try to understand user intent via LLM. Returns None if unavailable."""
    try:
        from bot.services.llm import is_llm_available, understand_intent

        if await is_llm_available():
            await _send_typing(update)
            return await understand_intent(text)
    except Exception:
        logger.debug("Intent understanding failed", exc_info=True)
    return None


async def _try_smart_parse(text: str, update: Update) -> list[dict] | None:
    """Try to parse items via LLM. Returns None if unavailable."""
    try:
        from bot.services.llm import is_llm_available, parse_items_smart

        if await is_llm_available():
            await _send_typing(update)
            return await parse_items_smart(text)
    except Exception:
        logger.debug("Smart parsing failed", exc_info=True)
    return None


async def _get_user_and_list(update: Update, session):
    """Helper: get or create user and active list for the current chat."""
    tg_user = update.effective_user
    chat = update.effective_chat

    if tg_user is None or chat is None:
        raise ValueError("Missing effective_user or effective_chat")

    user = await get_or_create_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        display_name=tg_user.full_name,
    )

    grocery_list = await get_or_create_active_list(
        session,
        chat_id=chat.id,
        user_id=user.id,
    )

    return user, grocery_list


async def _handle_add_action(
    update: Update,
    item_names: list[str] | None = None,
    parsed_items: list[dict] | None = None,
    auto_sort: bool = False,
) -> None:
    """Handle adding items — either from plain names or structured parsed items.

    Args:
        auto_sort: If True and 3+ items are added, automatically show the sorted list.
    """
    if not update.message:
        return

    duplicates: list[str] = []

    try:
        async with db_session_with_retry() as session:
            user, grocery_list = await _get_user_and_list(update, session)
            chat_id = update.effective_chat.id

            if parsed_items:
                result = await add_items_structured_with_duplicates(
                    session,
                    list_id=grocery_list.id,
                    chat_id=chat_id,
                    parsed_items=parsed_items,
                    user_id=user.id,
                )
                added = result.added
                duplicates = result.duplicates
            elif item_names:
                result = await add_items_with_duplicates(
                    session,
                    list_id=grocery_list.id,
                    chat_id=chat_id,
                    item_names=item_names,
                    user_id=user.id,
                )
                added = result.added
                duplicates = result.duplicates
            else:
                return

            added_info = [
                _format_item_info(item) for item in added
            ]

            # If auto_sort and enough items, fetch the full list for sorted display
            sorted_text = None
            if auto_sort and len(added) >= 3:
                all_items = await get_list_items(session, grocery_list.id)
                list_name = grocery_list.name
                sorted_text = format_sorted_list(items_to_dicts(all_items), list_name)
    except Exception:
        logger.exception("Database error adding items")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    # Build response with duplicate info
    response = format_items_added(added_info)
    if duplicates:
        dup_names = ", ".join(duplicates)
        if added_info:
            response += f"\n\n⚠️ כבר ברשימה (דילגתי): {dup_names}"
        else:
            response = f"⚠️ כל הפריטים כבר ברשימה: {dup_names}"

    await update.message.reply_text(response)

    # Auto-show sorted list for bulk additions
    if auto_sort and sorted_text:
        await update.message.reply_text(sorted_text)


def _format_item_info(item) -> dict:
    """Format a GroceryItem into a dict for the formatter."""
    detail_parts = []
    if item.quantity:
        qty_str = item.quantity
        if item.unit:
            qty_str += f" {item.unit}"
        detail_parts.append(qty_str)
    if item.brand:
        detail_parts.append(item.brand)
    if item.description and item.description != item.brand:
        detail_parts.append(item.description)

    return {
        "name": item.name,
        "detail": " | ".join(detail_parts) if detail_parts else item.description,
    }


async def _handle_remove_action(update: Update, item_names: list[str]) -> None:
    """Handle removing items by name."""
    if not item_names or not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            removed = await remove_items(session, grocery_list.id, item_names)
    except Exception:
        logger.exception("Database error removing items")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(format_items_removed(removed))


async def _handle_done_action(update: Update, item_names: list[str]) -> None:
    """Handle marking items as done."""
    if not item_names or not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)

            done_names = []
            for name in item_names:
                item = await mark_item_done(
                    session, grocery_list.id, name.strip()
                )
                if item:
                    done_names.append(item.name)
    except Exception:
        logger.exception("Database error marking items done")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if done_names:
        names_str = ", ".join(done_names)
        await update.message.reply_text(f"✅ {names_str} סומנו כנקנו!")
    else:
        await update.message.reply_text("❌ הפריטים לא נמצאו ברשימה.")


async def _handle_list_action(update: Update) -> None:
    """Handle showing the list."""
    if not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            items = await get_list_items(session, grocery_list.id)
            list_name = grocery_list.name
    except Exception:
        logger.exception("Database error listing items")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(
        format_plain_list(items_to_dicts(items), list_name)
    )


async def _handle_sort_action(update: Update) -> None:
    """Handle showing the sorted list."""
    if not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            items = await get_list_items(session, grocery_list.id)
            list_name = grocery_list.name
    except Exception:
        logger.exception("Database error sorting items")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(
        format_sorted_list(items_to_dicts(items), list_name)
    )


async def _handle_clear_action(update: Update) -> None:
    """Handle clearing the list."""
    if not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            count = await clear_list(session, grocery_list.id)
    except Exception:
        logger.exception("Database error clearing list")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if count > 0:
        await update.message.reply_text(f"🗑️ הרשימה נוקתה! ({count} פריטים הוסרו)")
    else:
        await update.message.reply_text("📝 הרשימה כבר ריקה!")


async def _handle_help_action(update: Update) -> None:
    """Handle help request."""
    if not update.message:
        return

    await update.message.reply_text(format_help())


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle plain text messages.

    Pipeline:
    1. Try LLM intent understanding (natural language commands)
    2. If intent is "add" or looks like a grocery list, try LLM smart parsing
    3. Fall back to regex-based parsing
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text

    # Skip commands
    if text.startswith("/"):
        return

    # ── Step 1: Try LLM intent understanding ──────────────────────
    intent = await _try_intent_understanding(text, update)

    if intent and intent["action"] != "unknown":
        action = intent["action"]
        items = intent.get("items", [])

        if action == "add" and items:
            # For add intents, try smart parsing on the original text
            # to extract quantity/unit/brand
            parsed = await _try_smart_parse(text, update)
            if parsed:
                await _handle_add_action(update, parsed_items=parsed)
            else:
                await _handle_add_action(update, item_names=items)
            return

        if action == "remove" and items:
            await _handle_remove_action(update, items)
            return

        if action == "done" and items:
            await _handle_done_action(update, items)
            return

        if action == "list":
            await _handle_list_action(update)
            return

        if action == "sort":
            await _handle_sort_action(update)
            return

        if action == "clear":
            await _handle_clear_action(update)
            return

        if action == "help":
            await _handle_help_action(update)
            return

    # ── Step 2: Check if it looks like a grocery list ─────────────
    if not looks_like_grocery_list(text):
        return

    # ── Step 3: Try LLM smart parsing ────────────────────────────
    parsed_items = await _try_smart_parse(text, update)
    if parsed_items and len(parsed_items) >= 1:
        await _handle_add_action(update, parsed_items=parsed_items, auto_sort=True)
        return

    # ── Step 4: Fall back to regex parsing ────────────────────────
    item_names = parse_items_text(text)
    if not item_names or len(item_names) < 2:
        return

    await _handle_add_action(update, item_names=item_names, auto_sort=True)
