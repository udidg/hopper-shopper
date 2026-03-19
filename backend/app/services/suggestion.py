"""Auto-suggestion engine – queries ItemDictionary + GlobalItem for matches."""

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_dictionary import ItemDictionary
from app.models.global_item import GlobalItem
from app.services.grouping import is_hebrew


async def search_suggestions(
    db: AsyncSession,
    query: str,
    user_id: int,
    limit: int = 10,
) -> list[dict]:
    """
    Search for item suggestions matching the query.

    Searches two sources:
    1. User's own ItemDictionary (ranked higher)
    2. GlobalItem table (fallback for new users)

    Supports both English and Hebrew queries.
    Returns a unified list of suggestion dicts.
    """
    if not query or len(query) < 1:
        return []

    results: list[dict] = []
    seen_names: set[str] = set()

    # 1. Search user's ItemDictionary first (higher priority)
    user_result = await db.execute(
        select(ItemDictionary)
        .where(
            ItemDictionary.user_id == user_id,
            ItemDictionary.name.ilike(f"%{query}%"),
        )
        .order_by(ItemDictionary.updated_at.desc())
        .limit(limit)
    )
    for item in user_result.scalars().all():
        key = item.name.lower()
        if key not in seen_names:
            results.append({
                "id": item.id,
                "name": item.name,
                "default_category": item.default_category,
                "last_observed_price": (
                    float(item.last_observed_price)
                    if item.last_observed_price is not None
                    else None
                ),
                "preferred_store": item.preferred_store,
                "source": "user",
            })
            seen_names.add(key)

    # 2. Search GlobalItem table (fill remaining slots)
    remaining = limit - len(results)
    if remaining > 0:
        hebrew_query = is_hebrew(query)
        if hebrew_query:
            global_result = await db.execute(
                select(GlobalItem)
                .where(GlobalItem.name_he.ilike(f"%{query}%"))
                .limit(remaining)
            )
        else:
            global_result = await db.execute(
                select(GlobalItem)
                .where(GlobalItem.name.ilike(f"%{query}%"))
                .limit(remaining)
            )

        for item in global_result.scalars().all():
            # Use Hebrew name if query is Hebrew, else English
            display_name = item.name_he if hebrew_query and item.name_he else item.name
            display_category = (
                item.category_he if hebrew_query and item.category_he else item.category
            )
            key = display_name.lower()
            if key not in seen_names:
                results.append({
                    "id": item.id + 1_000_000,  # Offset to avoid ID collision
                    "name": display_name,
                    "default_category": display_category,
                    "last_observed_price": None,
                    "preferred_store": None,
                    "source": "global",
                })
                seen_names.add(key)

    return results[:limit]


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
