"""Inline query handler — suggest items from history when typing @bot_name."""

import logging
from uuid import uuid4

from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import ContextTypes

from bot.database import async_session
from bot.services.list_manager import search_item_history

logger = logging.getLogger(__name__)


async def handle_inline_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle inline queries — suggest items from the chat's history.

    Usage: @bot_name חל → suggests חלב, חלה, etc.
    """
    query = update.inline_query
    if not query:
        return

    search_text = query.query.strip()
    if not search_text or len(search_text) < 1:
        return

    # Use the user's ID to find their chat histories
    # Note: inline queries don't have a chat_id, so we search across all chats
    # the user has interacted with
    user_id = query.from_user.id

    results: list[InlineQueryResultArticle] = []

    async with async_session() as session:
        # Search across all chats (we use chat_id=0 as a fallback)
        # In practice, we'd need to track which chats the user belongs to
        # For now, search with a broad approach
        from sqlalchemy import select
        from bot.models.item_history import ItemHistory

        result = await session.execute(
            select(ItemHistory)
            .where(ItemHistory.name.ilike(f"%{search_text}%"))
            .order_by(ItemHistory.times_added.desc())
            .limit(10)
        )
        history_items = result.scalars().all()

    for item in history_items:
        category_text = f" ({item.default_category})" if item.default_category else ""
        price_text = f" — ₪{item.last_price:.2f}" if item.last_price else ""

        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=item.name,
                description=f"{category_text}{price_text}",
                input_message_content=InputTextMessageContent(
                    message_text=f"/add {item.name}",
                ),
            )
        )

    await query.answer(results, cache_time=30)
