"""Pydantic schemas for User and Auth endpoints."""

from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    """Request body for Telegram authentication."""

    init_data: str


class AuthResponse(BaseModel):
    """Response after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """Public user representation."""

    id: int
    telegram_id: int
    username: str | None
    display_name: str

    model_config = {"from_attributes": True}
