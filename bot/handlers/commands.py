"""Command handlers for the Hopper Shopper bot.

Handles: /start, /help, /add, /remove, /clear, /done, /undone, /list, /sort, /price
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import async_session
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

logger = logging.getLogger(__name__)

DB_ERROR_MSG = "❌ שגיאה בגישה למסד הנתונים. נסו שוב."


def _extract_args(text: str) -> str:
    """Extract command arguments, handling bot username suffix in groups.

    E.g. '/add@MyBot חלב' → 'חלב'
    """
    parts = text.split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


async def _get_user_and_list(update: Update, session):
    """Helper: get or create user and active list for the current chat."""
    tg_user = update.effective_user
    chat_id = update.effective_chat.id

    user = await get_or_create_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        display_name=tg_user.full_name,
    )

    grocery_list = await get_or_create_active_list(
        session,
        chat_id=chat_id,
        user_id=user.id,
    )

    return user, grocery_list


# ── /start ───────────────────────────────────────────────────────


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    await update.message.reply_text(
        "🛒 ברוכים הבאים ל-Hopper Shopper!\n\n"
        "אני בוט לניהול רשימות קניות.\n"
        "הוסיפו אותי לקבוצה ותתחילו לנהל רשימות קניות משותפות!\n\n"
        "שלחו /help לרשימת הפקודות.",
    )


# ── /help ────────────────────────────────────────────────────────


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show available commands."""
    await update.message.reply_text(format_help())


# ── /add ─────────────────────────────────────────────────────────


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add — add items to the grocery list."""
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

    try:
        async with async_session() as session:
            async with session.begin():
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
    items_text = _extract_args(update.message.text)

    if not items_text.strip():
        await update.message.reply_text(
            "🗑️ כדי להסיר פריט, כתבו אחרי הפקודה:\n\n"
            "/remove חלב",
        )
        return

    item_names = parse_items_text(items_text)

    try:
        async with async_session() as session:
            async with session.begin():
                _, grocery_list = await _get_user_and_list(update, session)
                removed = await remove_items(session, grocery_list.id, item_names)
    except Exception:
        logger.exception("Database error in /remove")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(format_items_removed(removed))


# ── /clear ───────────────────────────────────────────────────────


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — clear the entire grocery list."""
    try:
        async with async_session() as session:
            async with session.begin():
                _, grocery_list = await _get_user_and_list(update, session)
                count = await clear_list(session, grocery_list.id)
    except Exception:
        logger.exception("Database error in /clear")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    if count > 0:
        await update.message.reply_text(f"🗑️ הרשימה נוקתה! ({count} פריטים הוסרו)")
    else:
        await update.message.reply_text("📝 הרשימה כבר ריקה!")


# ── /done ────────────────────────────────────────────────────────


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /done — mark an item as purchased."""
    item_name = _extract_args(update.message.text)

    if not item_name.strip():
        await update.message.reply_text(
            "✅ כדי לסמן פריט כנקנה, כתבו אחרי הפקודה:\n\n"
            "/done חלב",
        )
        return

    try:
        async with async_session() as session:
            async with session.begin():
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
    item_name = _extract_args(update.message.text)

    if not item_name.strip():
        await update.message.reply_text(
            "↩️ כדי לבטל סימון פריט, כתבו אחרי הפקודה:\n\n"
            "/undone חלב",
        )
        return

    try:
        async with async_session() as session:
            async with session.begin():
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
    """Handle /list — show the current grocery list (unsorted)."""
    try:
        async with async_session() as session:
            async with session.begin():
                _, grocery_list = await _get_user_and_list(update, session)
                items = await get_list_items(session, grocery_list.id)
                list_name = grocery_list.name
    except Exception:
        logger.exception("Database error in /list")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(
        format_plain_list(items_to_dicts(items), list_name),
    )


# ── /sort ────────────────────────────────────────────────────────


async def sort_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sort — show the grocery list sorted by department."""
    try:
        async with async_session() as session:
            async with session.begin():
                _, grocery_list = await _get_user_and_list(update, session)
                items = await get_list_items(session, grocery_list.id)
                list_name = grocery_list.name
    except Exception:
        logger.exception("Database error in /sort")
        await update.message.reply_text(DB_ERROR_MSG)
        return

    await update.message.reply_text(
        format_sorted_list(items_to_dicts(items), list_name),
    )


# ── /price ───────────────────────────────────────────────────────


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /price — set price for an item. Usage: /price חלב 7.90"""
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
        async with async_session() as session:
            async with session.begin():
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

    Usage: /detail תפוחי אדמה של דוד משה
    This saves "של דוד משה" as the default detail for "תפוחי אדמה".
    Next time you add "תפוחי אדמה", the detail will be auto-applied.
    """
    args = _extract_args(update.message.text)

    if not args.strip():
        await update.message.reply_text(
            "❌ שימוש: /detail פריט פרטים\n"
            "דוגמה: /detail תפוחי אדמה של דוד משה\n\n"
            "הפרטים יישמרו ויוצגו אוטומטית בכל פעם שתוסיפו את הפריט.",
        )
        return

    # Split: first word(s) = item name, rest = detail
    # We need a smarter split — try to match against known items in history
    # For now, use a simple approach: everything before the last known separator
    parts = args.strip()

    # Try to find the item name by checking history
    try:
        async with async_session() as session:
            async with session.begin():
                chat_id = update.effective_chat.id

                # Strategy: try progressively shorter prefixes as item name
                words = parts.split()
                item_name = None
                detail = None

                for i in range(len(words) - 1, 0, -1):
                    candidate_name = " ".join(words[:i])
                    candidate_detail = " ".join(words[i:])

                    # Check if this candidate exists in history or in the active list
                    from bot.services.list_manager import get_or_create_active_list
                    from bot.models.grocery_item import GroceryItem
                    from bot.models.item_history import ItemHistory
                    from sqlalchemy import select, and_

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
