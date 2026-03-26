"""Message handler — auto-detect grocery lists from free-text messages."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import async_session
from bot.services.formatter import format_items_added
from bot.services.list_manager import (
    add_items,
    get_or_create_active_list,
    get_or_create_user,
)
from bot.services.parser import looks_like_grocery_list, parse_items_text

logger = logging.getLogger(__name__)


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle plain text messages.

    If the message looks like a grocery list (multiple lines of short items),
    automatically parse and add the items.
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text

    # Skip commands
    if text.startswith("/"):
        return

    # Check if this looks like a grocery list
    if not looks_like_grocery_list(text):
        return

    item_names = parse_items_text(text)
    if not item_names or len(item_names) < 2:
        return

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
                    session,
                    chat_id=chat_id,
                    user_id=user.id,
                )

                added = await add_items(
                    session,
                    list_id=grocery_list.id,
                    chat_id=chat_id,
                    item_names=item_names,
                    user_id=user.id,
                )
                added_info = [
                    {"name": item.name, "detail": item.description}
                    for item in added
                ]
    except Exception:
        logger.exception("Database error in message handler")
        return  # Silently fail for auto-detection — don't spam the chat

    await update.message.reply_text(
        f"🔍 זיהיתי רשימת קניות!\n\n"
        + format_items_added(added_info)
        + "\n\nשלחו /sort למיון לפי מחלקות 🏪",
    )
