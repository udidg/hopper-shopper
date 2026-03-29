"""Command handlers for the Hopper Shopper bot.

Handles: /start, /help, /add, /remove, /clear, /cleardone, /done, /undone, /list, /sort, /price, /detail
"""

import logging

from sqlalchemy import select, and_
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from bot.models.grocery_item import GroceryItem
from bot.models.item_history import ItemHistory
from bot.services.formatter import (
    format_help,
    format_items_added,
    format_items_removed,
    format_plain_list,
    format_sorted_list,
)
from bot.services.list_manager import (
    add_items,
    clear_list,
    get_list_items,
    get_or_create_active_list,
    get_or_create_user,
    items_to_dicts,
    mark_item_done,
    remove_items,
    set_item_detail,
    set_item_price,
)
from bot.services.parser import parse_items_text
from bot.utils.db import db_session_with_retry

logger = logging.getLogger(__name__)

DB_ERROR_MSG = "❌ שגיאה בגישה למסד הנתונים. נסו שוב."


def _extract_args(text: str) -> str:
    """Extract command arguments, handling bot username suffix in groups.

    E.g. '/add@MyBot חלב' → 'חלב'
    """
    parts = text.split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


async def _get_user_and_list(update: Update, session):
    """Helper: get or create user and active list for the current chat.

    Returns (user, grocery_list) or raises if effective_user/chat is None.
    """
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


# ── /start ───────────────────────────────────────────────────────


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    if not update.message:
        return

    await update.message.reply_text(
        "🛒 ברוכים הבאים ל-Hopper Shopper!\n\n"
        "אני בוט לניהול רשימות קניות.\n"
        "הוסיפו אותי לקבוצה ותתחילו לנהל רשימות קניות משותפות!\n\n"
        "שלחו /help לרשימת הפקודות.",
    )


# ── /help ────────────────────────────────────────────────────────


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show available commands."""
    if not update.message:
        return

    await update.message.reply_text(format_help())


# ── /add ─────────────────────────────────────────────────────────


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add — add items to the grocery list."""
    if not update.message or not update.message.text:
        return

    items_text = _extract_args(update.message.text)

    if not items_text.strip():
        await update.message.reply_text(
            "🛒 כדי להוסיף פריטים, כתבו אחרי הפקודה:\n\n"
            "/add חלב, לחם, ביצים\n\n"
            "או שלחו רשימה כטקסט חופשי (פריט בכל שורה).",
        )
        return

    item_names = parse_items_text(items_text)
    if not item_names:
        await update.message.reply_text("❌ לא הצלחתי לזהות פריטים בהודעה.")
        return

    # Show typing indicator while classifying items (may involve LLM)
    try:
        await update.effective_chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    try:
        async with db_session_with_retry() as session:
            user, grocery_list = await _get_user_and_list(update, session)
            added = await add_items(
                session,
                list_id=grocery_list.id,
                chat_id=update.effective_chat.id,
                item_names=item_names,
                user_id=user.id,
            )
            added_info = [
                {"name": item.name, "detail": item.description}
                for item in added
            ]
    except Exception:
        logger.exception("Database error in /add")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(format_items_added(added_info))


# ── /remove ──────────────────────────────────────────────────────


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /remove — remove items from the grocery list."""
    if not update.message or not update.message.text:
        return

    items_text = _extract_args(update.message.text)

    if not items_text.strip():
        await update.message.reply_text(
            "🗑️ כדי להסיר פריט, כתבו אחרי הפקודה:\n\n"
            "/remove חלב",
        )
        return

    item_names = parse_items_text(items_text)

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            removed = await remove_items(session, grocery_list.id, item_names)
    except Exception:
        logger.exception("Database error in /remove")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(format_items_removed(removed))


# ── /clear ───────────────────────────────────────────────────────


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — ask for confirmation before clearing the entire grocery list."""
    if not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            items = await get_list_items(session, grocery_list.id)
    except Exception:
        logger.exception("Database error in /clear")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if not items:
        await update.message.reply_text("📝 הרשימה כבר ריקה!")
        return

    pending = sum(1 for i in items if not i.is_done)
    done = sum(1 for i in items if i.is_done)

    keyboard = [
        [
            InlineKeyboardButton("✅ כן, מחק הכל", callback_data="clear:all:confirm"),
            InlineKeyboardButton("❌ ביטול", callback_data="clear:cancel:0"),
        ]
    ]
    # If there are done items, offer to clear only those
    if done > 0 and pending > 0:
        keyboard.insert(0, [
            InlineKeyboardButton(
                f"🧹 מחק רק נקנו ({done})",
                callback_data="clear:done:confirm",
            ),
        ])

    await update.message.reply_text(
        f"🗑️ למחוק את הרשימה?\n\n"
        f"📊 {len(items)} פריטים ({pending} ממתינים, {done} נקנו)",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def cleardone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cleardone — clear only purchased items from the grocery list."""
    if not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            count = await clear_list(session, grocery_list.id, done_only=True)
    except Exception:
        logger.exception("Database error in /cleardone")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if count > 0:
        await update.message.reply_text(f"🧹 {count} פריטים שנקנו הוסרו מהרשימה!")
    else:
        await update.message.reply_text("✅ אין פריטים שנקנו להסרה.")


# ── /done ────────────────────────────────────────────────────────


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /done — mark an item as purchased."""
    if not update.message or not update.message.text:
        return

    item_name = _extract_args(update.message.text)

    if not item_name.strip():
        await update.message.reply_text(
            "✅ כדי לסמן פריט כנקנה, כתבו אחרי הפקודה:\n\n"
            "/done חלב",
        )
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            item = await mark_item_done(session, grocery_list.id, item_name.strip())
            result_name = item.name if item else None
    except Exception:
        logger.exception("Database error in /done")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if result_name:
        await update.message.reply_text(f"✅ {result_name} סומן כנקנה!")
    else:
        await update.message.reply_text(f"❌ הפריט '{item_name.strip()}' לא נמצא ברשימה.")


# ── /undone ──────────────────────────────────────────────────────


async def undone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /undone — unmark an item as purchased."""
    if not update.message or not update.message.text:
        return

    item_name = _extract_args(update.message.text)

    if not item_name.strip():
        await update.message.reply_text(
            "↩️ כדי לבטל סימון פריט, כתבו אחרי הפקודה:\n\n"
            "/undone חלב",
        )
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            item = await mark_item_done(
                session, grocery_list.id, item_name.strip(), done=False
            )
            result_name = item.name if item else None
    except Exception:
        logger.exception("Database error in /undone")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if result_name:
        await update.message.reply_text(f"↩️ {result_name} הוחזר לרשימה.")
    else:
        await update.message.reply_text(f"❌ הפריט '{item_name.strip()}' לא נמצא ברשימה.")


# ── /list ────────────────────────────────────────────────────────


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list — show the current grocery list (unsorted).

    If the list is empty, shows quick-add suggestions from item history.
    """
    if not update.message:
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            items = await get_list_items(session, grocery_list.id)
            list_name = grocery_list.name

            # If list is empty, fetch top items from history for quick-add
            frequent_items: list[str] = []
            if not items and update.effective_chat:
                history_result = await session.execute(
                    select(ItemHistory.name)
                    .where(ItemHistory.chat_id == update.effective_chat.id)
                    .order_by(ItemHistory.times_added.desc())
                    .limit(8)
                )
                frequent_items = [row[0] for row in history_result.fetchall()]
    except Exception:
        logger.exception("Database error in /list")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if not items and frequent_items:
        # Empty state with quick-add buttons from history
        keyboard = []
        # Arrange in rows of 2 buttons
        for i in range(0, len(frequent_items), 2):
            row = []
            for name in frequent_items[i:i + 2]:
                row.append(
                    InlineKeyboardButton(
                        f"➕ {name}",
                        callback_data=f"qa:{name[:50]}",
                    )
                )
            keyboard.append(row)

        await update.message.reply_text(
            "📝 הרשימה ריקה!\n\n"
            "🕐 פריטים שאתם בדרך כלל קונים:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Build action buttons for non-empty lists
    keyboard = _build_list_action_buttons(items)

    await update.message.reply_text(
        format_plain_list(items_to_dicts(items), list_name),
        reply_markup=keyboard,
    )


# ── /sort ────────────────────────────────────────────────────────


async def sort_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sort — show the grocery list sorted by department."""
    if not update.message:
        return

    # Show typing indicator while sorting (may involve LLM classification)
    try:
        await update.effective_chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            items = await get_list_items(session, grocery_list.id)
            list_name = grocery_list.name
    except Exception:
        logger.exception("Database error in /sort")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    # Build action buttons for non-empty lists
    keyboard = _build_list_action_buttons(items)

    await update.message.reply_text(
        format_sorted_list(items_to_dicts(items), list_name),
        reply_markup=keyboard,
    )


# ── /price ───────────────────────────────────────────────────────


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /price — set price for an item. Usage: /price חלב 7.90"""
    if not update.message or not update.message.text:
        return

    text = update.message.text
    parts = text.split(maxsplit=2)

    if len(parts) < 3:
        await update.message.reply_text(
            "💰 כדי לעדכן מחיר, כתבו:\n\n"
            "/price חלב 7.90",
        )
        return

    item_name = parts[1]
    try:
        price = float(parts[2])
    except ValueError:
        await update.message.reply_text("❌ מחיר לא תקין. נא להזין מספר.")
        return

    try:
        async with db_session_with_retry() as session:
            _, grocery_list = await _get_user_and_list(update, session)
            item = await set_item_price(session, grocery_list.id, item_name, price)
            result_name = item.name if item else None
    except Exception:
        logger.exception("Database error in /price")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if result_name:
        await update.message.reply_text(f"💰 מחיר {result_name} עודכן ל-₪{price:.2f}")
    else:
        await update.message.reply_text(f"❌ הפריט '{item_name}' לא נמצא ברשימה.")


# ── /detail ──────────────────────────────────────────────────────


async def detail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /detail — save a default detail/brand for an item.

    Two modes:
      1. Guided: ``/detail`` (no args) — shows item picker with inline buttons
      2. Direct: ``/detail תפוחי אדמה של דוד משה`` — saves detail directly

    The guided flow shows the current list items as buttons. Tapping one
    shows the item's current details and prompts for new ones.
    """
    if not update.message or not update.message.text:
        return

    args = _extract_args(update.message.text)

    if not args.strip():
        # Guided flow: show item picker
        await _detail_guided_flow(update, context)
        return

    # Direct flow: parse item name + detail from args
    parts = args.strip()

    # Try to find the item name by checking history
    try:
        async with db_session_with_retry() as session:
            chat_id = update.effective_chat.id

            # Strategy: try progressively shorter prefixes as item name
            words = parts.split()
            item_name = None
            detail = None

            for i in range(len(words) - 1, 0, -1):
                candidate_name = " ".join(words[:i])
                candidate_detail = " ".join(words[i:])

                active_list = await get_or_create_active_list(session, chat_id)

                # Check active list
                result = await session.execute(
                    select(GroceryItem).where(
                        and_(
                            GroceryItem.list_id == active_list.id,
                            GroceryItem.name.ilike(candidate_name),
                        )
                    )
                )
                if result.scalar_one_or_none():
                    item_name = candidate_name
                    detail = candidate_detail
                    break

                # Check history
                result = await session.execute(
                    select(ItemHistory).where(
                        and_(
                            ItemHistory.chat_id == chat_id,
                            ItemHistory.name.ilike(candidate_name),
                        )
                    )
                )
                if result.scalar_one_or_none():
                    item_name = candidate_name
                    detail = candidate_detail
                    break

            # Fallback: first word = item, rest = detail
            if item_name is None:
                item_name = words[0]
                detail = " ".join(words[1:]) if len(words) > 1 else None

            if not detail:
                await update.message.reply_text(
                    "❌ נא לציין גם פריט וגם פרטים.\n"
                    "דוגמה: /detail תפוחי אדמה של דוד משה",
                )
                return

            await set_item_detail(session, chat_id, item_name, detail)
    except Exception:
        logger.exception("Database error in /detail")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(
        f"📝 פרטים נשמרו!\n"
        f"פריט: {item_name}\n"
        f"פרטים: {detail}\n\n"
        f"מעכשיו כשתוסיפו '{item_name}' הפרטים יופיעו אוטומטית.",
    )


async def _detail_guided_flow(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the current list items as inline buttons for detail editing.

    When the user taps an item, the detail card is shown via the
    ``dt:pick:{item_id}`` callback (handled in callbacks.py).
    """
    try:
        async with db_session_with_retry() as session:
            tg_user = update.effective_user
            chat = update.effective_chat

            if tg_user is None or chat is None:
                return

            user = await get_or_create_user(
                session,
                telegram_id=tg_user.id,
                username=tg_user.username,
                display_name=tg_user.full_name,
            )

            grocery_list = await get_or_create_active_list(
                session, chat_id=chat.id, user_id=user.id
            )

            items = await get_list_items(session, grocery_list.id)
    except Exception:
        logger.exception("Database error in /detail guided flow")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if not items:
        await update.message.reply_text(
            "📝 הרשימה ריקה!\n\n"
            "הוסיפו פריטים עם /add ואז השתמשו ב-/detail כדי לערוך פרטים.",
        )
        return

    # Build item picker keyboard
    keyboard: list[list[InlineKeyboardButton]] = []
    for item in items:
        label = item.name
        if item.description:
            label += f" — {item.description}"
        keyboard.append([
            InlineKeyboardButton(
                f"📝 {label}",
                callback_data=f"dt:pick:{item.id}",
            )
        ])

    await update.message.reply_text(
        "✏️ בחרו פריט לעריכת פרטים:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Helper: list action buttons ──────────────────────────────────


def _build_list_action_buttons(items) -> InlineKeyboardMarkup | None:
    """Build inline action buttons shown below list views.

    Returns None if the list is empty (no buttons needed).
    """
    if not items:
        return None

    done_count = sum(1 for i in items if (i.is_done if hasattr(i, "is_done") else i.get("is_done", False)))
    buttons: list[list[InlineKeyboardButton]] = []

    row = [
        InlineKeyboardButton("🛍️ מצב קניות", callback_data="lv:shop"),
    ]
    if done_count > 0:
        row.append(
            InlineKeyboardButton(
                f"🧹 נקה נקנו ({done_count})",
                callback_data="lv:cleardone",
            )
        )
    buttons.append(row)

    # Pin button (second row)
    buttons.append([
        InlineKeyboardButton("📌 הצמד הודעה", callback_data="lv:pin"),
    ])

    return InlineKeyboardMarkup(buttons)
