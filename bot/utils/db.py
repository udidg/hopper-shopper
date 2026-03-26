"""Reusable database session helpers with retry logic and guard utilities."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.exc import DisconnectionError, OperationalError

from bot.database import async_session

logger = logging.getLogger(__name__)

# Transient DB errors worth retrying
_RETRYABLE = (OperationalError, DisconnectionError, OSError, ConnectionError)

_MAX_RETRIES = 2
_RETRY_BACKOFF = 0.5  # seconds


@asynccontextmanager
async def db_session_with_retry(
    max_retries: int = _MAX_RETRIES,
    backoff: float = _RETRY_BACKOFF,
) -> AsyncGenerator:
    """Async context manager that provides a DB session with automatic retry.

    On transient connection errors (OperationalError, DisconnectionError),
    the entire block is NOT re-executed (generators can only yield once).
    Instead, the retry logic applies to session creation and connection
    acquisition. If the connection fails, it retries before yielding.

    Once the session is yielded, any errors during the caller's work
    propagate normally (no retry on application-level errors).

    Usage::

        async with db_session_with_retry() as session:
            # do DB work — session.begin() is already active
            ...
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            async with async_session() as session:
                async with session.begin():
                    # Test the connection is alive before yielding
                    await session.connection()
                    yield session
                    return
        except _RETRYABLE as exc:
            last_error = exc
            if attempt < max_retries:
                wait = backoff * (2 ** attempt)
                logger.warning(
                    "Transient DB error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    max_retries + 1,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "DB error persisted after %d attempts: %s",
                    max_retries + 1,
                    exc,
                )
                raise
        except GeneratorExit:
            # Context manager is being closed normally
            return

    # Should not reach here, but just in case
    if last_error:
        raise last_error
