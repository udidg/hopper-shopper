"""Authentication router – Telegram initData validation."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import AuthResponse, TelegramAuthRequest, UserResponse
from app.services.auth import create_access_token, validate_telegram_init_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(
    body: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate Telegram Web App initData and return a JWT.

    - If the user doesn't exist yet, create them.
    - If the user exists, update their display name / username.
    """
    logger.warning("Raw init_data (first 300 chars): %s", repr(body.init_data[:300]))
    tg_user = validate_telegram_init_data(body.init_data)
    if tg_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData",
        )

    telegram_id = tg_user["id"]
    username = tg_user.get("username")
    display_name = (
        f"{tg_user.get('first_name', '')} {tg_user.get('last_name', '')}".strip()
        or username
        or str(telegram_id)
    )

    # Upsert user
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
        )
        db.add(user)
        await db.flush()
    else:
        user.username = username
        user.display_name = display_name

    token = create_access_token(user.id, user.telegram_id)

    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
