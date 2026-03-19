"""Department search service – autocomplete for store departments."""

from sqlalchemy import select, distinct, union_all, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.global_item import GlobalItem
from app.models.item_dictionary import ItemDictionary
from app.services.grouping import (
    DEPARTMENTS_EN,
    DEPARTMENTS_HE,
    is_hebrew,
)


async def search_departments(
    db: AsyncSession,
    query: str,
    user_id: int,
    limit: int = 10,
) -> list[dict[str, str | None]]:
    """
    Search for store departments matching the query.

    Sources (in priority order):
    1. Hardcoded department lists (EN + HE)
    2. Categories from user's ItemDictionary
    3. Categories from GlobalItem table

    Returns a list of dicts with 'name' and 'name_he' keys.
    """
    query = query.strip().lower()
    if not query:
        # Return all known departments
        return _all_departments()[:limit]

    hebrew_query = is_hebrew(query)

    # Start with hardcoded departments
    results: list[dict[str, str | None]] = []
    seen: set[str] = set()

    # Match against hardcoded lists
    for en, he in zip(DEPARTMENTS_EN, DEPARTMENTS_HE):
        if hebrew_query:
            if query in he.lower():
                key = he.lower()
                if key not in seen:
                    results.append({"name": en, "name_he": he})
                    seen.add(key)
        else:
            if query in en.lower():
                key = en.lower()
                if key not in seen:
                    results.append({"name": en, "name_he": he})
                    seen.add(key)

    # Search user's ItemDictionary categories
    user_cats = await db.execute(
        select(distinct(ItemDictionary.default_category))
        .where(
            ItemDictionary.user_id == user_id,
            ItemDictionary.default_category.isnot(None),
            ItemDictionary.default_category.ilike(f"%{query}%"),
        )
        .limit(limit)
    )
    for (cat,) in user_cats:
        key = cat.lower()
        if key not in seen:
            results.append({"name": cat, "name_he": None})
            seen.add(key)

    # Search GlobalItem categories
    if hebrew_query:
        global_cats = await db.execute(
            select(distinct(GlobalItem.category_he))
            .where(
                GlobalItem.category_he.isnot(None),
                GlobalItem.category_he.ilike(f"%{query}%"),
            )
            .limit(limit)
        )
        for (cat,) in global_cats:
            key = cat.lower()
            if key not in seen:
                # Try to find the EN equivalent
                en_name = _find_en_for_he(cat)
                results.append({"name": en_name, "name_he": cat})
                seen.add(key)
    else:
        global_cats = await db.execute(
            select(distinct(GlobalItem.category))
            .where(
                GlobalItem.category.isnot(None),
                GlobalItem.category.ilike(f"%{query}%"),
            )
            .limit(limit)
        )
        for (cat,) in global_cats:
            key = cat.lower()
            if key not in seen:
                he_name = _find_he_for_en(cat)
                results.append({"name": cat, "name_he": he_name})
                seen.add(key)

    return results[:limit]


def _all_departments() -> list[dict[str, str | None]]:
    """Return all known departments as dicts."""
    return [
        {"name": en, "name_he": he}
        for en, he in zip(DEPARTMENTS_EN, DEPARTMENTS_HE)
    ]


def _find_en_for_he(he_name: str) -> str | None:
    """Find the English department name for a Hebrew one."""
    from app.services.grouping import DEPT_HE_TO_EN
    return DEPT_HE_TO_EN.get(he_name)


def _find_he_for_en(en_name: str) -> str | None:
    """Find the Hebrew department name for an English one."""
    from app.services.grouping import DEPT_EN_TO_HE
    return DEPT_EN_TO_HE.get(en_name)
