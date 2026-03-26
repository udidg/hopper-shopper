"""CRUD operations for grocery lists and items."""

import logging

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.grocery_list import GroceryList
from bot.models.grocery_item import GroceryItem
from bot.models.item_history import ItemHistory
from bot.models.user import User
from bot.services.grouping import guess_category_smart

logger = logging.getLogger(__name__)


# ── User management ──────────────────────────────────────────────


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    display_name: str | None = None,
) -> User:
    """Get an existing user or create a new one."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
        )
        session.add(user)
        await session.flush()
    else:
        # Update display info
        if username is not None:
            user.username = username
        if display_name is not None:
            user.display_name = display_name
        await session.flush()

    return user


# ── List management ──────────────────────────────────────────────


async def get_or_create_active_list(
    session: AsyncSession,
    chat_id: int,
    user_id: int | None = None,
    list_name: str = "רשימת קניות",
) -> GroceryList:
    """Get the active grocery list for a chat, or create one."""
    result = await session.execute(
        select(GroceryList).where(
            and_(
                GroceryList.chat_id == chat_id,
                GroceryList.is_active == True,  # noqa: E712
            )
        )
    )
    grocery_list = result.scalar_one_or_none()

    if grocery_list is None:
        grocery_list = GroceryList(
            chat_id=chat_id,
            name=list_name,
            is_active=True,
            created_by=user_id,
        )
        session.add(grocery_list)
        await session.flush()

    return grocery_list


async def get_list_items(
    session: AsyncSession,
    list_id: int,
    include_done: bool = True,
) -> list[GroceryItem]:
    """Get all items in a grocery list."""
    query = select(GroceryItem).where(GroceryItem.list_id == list_id)
    if not include_done:
        query = query.where(GroceryItem.is_done == False)  # noqa: E712
    query = query.order_by(GroceryItem.sort_order, GroceryItem.created_at)

    result = await session.execute(query)
    return list(result.scalars().all())


def items_to_dicts(items: list[GroceryItem]) -> list[dict]:
    """Convert GroceryItem models to dicts for the formatter."""
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "is_done": item.is_done,
            "price": float(item.price) if item.price is not None else None,
            "description": item.description,
        }
        for item in items
    ]


# ── Item operations ──────────────────────────────────────────────


async def add_items(
    session: AsyncSession,
    list_id: int,
    chat_id: int,
    item_names: list[str],
    user_id: int | None = None,
) -> list[GroceryItem]:
    """
    Add multiple items to a grocery list.

    Automatically classifies each item into a department.
    Auto-applies saved details/brand from item history.
    Updates item history for future suggestions.
    """
    added: list[GroceryItem] = []

    # Get current max sort_order
    result = await session.execute(
        select(func.coalesce(func.max(GroceryItem.sort_order), 0)).where(
            GroceryItem.list_id == list_id
        )
    )
    max_order = result.scalar() or 0

    for i, name in enumerate(item_names):
        # Classify the item
        category = await guess_category_smart(name)

        # Look up saved detail/brand from history
        saved_detail = await _get_saved_detail(session, chat_id, name)

        item = GroceryItem(
            list_id=list_id,
            name=name,
            category=category,
            description=saved_detail,
            added_by=user_id,
            sort_order=max_order + i + 1,
        )
        session.add(item)
        added.append(item)

        # Update item history
        await _upsert_item_history(session, chat_id, name, category)

    await session.flush()
    return added


async def remove_items(
    session: AsyncSession,
    list_id: int,
    item_names: list[str],
) -> list[str]:
    """Remove items from a grocery list by name. Returns names of removed items."""
    removed: list[str] = []

    for name in item_names:
        result = await session.execute(
            select(GroceryItem).where(
                and_(
                    GroceryItem.list_id == list_id,
                    GroceryItem.name.ilike(name.strip()),
                )
            )
        )
        item = result.scalar_one_or_none()
        if item:
            removed.append(item.name)
            await session.delete(item)

    await session.flush()
    return removed


async def mark_item_done(
    session: AsyncSession,
    list_id: int,
    item_name: str,
    done: bool = True,
) -> GroceryItem | None:
    """Mark an item as done/undone. Returns the item or None if not found."""
    result = await session.execute(
        select(GroceryItem).where(
            and_(
                GroceryItem.list_id == list_id,
                GroceryItem.name.ilike(item_name.strip()),
            )
        )
    )
    item = result.scalar_one_or_none()

    if item:
        item.is_done = done
        await session.flush()

    return item


async def mark_item_done_by_id(
    session: AsyncSession,
    item_id: int,
    done: bool = True,
) -> GroceryItem | None:
    """Mark an item as done/undone by ID. Returns the item or None."""
    result = await session.execute(
        select(GroceryItem).where(GroceryItem.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item:
        item.is_done = done
        await session.flush()

    return item


async def clear_list(
    session: AsyncSession,
    list_id: int,
    done_only: bool = False,
) -> int:
    """
    Clear items from a grocery list.

    Args:
        done_only: If True, only clear done items. If False, clear all.

    Returns:
        Number of items removed.
    """
    query = select(GroceryItem).where(GroceryItem.list_id == list_id)
    if done_only:
        query = query.where(GroceryItem.is_done == True)  # noqa: E712

    result = await session.execute(query)
    items = result.scalars().all()
    count = len(items)

    for item in items:
        await session.delete(item)

    await session.flush()
    return count


async def set_item_price(
    session: AsyncSession,
    list_id: int,
    item_name: str,
    price: float,
) -> GroceryItem | None:
    """Set the price for an item. Returns the item or None if not found."""
    result = await session.execute(
        select(GroceryItem).where(
            and_(
                GroceryItem.list_id == list_id,
                GroceryItem.name.ilike(item_name.strip()),
            )
        )
    )
    item = result.scalar_one_or_none()

    if item:
        item.price = price
        await session.flush()

    return item


# ── Item history (for suggestions & details) ─────────────────────


async def _get_saved_detail(
    session: AsyncSession,
    chat_id: int,
    name: str,
) -> str | None:
    """Look up saved detail/brand for an item from history."""
    result = await session.execute(
        select(ItemHistory.default_detail).where(
            and_(
                ItemHistory.chat_id == chat_id,
                ItemHistory.name.ilike(name.strip()),
                ItemHistory.default_detail.isnot(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def set_item_detail(
    session: AsyncSession,
    chat_id: int,
    item_name: str,
    detail: str,
) -> bool:
    """
    Save a default detail/brand for an item in history.

    Also updates the description on any existing items in the active list.
    Returns True if the history entry was found/created.
    """
    # Upsert the history entry
    result = await session.execute(
        select(ItemHistory).where(
            and_(
                ItemHistory.chat_id == chat_id,
                ItemHistory.name.ilike(item_name.strip()),
            )
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        # Create a new history entry with the detail
        entry = ItemHistory(
            chat_id=chat_id,
            name=item_name.strip(),
            default_detail=detail,
            times_added=0,
        )
        session.add(entry)
    else:
        entry.default_detail = detail

    # Also update description on existing items in the active list
    active_list = await get_or_create_active_list(session, chat_id)
    items_result = await session.execute(
        select(GroceryItem).where(
            and_(
                GroceryItem.list_id == active_list.id,
                GroceryItem.name.ilike(item_name.strip()),
            )
        )
    )
    for item in items_result.scalars().all():
        item.description = detail

    await session.flush()
    return True


async def _upsert_item_history(
    session: AsyncSession,
    chat_id: int,
    name: str,
    category: str | None,
) -> None:
    """Create or update an item history entry."""
    result = await session.execute(
        select(ItemHistory).where(
            and_(
                ItemHistory.chat_id == chat_id,
                ItemHistory.name.ilike(name.strip()),
            )
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        entry = ItemHistory(
            chat_id=chat_id,
            name=name,
            default_category=category,
            times_added=1,
        )
        session.add(entry)
    else:
        entry.times_added += 1
        if category:
            entry.default_category = category

    await session.flush()


async def search_item_history(
    session: AsyncSession,
    chat_id: int,
    query: str,
    limit: int = 10,
) -> list[ItemHistory]:
    """Search item history for suggestions."""
    result = await session.execute(
        select(ItemHistory)
        .where(
            and_(
                ItemHistory.chat_id == chat_id,
                ItemHistory.name.ilike(f"%{query}%"),
            )
        )
        .order_by(ItemHistory.times_added.desc(), ItemHistory.last_used.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
