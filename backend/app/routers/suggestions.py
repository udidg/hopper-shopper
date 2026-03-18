"""Suggestions router – auto-complete from ItemDictionary."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.grocery_item import SuggestionResponse
from app.services.suggestion import search_suggestions

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.get("", response_model=list[SuggestionResponse])
async def get_suggestions(
    q: str = Query(..., min_length=1, description="Search query"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for item suggestions based on partial name match.

    Returns matching items from the user's ItemDictionary with
    their default category, last observed price, and preferred store.
    """
    results = await search_suggestions(db=db, query=q, user_id=user.id)
    return [SuggestionResponse.model_validate(r) for r in results]
