"""Callback query handlers for inline keyboard buttons (shopping mode, clear confirmation, quick-add, detail picker)."""

import logging
from datetime import datetime

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from bot.models.grocery_item import GroceryItem
from bot.models.user import User
from bot.services.formatter import DEPT_EMOJI, DEFAULT_EMOJI, format_item_detail
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
        _build_shopping_header(pending, done),
        reply_markup=keyboard,
    )


async def handle_shop_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from shopping mode buttons.

    Supported actions:
      - shop:noop:0       — department header (no-op)
      - shop:toggle:{id}  — toggle item done status
      - shop:detail:{id}  — show item detail card (replaces keyboard)
      - shop:back:{id}    — return from detail card to shopping keyboard
      - shop:done:{id}    — mark item done from detail card
    """
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

    if action == "detail":
        # Show item detail card (replaces shopping keyboard with detail view)
        await _handle_detail_card(query, parts[2])
        return

    if action == "back":
        # Return from detail card to shopping keyboard
        await _handle_back_to_shopping(query, parts[2])
        return

    if action == "done":
        # Mark item done from detail card, then show updated detail card
        await _handle_done_from_detail(query, parts[2])
        return

    # Default: toggle action
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

            # Build a detail toast for the toggled item
            toast = _build_toggle_toast(item)

            # Reload all items for this list
            items = await get_list_items(session, item.list_id)
    except Exception:
        logger.exception("Database error in shop callback")
        await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
        return

    # Answer with detail toast (brief info about the toggled item)
    await query.answer(toast)

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
        text = _build_shopping_header(pending, done)
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


# ── Shopping mode helpers ─────────────────────────────────────────


def _build_progress_bar(done: int, total: int, width: int = 10) -> str:
    """Build a text-based progress bar for shopping mode.

    Example: ▓▓▓▓▓▓░░░░ 60%
    """
    if total == 0:
        return "░" * width
    ratio = done / total
    filled = round(ratio * width)
    bar = "▓" * filled + "░" * (width - filled)
    pct = round(ratio * 100)
    return f"{bar} {pct}%"


def _build_shopping_header(pending: int, done: int) -> str:
    """Build the shopping mode header text with progress bar."""
    total = pending + done
    progress = _build_progress_bar(done, total)

    return (
        f"🛒 מצב קניות\n"
        f"\n"
        f"{progress}\n"
        f"📊 {pending} נותרו · {done} נקנו\n"
        f"\n"
        f"לחצו על פריט לסימון ✅ · על ℹ️ לפרטים"
    )


def _build_toggle_toast(item) -> str:
    """Build a brief toast message shown after toggling an item.

    Uses format_item_detail for consistent formatting.
    Telegram toast is limited to ~200 chars.
    """
    status = "✅" if item.is_done else "↩️"

    item_dict = _grocery_item_to_dict(item)
    detail = format_item_detail(item_dict, style="inline")

    toast = f"{status} {detail}"

    # Truncate if needed (toast limit ~200 chars)
    if len(toast) > 200:
        toast = toast[:197] + "..."

    return toast


def _grocery_item_to_dict(item, added_by_name: str | None = None) -> dict:
    """Convert a GroceryItem ORM object to a dict for format_item_detail."""
    return {
        "name": item.name,
        "brand": item.brand,
        "quantity": item.quantity,
        "unit": item.unit,
        "description": item.description,
        "category": item.category,
        "price": item.price,
        "is_done": item.is_done,
        "added_by_name": added_by_name,
        "created_at": item.created_at,
    }


# ── Detail card view ──────────────────────────────────────────────


async def _handle_detail_card(query, item_id_str: str) -> None:
    """Show item details as a rich card by editing the shopping message.

    Replaces the shopping keyboard with a detail card and action buttons.
    The user can go back to the shopping list or mark the item as done.
    """
    try:
        item_id = int(item_id_str)
    except ValueError:
        await query.answer()
        return

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

            # Look up who added the item
            added_by_name = None
            if item.added_by:
                user_result = await session.execute(
                    select(User).where(User.id == item.added_by)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    added_by_name = user.display_name or user.username or str(user.telegram_id)

            item_dict = _grocery_item_to_dict(item, added_by_name)
            list_id = item.list_id
            is_done = item.is_done
    except Exception:
        logger.exception("Database error in detail card")
        await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
        return

    await query.answer()

    # Build detail card text using the unified formatter
    detail_text = format_item_detail(item_dict, style="card")

    # Build action buttons
    buttons: list[list[InlineKeyboardButton]] = []

    # Toggle done button
    if is_done:
        toggle_label = "↩️ סמן כלא נקנה"
    else:
        toggle_label = "✅ סמן כנקנה"

    buttons.append([
        InlineKeyboardButton("← חזרה לרשימה", callback_data=f"shop:back:{list_id}"),
        InlineKeyboardButton(toggle_label, callback_data=f"shop:done:{item_id}"),
    ])

    keyboard = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(
            text=detail_text,
            reply_markup=keyboard,
        )
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.warning("BadRequest editing detail card: %s", e)
    except Exception:
        logger.exception("Error showing detail card")


async def _handle_back_to_shopping(query, list_id_str: str) -> None:
    """Return from detail card view back to the shopping keyboard."""
    try:
        list_id = int(list_id_str)
    except ValueError:
        await query.answer()
        return

    if list_id <= 0 or list_id > 2_147_483_647:
        await query.answer()
        return

    try:
        async with db_session_with_retry() as session:
            items = await get_list_items(session, list_id)
    except Exception:
        logger.exception("Database error in back to shopping")
        await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
        return

    if not items:
        await query.answer("📝 הרשימה ריקה!")
        try:
            await query.edit_message_text("📝 הרשימה ריקה! אין מה לקנות 😊")
        except Exception:
            pass
        return

    await query.answer()

    keyboard = _build_shopping_keyboard(items)
    pending = sum(1 for i in items if not i.is_done)
    done = sum(1 for i in items if i.is_done)

    try:
        await query.edit_message_text(
            _build_shopping_header(pending, done),
            reply_markup=keyboard,
        )
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.warning("BadRequest editing back to shopping: %s", e)
    except Exception:
        logger.exception("Error returning to shopping mode")


async def _handle_done_from_detail(query, item_id_str: str) -> None:
    """Toggle item done status from the detail card, then refresh the card."""
    try:
        item_id = int(item_id_str)
    except ValueError:
        await query.answer()
        return

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

            toast = _build_toggle_toast(item)

            # Look up who added the item
            added_by_name = None
            if item.added_by:
                user_result = await session.execute(
                    select(User).where(User.id == item.added_by)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    added_by_name = user.display_name or user.username or str(user.telegram_id)

            item_dict = _grocery_item_to_dict(item, added_by_name)
            list_id = item.list_id
            is_done = item.is_done
    except Exception:
        logger.exception("Database error in done from detail")
        await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
        return

    await query.answer(toast)

    # Refresh the detail card with updated status
    detail_text = format_item_detail(item_dict, style="card")

    if is_done:
        toggle_label = "↩️ סמן כלא נקנה"
    else:
        toggle_label = "✅ סמן כנקנה"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("← חזרה לרשימה", callback_data=f"shop:back:{list_id}"),
            InlineKeyboardButton(toggle_label, callback_data=f"shop:done:{item_id}"),
        ],
    ])

    try:
        await query.edit_message_text(
            text=detail_text,
            reply_markup=keyboard,
        )
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            logger.warning("BadRequest editing detail card after toggle: %s", e)
    except Exception:
        logger.exception("Error refreshing detail card after toggle")


# ── Shopping keyboard builder ─────────────────────────────────────


def _build_shopping_keyboard(items) -> InlineKeyboardMarkup:
    """Build an inline keyboard with items grouped by department.

    Each item row has two buttons:
      - Left (wide): toggle done status — ``shop:toggle:{id}``
      - Right (narrow): view details — ``shop:detail:{id}``

    Department headers are visually distinct with wider separators
    and item counts.
    """
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
        dept_done = sum(1 for i in dept_items if i.is_done)
        dept_total = len(dept_items)

        # Department header — visually distinct with count
        if dept_done == dept_total:
            header = f"━━ {emoji} {dept} ✅ ━━"
        else:
            header = f"━━ {emoji} {dept} ({dept_done}/{dept_total}) ━━"

        keyboard.append([
            InlineKeyboardButton(
                header,
                callback_data="shop:noop:0",
            )
        ])

        for item in dept_items:
            # Build clean label — name + quantity hint only
            display_name = item.name

            # Add quantity hint (compact)
            if item.quantity:
                if item.unit:
                    display_name += f" · {item.quantity} {item.unit}"
                else:
                    display_name += f" x{item.quantity}"

            if item.is_done:
                label = f"✅ {display_name}"
            else:
                label = f"☐ {display_name}"

            # Two-button row: toggle (wide) + detail info (narrow)
            keyboard.append([
                InlineKeyboardButton(
                    label,
                    callback_data=f"shop:toggle:{item.id}",
                ),
                InlineKeyboardButton(
                    "ℹ️",
                    callback_data=f"shop:detail:{item.id}",
                ),
            ])

    return InlineKeyboardMarkup(keyboard)


# ── List view callbacks ───────────────────────────────────────────


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
                _build_shopping_header(pending, done),
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


# ── Detail picker callbacks (from /detail guided flow) ────────────


async def handle_detail_pick_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from the /detail item picker (dt: prefix).

    Supports:
      - dt:pick:{item_id} — show item detail card for editing
    """
    query = update.callback_query
    if not query:
        return

    data = query.data
    if not data or not data.startswith("dt:"):
        await query.answer()
        return

    parts = data.split(":")
    if len(parts) != 3:
        await query.answer()
        return

    action = parts[1]

    if action == "pick":
        # Show the item's detail card (standalone, not in shopping mode)
        try:
            item_id = int(parts[2])
        except ValueError:
            await query.answer()
            return

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

                # Look up who added the item
                added_by_name = None
                if item.added_by:
                    user_result = await session.execute(
                        select(User).where(User.id == item.added_by)
                    )
                    user = user_result.scalar_one_or_none()
                    if user:
                        added_by_name = user.display_name or user.username or str(user.telegram_id)

                item_dict = _grocery_item_to_dict(item, added_by_name)
                item_name = item.name
                current_detail = item.description
        except Exception:
            logger.exception("Database error in detail pick callback")
            await query.answer("❌ שגיאה. נסו שוב.", show_alert=True)
            return

        await query.answer()

        # Build detail card text
        detail_text = format_item_detail(item_dict, style="card")

        # Add instruction for editing
        detail_text += "\n\n✏️ לעדכון פרטים, שלחו:\n"
        detail_text += f"/detail {item_name} <פרטים חדשים>"
        if current_detail:
            detail_text += f"\n\n📝 פרטים נוכחיים: {current_detail}"

        try:
            await query.edit_message_text(text=detail_text)
        except BadRequest as e:
            if "not modified" not in str(e).lower():
                logger.warning("BadRequest editing detail pick message: %s", e)
        except Exception:
            logger.exception("Error showing detail pick card")

    else:
        await query.answer()
