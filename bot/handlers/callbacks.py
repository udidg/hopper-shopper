"""Callback query handlers for inline keyboard buttons (shopping mode)."""

import logging

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.models.grocery_item import GroceryItem
from bot.services.formatter import DEPT_EMOJI, DEFAULT_EMOJI
from bot.services.grouping import DEPT_ORDER
from bot.services.list_manager import (
    get_list_items,
    get_or_create_active_list,
    get_or_create_user,
)
from bot.utils.db import db_session_with_retry

logger = logging.getLogger(__name__)

DB_ERROR_MSG = "❌ שגיאה בגישה למסד הנתונים. נסו שוב."


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /shop — enter interactive shopping mode with checkoff buttons."""
    if not update.message:
        return

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
        logger.exception("Database error in /shop")
        await update.message.reply_text(DB_ERROR_MSG)
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
    if not query:
        return

    data = query.data
    if not data or not data.startswith("shop:"):
        await query.answer()
        return

    parts = data.split(":")
    if len(parts) != 3:
        await query.answer()
        return

    action = parts[1]
    if action == "noop":
        # Department header button — do nothing
        await query.answer()
        return

    try:
        item_id = int(parts[2])
    except ValueError:
        await query.answer()
        return

    # Validate item_id is within reasonable bounds
    if item_id <= 0 or item_id > 2_147_483_647:
        await query.answer()
        return

    try:
        async with db_session_with_retry() as session:
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

    # Answer the callback to dismiss the loading indicator
    await query.answer()

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
    except BadRequest as e:
        # "Message is not modified" — user tapped same button twice quickly
        if "not modified" not in str(e).lower():
            logger.warning("BadRequest editing shop message: %s", e)
    except Exception:
        logger.exception("Error editing shop message")


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
            # Build label with quantity/unit/brand
            name_parts = [item.name]
            if item.quantity:
                if item.unit:
                    name_parts.append(f"({item.quantity} {item.unit})")
                else:
                    name_parts.append(f"({item.quantity})")
            if item.brand:
                name_parts.append(f"[{item.brand}]")

            display_name = " ".join(name_parts)

            if item.is_done:
                label = f"✅ {display_name}"
            else:
                label = f"☐ {display_name}"

            keyboard.append([
                InlineKeyboardButton(
                    label,
                    callback_data=f"shop:toggle:{item.id}",
                )
            ])

    return InlineKeyboardMarkup(keyboard)
