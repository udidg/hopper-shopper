"""Pydantic schemas for GroceryList endpoints."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserResponse


class ListCreateRequest(BaseModel):
    """Request body for creating a new grocery list."""

    name: str


class ListResponse(BaseModel):
    """Public grocery list representation."""

    id: int
    name: str
    invite_code: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ListDetailResponse(ListResponse):
    """Grocery list with members."""

    members: list["ListMemberResponse"]


class ListMemberResponse(BaseModel):
    """A member of a grocery list."""

    id: int
    user_id: int
    role: str
    user: UserResponse

    model_config = {"from_attributes": True}


class JoinListRequest(BaseModel):
    """Request body for joining a list via invite code."""

    invite_code: str
