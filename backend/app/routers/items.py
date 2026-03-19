"""Item management router – CRUD, scratch, sort."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.grocery_item import GroceryItem
from app.models.list_member import ListMember
from app.models.user import User
from app.schemas.grocery_item import (
    ItemCreateRequest,
    ItemResponse,
    ItemUpdateRequest,
    SortRequest,
)
from app.services.grouping import guess_category_smart
from app.services.suggestion import upsert_dictionary_entry

router = APIRouter(prefix="/api", tags=["items"])


# ── Helpers ──────────────────────────────────────────────────────


async def _check_membership(
    db: AsyncSession, user_id: int, list_id: int
) -> None:
    """Raise 403 if user is not a member of the list."""
    result = await db.execute(
        select(ListMember).where(
            ListMember.user_id == user_id,
            ListMember.list_id == list_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Not a member of this list")


# ── Endpoints ────────────────────────────────────────────────────


@router.get("/lists/{list_id}/items", response_model=list[ItemResponse])
async def get_items(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all items for a list, ordered by sort_order."""
    await _check_membership(db, user.id, list_id)

    result = await db.execute(
        select(GroceryItem)
        .where(GroceryItem.list_id == list_id)
        .order_by(GroceryItem.sort_order)
    )
    items = result.scalars().all()
    return [ItemResponse.model_validate(item) for item in items]


@router.post(
    "/lists/{list_id}/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_item(
    list_id: int,
    body: ItemCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an item to a list with auto-grouping."""
    await _check_membership(db, user.id, list_id)

    # Auto-grouping: use provided category, or guess from name (with LLM fallback)
    category = body.category or await guess_category_smart(body.name)

    # Determine sort_order (append to end)
    max_order = await db.execute(
        select(func.coalesce(func.max(GroceryItem.sort_order), 0)).where(
            GroceryItem.list_id == list_id
        )
    )
    next_order = max_order.scalar() + 1

    item = GroceryItem(
        list_id=list_id,
        name=body.name,
        category=category,
        description=body.description,
        preferred_store=body.preferred_store,
        last_observed_price=body.last_observed_price,
        sort_order=next_order,
        added_by=user.id,
    )
    db.add(item)
    await db.flush()

    # Upsert into ItemDictionary for future suggestions
    await upsert_dictionary_entry(
        db=db,
        user_id=user.id,
        name=body.name,
        category=category,
        price=body.last_observed_price,
        store=body.preferred_store,
        list_id=list_id,
    )

    # Refresh to load server-generated fields (created_at, updated_at)
    await db.refresh(item)
    return ItemResponse.model_validate(item)


@router.patch("/items/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    body: ItemUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an item's fields (name, category, description, scratch, price, store)."""
    result = await db.execute(
        select(GroceryItem).where(GroceryItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    await _check_membership(db, user.id, item.list_id)

    # Apply updates
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.flush()

    # Update dictionary if relevant fields changed
    if any(k in update_data for k in ("name", "category", "last_observed_price", "preferred_store")):
        await upsert_dictionary_entry(
            db=db,
            user_id=user.id,
            name=item.name,
            category=item.category,
            price=item.last_observed_price,
            store=item.preferred_store,
            list_id=item.list_id,
        )

    # Refresh to load server-generated fields (e.g. updated_at via onupdate)
    await db.refresh(item)
    return ItemResponse.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an item from a list."""
    result = await db.execute(
        select(GroceryItem).where(GroceryItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    await _check_membership(db, user.id, item.list_id)
    await db.delete(item)


@router.delete(
    "/lists/{list_id}/items/scratched",
    status_code=status.HTTP_200_OK,
)
async def archive_scratched_items(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk-delete all scratched (bought) items from a list."""
    await _check_membership(db, user.id, list_id)

    result = await db.execute(
        select(GroceryItem).where(
            GroceryItem.list_id == list_id,
            GroceryItem.is_scratched == True,  # noqa: E712
        )
    )
    scratched_items = result.scalars().all()
    count = len(scratched_items)

    for item in scratched_items:
        await db.delete(item)

    return {"status": "ok", "archived_count": count}


@router.put("/items/sort", status_code=status.HTTP_200_OK)
async def sort_items(
    body: SortRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder items by updating sort_order based on the provided ID array."""
    for index, item_id in enumerate(body.item_ids):
        result = await db.execute(
            select(GroceryItem).where(GroceryItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            continue
        # Verify membership on first item
        if index == 0:
            await _check_membership(db, user.id, item.list_id)
        item.sort_order = index

    return {"status": "ok", "count": len(body.item_ids)}
