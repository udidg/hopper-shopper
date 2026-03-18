"""Pydantic schemas for GroceryItem endpoints."""

from datetime import datetime

from pydantic import BaseModel


class ItemCreateRequest(BaseModel):
    """Request body for adding an item to a list."""

    name: str
    category: str | None = None
    description: str | None = None
    preferred_store: str | None = None
    last_observed_price: float | None = None


class ItemUpdateRequest(BaseModel):
    """Request body for updating an item."""

    name: str | None = None
    category: str | None = None
    description: str | None = None
    is_scratched: bool | None = None
    preferred_store: str | None = None
    last_observed_price: float | None = None


class ItemResponse(BaseModel):
    """Public grocery item representation."""

    id: int
    list_id: int
    name: str
    category: str | None
    description: str | None
    is_scratched: bool
    sort_order: int
    preferred_store: str | None
    last_observed_price: float | None
    added_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SortRequest(BaseModel):
    """Request body for reordering items."""

    item_ids: list[int]


class SuggestionResponse(BaseModel):
    """A suggestion from the item dictionary."""

    id: int
    name: str
    default_category: str | None
    last_observed_price: float | None
    preferred_store: str | None

    model_config = {"from_attributes": True}
