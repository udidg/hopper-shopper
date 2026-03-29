"""Hopper Shopper Telegram Bot — entry point."""

import asyncio
import logging
import sys

import httpx
from telegram import BotCommand, Update
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from bot.config import settings
from bot.database import dispose_engine
from bot.handlers.callbacks import (
    handle_clear_callback,
    handle_detail_pick_callback,
    handle_list_view_callback,
    handle_quick_add_callback,
    handle_shop_callback,
    shop_command,
)
from bot.handlers.commands import (
    add_command,
    clear_command,
    cleardone_command,
    detail_command,
    done_command,
    help_command,
    list_command,
    price_command,
    remove_command,
    sort_command,
    start_command,
    undone_command,
)
from bot.handlers.inline import handle_inline_query
from bot.handlers.messages import handle_text_message

# ── Logging configuration ────────────────────────────────────────
_log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=_log_level,
)
# Reduce noise from httpx and httpcore
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Bot commands for the Telegram menu
BOT_COMMANDS = [
    BotCommand("add", "הוספת פריטים לרשימה"),
    BotCommand("remove", "הסרת פריט מהרשימה"),
    BotCommand("list", "הצגת הרשימה"),
    BotCommand("sort", "מיון לפי מחלקות"),
    BotCommand("done", "סימון פריט כנקנה"),
    BotCommand("undone", "ביטול סימון"),
    BotCommand("clear", "ניקוי הרשימה"),
    BotCommand("cleardone", "ניקוי פריטים שנקנו"),
    BotCommand("shop", "מצב קניות אינטראקטיבי"),
    BotCommand("detail", "שמירת פרטים/מותג לפריט"),
    BotCommand("price", "עדכון מחיר פריט"),
    BotCommand("help", "עזרה"),
]


async def _force_close_stale_session(token: str) -> None:
    """Force-close any stale polling/webhook session BEFORE building the app.

    The 409 Conflict happens when two ``getUpdates`` long-polls overlap.
    ``delete_webhook`` alone does NOT cancel an in-flight ``getUpdates``.
    Calling ``getUpdates`` with ``offset=-1, timeout=0`` forces Telegram to
    close the previous long-poll, returning immediately.  We do this with a
    raw HTTP call so it happens *before* python-telegram-bot opens its own
    session.
    """
    base = f"https://api.telegram.org/bot{token}"
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. Delete any webhook first
        r = await client.post(f"{base}/deleteWebhook", json={"drop_pending_updates": True})
        logger.info("deleteWebhook response: %s", r.json().get("description", r.text))

        # 2. Force-close any lingering getUpdates long-poll
        r = await client.post(
            f"{base}/getUpdates",
            json={"offset": -1, "limit": 1, "timeout": 0},
        )
        data = r.json()
        if data.get("ok"):
            # Acknowledge the last update so the old session is fully drained
            results = data.get("result", [])
            if results:
                last_id = results[-1]["update_id"]
                await client.post(
                    f"{base}/getUpdates",
                    json={"offset": last_id + 1, "limit": 1, "timeout": 0},
                )
            logger.info("Stale polling session force-closed successfully.")
        else:
            logger.warning("getUpdates pre-clear returned: %s", data)


async def post_init(application: Application) -> None:
    """Set bot commands on startup (session already cleared before build)."""
    global _net_error_count
    _net_error_count = 0  # Reset network backoff — we just connected successfully
    await application.bot.set_my_commands(BOT_COMMANDS)
    logger.info("Bot commands registered in Telegram menu.")


async def post_shutdown(application: Application) -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down — disposing database engine...")
    await dispose_engine()

    # Close the shared httpx client used by the LLM service
    try:
        from bot.services.llm import close_http_client
        await close_http_client()
    except Exception:
        pass

    logger.info("Shutdown complete.")


# Track consecutive conflict errors to decide when to bail out
_conflict_count = 0
_MAX_CONFLICTS = 5

# Track consecutive network errors for exponential backoff
_net_error_count = 0
_NET_BACKOFF_BASE = 1.0   # Start with 1 second
_NET_BACKOFF_MAX = 30.0   # Cap at 30 seconds


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors globally with exponential backoff on network errors.

    Without backoff, python-telegram-bot retries getUpdates immediately after
    a network error, creating a tight loop of failed HTTP requests that can
    saturate a home router's upload pipe and cause internet drops.
    """
    global _conflict_count, _net_error_count
    error = context.error

    if isinstance(error, Conflict):
        _conflict_count += 1
        logger.error(
            "409 Conflict (#%d) — another bot instance is running with the "
            "same token! Stop the other instance and restart.",
            _conflict_count,
        )
        if _conflict_count >= _MAX_CONFLICTS:
            logger.critical(
                "Received %d consecutive 409 Conflict errors. "
                "Shutting down to avoid infinite retry loop. "
                "Resolve the duplicate instance and restart the container.",
                _conflict_count,
            )
            # Graceful shutdown through the application's own mechanism
            if context.application:
                context.application.stop_running()
            else:
                sys.exit(1)
        return

    # Reset conflict counter on any other error (means polling is working)
    _conflict_count = 0

    if isinstance(error, (NetworkError, TimedOut)):
        _net_error_count += 1
        backoff = min(_NET_BACKOFF_BASE * (2 ** (_net_error_count - 1)), _NET_BACKOFF_MAX)
        logger.warning(
            "Network error #%d (backoff %.1fs before retry): %s",
            _net_error_count,
            backoff,
            error,
        )
        # Sleep here to prevent the polling loop from immediately retrying
        # and flooding the router with rapid-fire HTTP requests
        await asyncio.sleep(backoff)
        return

    # Any non-network error means the connection is working — reset backoff
    _net_error_count = 0

    logger.error("Unhandled exception:", exc_info=context.error)

    # Try to notify the user if possible
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ אירעה שגיאה. נסו שוב."
            )
        except Exception:
            pass


def main() -> None:
    """Start the bot."""
    logger.info("Starting Hopper Shopper bot (log_level=%s)...", settings.log_level)

    # ── Force-close any stale polling session BEFORE building the app ──
    # This prevents the 409 Conflict that occurs when a previous instance's
    # getUpdates long-poll is still active (e.g. during container restarts).
    #
    # NOTE: asyncio.run() creates and closes an event loop, which in
    # Python 3.12+ means get_event_loop() will fail afterwards.  We must
    # create a fresh loop so that run_polling() (which calls
    # get_event_loop internally) finds one.
    logger.info("Clearing any stale Telegram polling session...")
    asyncio.run(_force_close_stale_session(settings.telegram_bot_token))

    # Restore a fresh event loop after asyncio.run() closed the previous one.
    # Python 3.12+ no longer auto-creates a loop in get_event_loop().
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Build the application with lifecycle hooks.
    # connection_pool_size limits concurrent HTTP connections to Telegram,
    # preventing connection storms that can overwhelm a home router.
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .connection_pool_size(8)
        .build()
    )

    # ── Error handler ────────────────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Command handlers ─────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_command))
    app.add_handler(CommandHandler("remove", remove_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("cleardone", cleardone_command))
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("undone", undone_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("sort", sort_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("detail", detail_command))
    app.add_handler(CommandHandler("shop", shop_command))

    # ── Callback query handlers ──────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_shop_callback, pattern=r"^shop:"))
    app.add_handler(CallbackQueryHandler(handle_clear_callback, pattern=r"^clear:"))
    app.add_handler(CallbackQueryHandler(handle_quick_add_callback, pattern=r"^qa:"))
    app.add_handler(CallbackQueryHandler(handle_list_view_callback, pattern=r"^lv:"))
    app.add_handler(CallbackQueryHandler(handle_detail_pick_callback, pattern=r"^dt:"))

    # ── Inline query handler (suggestions) ───────────────────────
    app.add_handler(InlineQueryHandler(handle_inline_query))

    # ── Message handler (auto-detect grocery lists) ──────────────
    # Must be last — catches all text messages not handled by commands
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_message,
        )
    )

    logger.info("Bot is ready! Starting polling...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        # ── Network-friendly polling parameters ──────────────────
        # poll_interval: seconds between getUpdates calls (default 0.0).
        # Setting to 1.0 prevents a tight loop that floods the router
        # with rapid HTTP requests when the network is healthy.
        poll_interval=1.0,
        # timeout: Telegram long-poll timeout in seconds (default 10).
        # This is how long the server holds the connection open waiting
        # for new updates. 15s is a good balance between responsiveness
        # and connection efficiency.
        timeout=15,
        # read_timeout: max seconds to wait for a response from Telegram.
        # Must be > timeout to avoid false timeouts during long-polls.
        read_timeout=20,
        # connect_timeout: max seconds to establish a TCP connection.
        connect_timeout=10,
        # write_timeout: max seconds to send the request body.
        write_timeout=10,
    )


if __name__ == "__main__":
    main()
