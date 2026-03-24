"""Callback query handlers for inline keyboard buttons (shopping mode)."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.database import async_session
from bot.services.formatter import DEPT_EMOJI, DEFAULT_EMOJI
from bot.services.grouping import DEPT_ORDER
from bot.services.list_manager import (
    get_list_items,
    get_or_create_active_list,
    get_or_create_user,
)

logger = logging.getLogger(__name__)


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /shop — enter interactive shopping mode with checkoff buttons."""
    try:
        async with async_session() as session:
            async with session.begin():
                tg_user = update.effective_user
                chat_id = update.effective_chat.id

                user = await get_or_create_user(
                    session,
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    display_name=tg_user.full_name,
                )

                grocery_list = await get_or_create_active_list(
                    session, chat_id=chat_id, user_id=user.id
                )

                items = await get_list_items(session, grocery_list.id)
    except Exception:
        logger.exception("Database error in /shop")
        await update.message.reply_text("❌ שגיאה בגישה למסד הנתונים. נסו שוב.")
        return

    if not items:
        await update.message.reply_text("📝 הרשימה ריקה! אין מה לקנות 😊")
        return

    # Build inline keyboard with items grouped by department
    keyboard = _build_shopping_keyboard(items)

    # Count stats
    pending = sum(1 for i in items if not i.is_done)
    done = sum(1 for i in items if i.is_done)

    await update.message.reply_text(
        f"🛍️ מצב קניות\n\n"
        f"לחצו על פריט כדי לסמן/לבטל סימון ✅\n"
        f"📊 {pending} נותרו | {done} נקנו",
        reply_markup=keyboard,
    )


async def handle_shop_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from shopping mode buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data or not data.startswith("shop:"):
        return

    parts = data.split(":")
    if len(parts) != 3:
        return

    action = parts[1]
    if action == "noop":
        # Department header button — do nothing
        return

    try:
        item_id = int(parts[2])
    except ValueError:
        return

    try:
        async with async_session() as session:
            async with session.begin():
                from sqlalchemy import select
                from bot.models.grocery_item import GroceryItem

                result = await session.execute(
                    select(GroceryItem).where(GroceryItem.id == item_id)
                )
                item = result.scalar_one_or_none()

                if item is None:
                    await query.answer("❌ פריט לא נמצא", show_alert=True)
                    return

                # Toggle done status
                item.is_done = not item.is_done
                await session.flush()

                # Reload all items for this list
                items = await get_list_items(session, item.list_id)
    except Exception:
        logger.exception("Database error in shop callback")
        await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
        return

    # Rebuild the keyboard
    keyboard = _build_shopping_keyboard(items)

    pending = sum(1 for i in items if not i.is_done)
    done = sum(1 for i in items if i.is_done)

    if pending == 0:
        text = "🎉 סיימתם את הקניות!\n\n✅ כל הפריטים נקנו!"
    else:
        text = (
            f"🛍️ מצב קניות\n\n"
            f"לחצו על פריט כדי לסמן/לבטל סימון ✅\n"
            f"📊 {pending} נותרו | {done} נקנו"
        )

    try:
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard if pending > 0 else None,
        )
    except Exception:
        # Message might not have changed — ignore
        pass


def _build_shopping_keyboard(items) -> InlineKeyboardMarkup:
    """Build an inline keyboard with items grouped by department."""
    # Group by department
    groups: dict[str, list] = {}
    for item in items:
        dept = item.category or "אחר"
        if dept not in groups:
            groups[dept] = []
        groups[dept].append(item)

    # Sort departments
    sorted_depts = sorted(
        groups.keys(),
        key=lambda d: DEPT_ORDER.get(d, 999),
    )

    keyboard: list[list[InlineKeyboardButton]] = []

    for dept in sorted_depts:
        dept_items = groups[dept]
        emoji = DEPT_EMOJI.get(dept, DEFAULT_EMOJI)

        # Add department header as a non-clickable label
        keyboard.append([
            InlineKeyboardButton(
                f"── {emoji} {dept} ──",
                callback_data="shop:noop:0",
            )
        ])

        for item in dept_items:
            if item.is_done:
                label = f"✅ {item.name}"
            else:
                label = f"☐ {item.name}"

            keyboard.append([
                InlineKeyboardButton(
                    label,
                    callback_data=f"shop:toggle:{item.id}",
                )
            ])

    return InlineKeyboardMarkup(keyboard)
