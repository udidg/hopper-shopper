"""Telegram initData validation and JWT token management."""

import hashlib
import hmac
import json
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

logger = logging.getLogger(__name__)


def _try_hmac_validation(
    data_check_string: str,
    received_hash: str,
    token: str,
    method_name: str,
) -> bool:
    """Try HMAC-SHA256 validation with both possible key/msg orderings."""

    # Method A: key="WebAppData", msg=token (common in online examples)
    secret_a = hmac.new(
        b"WebAppData", token.encode(), hashlib.sha256
    ).digest()
    hash_a = hmac.new(
        secret_a, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(hash_a, received_hash):
        logger.info("Validated via %s (key=WebAppData, msg=token)", method_name)
        return True

    # Method B: key=token, msg="WebAppData" (literal reading of Telegram docs)
    secret_b = hmac.new(
        token.encode(), b"WebAppData", hashlib.sha256
    ).digest()
    hash_b = hmac.new(
        secret_b, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(hash_b, received_hash):
        logger.info("Validated via %s (key=token, msg=WebAppData)", method_name)
        return True

    logger.debug(
        "%s failed: hash_a=%s hash_b=%s received=%s",
        method_name,
        hash_a[:16],
        hash_b[:16],
        received_hash[:16],
    )
    return False


def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram Web App initData hash.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Tries multiple validation strategies to handle different Telegram SDK versions:
    1. URL-decoded values (standard parse_qsl)
    2. Raw URL-encoded values (split on & and =)

    Returns the parsed user dict if valid, None otherwise.
    """
    token = settings.telegram_bot_token

    # === Parse with URL decoding (standard method) ===
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        logger.warning("No hash found in initData")
        return None

    # Remove fields not part of hash computation
    parsed.pop("signature", None)

    # Build data-check-string from decoded values (sorted)
    decoded_dcs = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # Try decoded values
    if _try_hmac_validation(decoded_dcs, received_hash, token, "decoded"):
        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return None

    # === Parse WITHOUT URL decoding (raw values) ===
    raw_pairs = {}
    for part in init_data.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            raw_pairs[k] = v

    raw_hash = raw_pairs.pop("hash", None)
    raw_pairs.pop("signature", None)

    raw_dcs = "\n".join(
        f"{k}={v}" for k, v in sorted(raw_pairs.items())
    )

    # Try raw values
    if raw_hash and _try_hmac_validation(raw_dcs, raw_hash, token, "raw"):
        user_data = parsed.get("user")  # Use decoded for JSON parsing
        if user_data:
            return json.loads(user_data)
        return None

    # === Try with bot_id:WebAppData prefix (new Telegram format) ===
    bot_id = token.split(":")[0]
    prefixed_decoded_dcs = f"{bot_id}:WebAppData\n{decoded_dcs}"
    prefixed_raw_dcs = f"{bot_id}:WebAppData\n{raw_dcs}"

    if _try_hmac_validation(prefixed_decoded_dcs, received_hash, token, "prefixed-decoded"):
        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return None

    if raw_hash and _try_hmac_validation(prefixed_raw_dcs, raw_hash, token, "prefixed-raw"):
        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return None

    logger.warning(
        "All validation methods failed | token_len=%d | decoded_keys=%s",
        len(token),
        sorted(parsed.keys()),
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
