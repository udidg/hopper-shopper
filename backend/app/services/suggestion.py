"""Auto-suggestion engine – queries ItemDictionary for partial matches."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_dictionary import ItemDictionary


async def search_suggestions(
    db: AsyncSession,
    query: str,
    user_id: int,
    limit: int = 10,
) -> list[ItemDictionary]:
    """
    Search the ItemDictionary for items matching the query.

    Uses case-insensitive ILIKE for partial string matching.
    Results are scoped to the user's own dictionary entries.
    """
    if not query or len(query) < 1:
        return []

    result = await db.execute(
        select(ItemDictionary)
        .where(
            ItemDictionary.user_id == user_id,
            ItemDictionary.name.ilike(f"%{query}%"),
        )
        .order_by(ItemDictionary.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def upsert_dictionary_entry(
    db: AsyncSession,
    user_id: int,
    name: str,
    category: str | None = None,
    price: float | None = None,
    store: str | None = None,
    list_id: int | None = None,
) -> ItemDictionary:
    """
    Create or update an ItemDictionary entry.

    If an entry with the same name exists for this user, update it.
    Otherwise, create a new one.
    """
    result = await db.execute(
        select(ItemDictionary).where(
            ItemDictionary.user_id == user_id,
            ItemDictionary.name.ilike(name),
        )
    )
    entry = result.scalar_one_or_none()

    if entry is None:
        entry = ItemDictionary(
            user_id=user_id,
            list_id=list_id,
            name=name,
            default_category=category,
            last_observed_price=price,
            preferred_store=store,
        )
        db.add(entry)
    else:
        if category is not None:
            entry.default_category = category
        if price is not None:
            entry.last_observed_price = price
        if store is not None:
            entry.preferred_store = store

    await db.flush()
    return entry
