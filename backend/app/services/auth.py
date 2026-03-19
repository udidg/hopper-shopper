"""Telegram initData validation and JWT token management."""

import base64
import hashlib
import hmac
import json
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

logger = logging.getLogger(__name__)

# Telegram's public key for Ed25519 signature verification
# From: https://core.telegram.org/bots/webapps#validating-data-for-third-party-use
TELEGRAM_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAxBmr1v2hEb/xyRiSGf5MrjfEo1DnFBBEiLAECWFMbCQ=
-----END PUBLIC KEY-----"""


def _validate_via_signature(init_data: str, parsed: dict, signature_b64: str) -> bool:
    """
    Validate using Ed25519 signature (new Telegram method).
    
    The data-check-string is:
    <bot_id>:WebAppData\n<sorted key=value pairs excluding hash and signature>
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
    except ImportError:
        logger.warning("cryptography library not available for Ed25519 validation")
        return False

    try:
        bot_id = settings.telegram_bot_token.split(":")[0]
        
        # Build data-check-string with bot_id:WebAppData prefix
        sorted_pairs = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        data_check_string = f"{bot_id}:WebAppData\n{sorted_pairs}"
        
        # Decode the base64url signature
        # Add padding if needed
        sig_padded = signature_b64 + "=" * (4 - len(signature_b64) % 4) if len(signature_b64) % 4 else signature_b64
        signature_bytes = base64.urlsafe_b64decode(sig_padded)
        
        # Load the public key
        public_key = load_pem_public_key(TELEGRAM_PUBLIC_KEY_PEM.encode())
        
        # Verify the signature
        public_key.verify(signature_bytes, data_check_string.encode())
        
        logger.info("Telegram initData validated successfully via Ed25519 signature")
        return True
    except Exception as e:
        logger.debug("Ed25519 signature validation failed: %s", str(e))
        return False


def _validate_via_hmac(data_check_string: str, received_hash: str, token: str) -> bool:
    """Validate using HMAC-SHA256 hash (classic Telegram method)."""
    # Standard method: secret_key = HMAC_SHA256("WebAppData", <bot_token>)
    secret_key = hmac.new(
        b"WebAppData", token.encode(), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(computed_hash, received_hash):
        logger.info("Telegram initData validated successfully via HMAC hash")
        return True

    return False


def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram Web App initData.

    Supports both validation methods:
    1. Ed25519 signature (new, recommended by Telegram)
    2. HMAC-SHA256 hash (classic method)

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Returns the parsed user dict if valid, None otherwise.
    """
    token = settings.telegram_bot_token

    # Parse the raw query string into key=value pairs (URL-decoded)
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

    received_hash = parsed.pop("hash", None)
    signature = parsed.pop("signature", None)

    # === Method 1: Ed25519 signature validation (preferred) ===
    if signature:
        if _validate_via_signature(init_data, parsed, signature):
            user_data = parsed.get("user")
            if user_data:
                return json.loads(user_data)
            return None

    # === Method 2: HMAC-SHA256 hash validation (classic) ===
    if received_hash:
        # Build data-check-string (sorted key=value pairs, URL-decoded)
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        if _validate_via_hmac(data_check_string, received_hash, token):
            user_data = parsed.get("user")
            if user_data:
                return json.loads(user_data)
            return None

    logger.warning(
        "All validation methods failed | token_len=%d | has_signature=%s | has_hash=%s | keys=%s",
        len(token),
        bool(signature),
        bool(received_hash),
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
