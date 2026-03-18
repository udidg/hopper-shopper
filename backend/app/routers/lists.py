"""List management router – CRUD and invite system."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.grocery_list import GroceryList
from app.models.list_member import ListMember
from app.models.user import User
from app.schemas.grocery_list import (
    JoinListRequest,
    ListCreateRequest,
    ListDetailResponse,
    ListResponse,
)

router = APIRouter(prefix="/api/lists", tags=["lists"])


@router.post("", response_model=ListResponse, status_code=status.HTTP_201_CREATED)
async def create_list(
    body: ListCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new grocery list and add the creator as owner."""
    grocery_list = GroceryList(name=body.name)
    db.add(grocery_list)
    await db.flush()

    membership = ListMember(
        user_id=user.id,
        list_id=grocery_list.id,
        role="owner",
    )
    db.add(membership)
    await db.flush()

    return ListResponse.model_validate(grocery_list)


@router.get("", response_model=list[ListResponse])
async def get_my_lists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all lists the current user is a member of."""
    result = await db.execute(
        select(GroceryList)
        .join(ListMember)
        .where(ListMember.user_id == user.id)
        .order_by(GroceryList.created_at.desc())
    )
    lists = result.scalars().all()
    return [ListResponse.model_validate(gl) for gl in lists]


@router.get("/{list_id}", response_model=ListDetailResponse)
async def get_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific list with its members. User must be a member."""
    result = await db.execute(
        select(GroceryList)
        .options(selectinload(GroceryList.members).selectinload(ListMember.user))
        .where(GroceryList.id == list_id)
    )
    grocery_list = result.scalar_one_or_none()

    if grocery_list is None:
        raise HTTPException(status_code=404, detail="List not found")

    # Check membership
    is_member = any(m.user_id == user.id for m in grocery_list.members)
    if not is_member:
        raise HTTPException(status_code=403, detail="Not a member of this list")

    return ListDetailResponse.model_validate(grocery_list)


@router.post("/join", response_model=ListResponse)
async def join_list(
    body: JoinListRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a list using an invite code."""
    result = await db.execute(
        select(GroceryList).where(GroceryList.invite_code == body.invite_code)
    )
    grocery_list = result.scalar_one_or_none()

    if grocery_list is None:
        raise HTTPException(status_code=404, detail="Invalid invite code")

    # Check if already a member
    existing = await db.execute(
        select(ListMember).where(
            ListMember.user_id == user.id,
            ListMember.list_id == grocery_list.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Already a member of this list")

    membership = ListMember(
        user_id=user.id,
        list_id=grocery_list.id,
        role="member",
    )
    db.add(membership)
    await db.flush()

    return ListResponse.model_validate(grocery_list)
