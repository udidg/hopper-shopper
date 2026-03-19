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
    import logging

    logger = logging.getLogger(__name__)

    # Parse the raw query string into key=value pairs (URL-decoded)
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        logger.warning("No hash found in initData")
        return None

    # Remove 'signature' field – it's not part of the hash computation
    parsed.pop("signature", None)

    # Build the data-check-string (sorted key=value pairs, URL-decoded)
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

    if hmac.compare_digest(computed_hash, received_hash):
        logger.info("Telegram initData validated successfully (decoded method)")
        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return None

    # Method 2: Try with raw (non-URL-decoded) values from the query string
    # Some Telegram SDK versions send data where the hash is computed over raw values
    raw_pairs = {}
    for part in init_data.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            raw_pairs[k] = v

    raw_hash = raw_pairs.pop("hash", None)
    raw_pairs.pop("signature", None)

    raw_data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(raw_pairs.items())
    )

    raw_computed_hash = hmac.new(
        secret_key, raw_data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if raw_hash and hmac.compare_digest(raw_computed_hash, raw_hash):
        logger.info("Telegram initData validated successfully (raw method)")
        user_data = parsed.get("user")  # Use decoded values for JSON parsing
        if user_data:
            return json.loads(user_data)
        return None

    token = settings.telegram_bot_token
    logger.warning(
        "Hash mismatch (both methods failed): decoded_computed=%s raw_computed=%s received=%s | token_len=%d",
        computed_hash[:16] + "...",
        raw_computed_hash[:16] + "...",
        received_hash[:16] + "...",
        len(token),
    )
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
