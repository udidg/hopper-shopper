"""Callback query handlers for inline keyboard buttons (shopping mode, clear confirmation, quick-add)."""

import logging

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.models.grocery_item import GroceryItem
from bot.services.formatter import DEPT_EMOJI, DEFAULT_EMOJI
from bot.services.grouping import DEPT_ORDER
from bot.services.list_manager import (
    add_items,
    clear_list,
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
        # Richer completion message with summary and next actions
        total = len(items)

        # Calculate price summary if any items have prices
        priced_items = [i for i in items if i.price is not None]
        total_price = sum(float(i.price) for i in priced_items)

        # Build department summary
        dept_counts: dict[str, int] = {}
        for i in items:
            dept = i.category or "אחר"
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        summary_lines = [
            f"🎉 סיימתם את הקניות!\n",
            f"✅ כל {total} הפריטים נקנו!",
        ]

        # Department breakdown
        if len(dept_counts) > 1:
            summary_lines.append("")
            summary_lines.append("📦 לפי מחלקות:")
            for dept, count in sorted(dept_counts.items(), key=lambda x: -x[1]):
                emoji = DEPT_EMOJI.get(dept, DEFAULT_EMOJI)
                summary_lines.append(f"  {emoji} {dept}: {count}")

        # Price summary
        if priced_items:
            summary_lines.append("")
            summary_lines.append(f"💰 סה\"כ: ₪{total_price:.2f}")
            if len(priced_items) < total:
                summary_lines.append(
                    f"  ({len(priced_items)} מתוך {total} פריטים עם מחיר)"
                )

        summary_lines.append("")
        summary_lines.append("מה עכשיו?")

        completion_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🧹 נקה נקנו", callback_data="clear:done:confirm"),
                InlineKeyboardButton("🗑️ נקה הכל", callback_data="clear:all:confirm"),
            ],
        ])
        text = "\n".join(summary_lines)
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=completion_keyboard,
            )
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                logger.warning("BadRequest editing shop message: %s", e)
        except Exception:
            logger.exception("Error editing shop message")
    else:
        text = (
            f"🛍️ מצב קניות\n\n"
            f"לחצו על פריט כדי לסמן/לבטל סימון ✅\n"
            f"📊 {pending} נותרו | {done} נקנו"
        )
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=keyboard,
            )
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                logger.warning("BadRequest editing shop message: %s", e)
        except Exception:
            logger.exception("Error editing shop message")


async def handle_clear_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from clear confirmation buttons."""
    query = update.callback_query
    if not query:
        return

    data = query.data
    if not data or not data.startswith("clear:"):
        await query.answer()
        return

    parts = data.split(":")
    if len(parts) != 3:
        await query.answer()
        return

    action = parts[1]  # "all", "done", or "cancel"

    if action == "cancel":
        await query.answer("↩️ בוטל")
        try:
            await query.edit_message_text("↩️ הניקוי בוטל.")
        except Exception:
            pass
        return

    done_only = action == "done"

    try:
        async with db_session_with_retry() as session:
            tg_user = update.effective_user
            chat = update.effective_chat

            if tg_user is None or chat is None:
                await query.answer()
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

            count = await clear_list(session, grocery_list.id, done_only=done_only)
    except Exception:
        logger.exception("Database error in clear callback")
        await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
        return

    await query.answer()

    if done_only:
        if count > 0:
            text = f"🧹 {count} פריטים שנקנו הוסרו מהרשימה!"
        else:
            text = "✅ אין פריטים שנקנו להסרה."
    else:
        if count > 0:
            text = f"🗑️ הרשימה נוקתה! ({count} פריטים הוסרו)"
        else:
            text = "📝 הרשימה כבר ריקה!"

    try:
        await query.edit_message_text(text)
    except Exception:
        logger.exception("Error editing clear message")


async def handle_quick_add_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from quick-add buttons (empty list suggestions)."""
    query = update.callback_query
    if not query:
        return

    data = query.data
    if not data or not data.startswith("qa:"):
        await query.answer()
        return

    item_name = data[3:]  # Remove "qa:" prefix
    if not item_name.strip():
        await query.answer()
        return

    try:
        async with db_session_with_retry() as session:
            tg_user = update.effective_user
            chat = update.effective_chat

            if tg_user is None or chat is None:
                await query.answer()
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

            added = await add_items(
                session,
                list_id=grocery_list.id,
                chat_id=chat.id,
                item_names=[item_name],
                user_id=user.id,
            )
    except Exception:
        logger.exception("Database error in quick-add callback")
        await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
        return

    if added:
        await query.answer(f"✅ {item_name} נוסף!")
    else:
        await query.answer(f"⚠️ {item_name} כבר ברשימה")

    # Update the message to show the item was added
    try:
        await query.edit_message_text(
            f"✅ {item_name} נוסף לרשימה!\n\n"
            f"שלחו /list לצפייה ברשימה, או /shop למצב קניות 🛍️"
        )
    except Exception:
        logger.exception("Error editing quick-add message")


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


async def handle_list_view_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from list view action buttons (lv: prefix).

    Supports:
      - lv:shop — start shopping mode
      - lv:cleardone — clear only purchased items
    """
    query = update.callback_query
    if not query:
        return

    data = query.data
    if not data or not data.startswith("lv:"):
        await query.answer()
        return

    action = data[3:]  # Remove "lv:" prefix

    if action == "shop":
        # Start shopping mode — build the shopping keyboard
        try:
            async with db_session_with_retry() as session:
                tg_user = update.effective_user
                chat = update.effective_chat

                if tg_user is None or chat is None:
                    await query.answer()
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
            logger.exception("Database error in lv:shop callback")
            await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
            return

        if not items:
            await query.answer("📝 הרשימה ריקה!")
            return

        await query.answer()

        keyboard = _build_shopping_keyboard(items)
        pending = sum(1 for i in items if not i.is_done)
        done = sum(1 for i in items if i.is_done)

        try:
            await query.edit_message_text(
                f"🛍️ מצב קניות\n\n"
                f"לחצו על פריט כדי לסמן/לבטל סימון ✅\n"
                f"📊 {pending} נותרו | {done} נקנו",
                reply_markup=keyboard,
            )
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                logger.warning("BadRequest editing list view message: %s", e)
        except Exception:
            logger.exception("Error editing list view message")

    elif action == "cleardone":
        # Clear only purchased items
        try:
            async with db_session_with_retry() as session:
                tg_user = update.effective_user
                chat = update.effective_chat

                if tg_user is None or chat is None:
                    await query.answer()
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

                count = await clear_list(session, grocery_list.id, done_only=True)
        except Exception:
            logger.exception("Database error in lv:cleardone callback")
            await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
            return

        if count > 0:
            await query.answer(f"🧹 {count} פריטים שנקנו הוסרו!")
            try:
                await query.edit_message_text(
                    f"🧹 {count} פריטים שנקנו הוסרו מהרשימה!\n\n"
                    f"שלחו /list לצפייה ברשימה המעודכנת."
                )
            except Exception:
                logger.exception("Error editing cleardone message")
        else:
            await query.answer("✅ אין פריטים שנקנו להסרה.")

    elif action == "pin":
        # Pin the list message in the chat
        if not query.message:
            await query.answer()
            return

        try:
            await query.message.pin(disable_notification=True)
            await query.answer("📌 ההודעה הוצמדה!")
        except BadRequest as e:
            error_msg = str(e).lower()
            if "not enough rights" in error_msg or "admin" in error_msg:
                await query.answer(
                    "❌ אין לי הרשאות להצמיד הודעות.\n"
                    "הוסיפו אותי כמנהל עם הרשאת הצמדה.",
                    show_alert=True,
                )
            elif "chat is not modified" in error_msg:
                await query.answer("📌 ההודעה כבר מוצמדת!")
            else:
                logger.warning("BadRequest pinning message: %s", e)
                await query.answer("❌ לא הצלחתי להצמיד. נסו שוב.", show_alert=True)
        except Exception:
            logger.exception("Error pinning message")
            await query.answer("❌ שגיאה בהצמדה. נסו שוב.", show_alert=True)

    else:
        await query.answer()
