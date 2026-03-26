"""Inline query handler — suggest items from history when typing @bot_name."""

import logging
import re
from uuid import uuid4

from sqlalchemy import select, and_
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import ContextTypes

from bot.database import async_session
from bot.models.item_history import ItemHistory
from bot.models.user import User

logger = logging.getLogger(__name__)

# Characters that have special meaning in SQL LIKE patterns
_LIKE_ESCAPE_RE = re.compile(r"([%_\\])")


def _escape_like(text: str) -> str:
    """Escape SQL LIKE special characters (%, _, \\) in user input."""
    return _LIKE_ESCAPE_RE.sub(r"\\\1", text)


async def handle_inline_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle inline queries — suggest items from the user's chat histories.

    Usage: @bot_name חל → suggests חלב, חלה, etc.

    Privacy: Only returns items from chats the user has interacted with
    (via the users table → grocery_lists → item_history chain).
    """
    query = update.inline_query
    if not query:
        return

    search_text = query.query.strip()
    if not search_text or len(search_text) < 1:
        return

    user_tg_id = query.from_user.id

    # Escape LIKE wildcards in user input to prevent pattern injection
    escaped_search = _escape_like(search_text)

    results: list[InlineQueryResultArticle] = []

    try:
        async with async_session() as session:
            # First, find the internal user ID
            user_result = await session.execute(
                select(User.id).where(User.telegram_id == user_tg_id)
            )
            user_id = user_result.scalar_one_or_none()

            if user_id is None:
                # User hasn't interacted with the bot yet
                await query.answer([], cache_time=30)
                return

            # Find chat_ids where this user has created lists
            from bot.models.grocery_list import GroceryList

            chat_result = await session.execute(
                select(GroceryList.chat_id).where(
                    GroceryList.created_by == user_id
                ).distinct()
            )
            user_chat_ids = [row[0] for row in chat_result.fetchall()]

            if not user_chat_ids:
                await query.answer([], cache_time=30)
                return

            # Search item history only in the user's chats
            result = await session.execute(
                select(ItemHistory)
                .where(
                    and_(
                        ItemHistory.chat_id.in_(user_chat_ids),
                        ItemHistory.name.ilike(f"%{escaped_search}%"),
                    )
                )
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
    except Exception:
        logger.exception("Error handling inline query")

    await query.answer(results, cache_time=30)
