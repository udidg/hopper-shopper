"""Suggestions router – auto-complete from ItemDictionary + GlobalItem."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.grocery_item import SuggestionResponse
from app.services.suggestion import search_suggestions
from app.services.department import search_departments

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


# ── Schemas ──────────────────────────────────────────────────────


class DepartmentResponse(BaseModel):
    """A store department suggestion."""

    name: str | None
    name_he: str | None


# ── Endpoints ────────────────────────────────────────────────────


@router.get("", response_model=list[SuggestionResponse])
async def get_suggestions(
    q: str = Query(..., min_length=1, description="Search query"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for item suggestions based on partial name match.

    Returns matching items from the user's ItemDictionary and
    the global item dictionary, with their default category,
    last observed price, and preferred store.
    """
    results = await search_suggestions(db=db, query=q, user_id=user.id)
    return [SuggestionResponse(**r) for r in results]


@router.get("/departments", response_model=list[DepartmentResponse])
async def get_departments(
    q: str = Query("", description="Search query for departments"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for store departments / categories.

    Returns matching department names in both English and Hebrew.
    If no query is provided, returns all known departments.
    """
    results = await search_departments(db=db, query=q, user_id=user.id)
    return [DepartmentResponse(**r) for r in results]
