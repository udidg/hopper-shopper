"""Telegram initData validation and JWT token management."""

import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram Web App initData hash.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Returns the parsed user dict if valid, None otherwise.
    """
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    # Build the data-check-string (sorted key=value pairs)
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # Compute HMAC-SHA256
    secret_key = hmac.new(
        b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    # Parse the user JSON from initData
    user_data = parsed.get("user")
    if user_data:
        return json.loads(user_data)

    return None


def create_access_token(user_id: int, telegram_id: int) -> str:
    """Create a JWT access token for the authenticated user."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns payload or None."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.PyJWTError:
        return None
