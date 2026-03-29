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
    update_item_details,
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


async def _try_intent_understanding(
    text: str,
    update: Update,
    list_item_names: list[str] | None = None,
) -> dict | None:
    """Try to understand user intent via LLM.

    If list_item_names is provided, uses context-aware intent understanding
    so the LLM can recognize references to existing items.

    Returns None if unavailable.
    """
    try:
        from bot.services.llm import (
            is_llm_available,
            understand_intent,
            understand_intent_with_context,
        )

        if await is_llm_available():
            await _send_typing(update)
            if list_item_names:
                return await understand_intent_with_context(text, list_item_names)
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
    """Format a GroceryItem into a dict for the formatter.

    Uses format_item_detail with 'inline' style for consistent detail display.
    Returns a dict with 'name' and 'detail' keys for format_items_added().
    """
    from bot.services.formatter import format_item_detail

    item_dict = {
        "name": item.name,
        "brand": item.brand,
        "quantity": item.quantity,
        "unit": item.unit,
        "description": item.description,
    }
    # format_item_detail returns "name (details)" — extract just the detail part
    inline = format_item_detail(item_dict, style="inline")
    # If there are parenthesized details, extract them; otherwise no detail
    if "(" in inline and inline.endswith(")"):
        detail = inline[inline.index("(") + 1 : -1]
    else:
        detail = None

    return {
        "name": item.name,
        "detail": detail,
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


async def _handle_update_action(update: Update, items: list[dict]) -> None:
    """Handle updating details on existing items in the list.

    Each item in the list is a dict with 'name' and optional
    'brand', 'quantity', 'unit', 'detail' fields.
    """
    if not items or not update.message:
        return

    updated_names: list[str] = []
    not_found_names: list[str] = []

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            chat_id = update.effective_chat.id

            for item_info in items:
                name = item_info.get("name", "").strip()
                if not name:
                    continue

                updated = await update_item_details(
                    session,
                    list_id=grocery_list.id,
                    chat_id=chat_id,
                    item_name=name,
                    brand=item_info.get("brand"),
                    quantity=item_info.get("quantity"),
                    unit=item_info.get("unit"),
                    detail=item_info.get("detail"),
                )

                if updated:
                    # Build a summary of what was updated
                    parts = [updated.name]
                    if item_info.get("brand"):
                        parts.append(f"🏷️ {item_info['brand']}")
                    if item_info.get("quantity"):
                        qty = item_info["quantity"]
                        if item_info.get("unit"):
                            qty += f" {item_info['unit']}"
                        parts.append(f"📏 {qty}")
                    if item_info.get("detail"):
                        parts.append(f"📝 {item_info['detail']}")
                    updated_names.append(" — ".join(parts))
                else:
                    not_found_names.append(name)
    except Exception:
        logger.exception("Database error updating items")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    response_parts: list[str] = []
    if updated_names:
        if len(updated_names) == 1:
            response_parts.append(f"✏️ עודכן: {updated_names[0]}")
        else:
            items_text = "\n".join(f"  • {n}" for n in updated_names)
            response_parts.append(f"✏️ {len(updated_names)} פריטים עודכנו:\n{items_text}")

    if not_found_names:
        names_str = ", ".join(not_found_names)
        response_parts.append(f"❌ לא נמצאו ברשימה: {names_str}")

    if response_parts:
        await update.message.reply_text("\n\n".join(response_parts))


async def _get_list_item_names_for_context(update: Update) -> list[str]:
    """Fetch current list item names for LLM context. Returns empty list on failure."""
    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            items = await get_list_items(session, grocery_list.id)
            return [item.name for item in items if not item.is_done]
    except Exception:
        logger.debug("Failed to fetch list items for context", exc_info=True)
        return []


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle plain text messages.

    Pipeline:
    1. Fetch current list items for LLM context
    2. Try LLM intent understanding with list context
    3. Handle recognized intents (add, remove, done, update, list, sort, clear, help)
    4. Silently ignore chat/unknown intents
    5. Fall back to heuristic grocery list detection + regex parsing
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text

    # Skip commands
    if text.startswith("/"):
        return

    # ── Step 1: Fetch current list items for context ──────────────
    list_item_names = await _get_list_item_names_for_context(update)

    # ── Step 2: Try LLM intent understanding (with list context) ──
    intent = await _try_intent_understanding(text, update, list_item_names)

    if intent and intent["action"] not in ("unknown", "chat"):
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

        if action == "update" and items:
            await _handle_update_action(update, items)
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

    # If LLM recognized it as chat or unknown, silently ignore
    if intent and intent["action"] in ("chat", "unknown"):
        return

    # ── Step 3: Check if it looks like a grocery list ─────────────
    if not looks_like_grocery_list(text):
        return

    # ── Step 4: Try LLM smart parsing ────────────────────────────
    parsed_items = await _try_smart_parse(text, update)
    if parsed_items and len(parsed_items) >= 1:
        await _handle_add_action(update, parsed_items=parsed_items, auto_sort=True)
        return

    # ── Step 5: Fall back to regex parsing ────────────────────────
    item_names = parse_items_text(text)
    if not item_names or len(item_names) < 2:
        return

    await _handle_add_action(update, item_names=item_names, auto_sort=True)
