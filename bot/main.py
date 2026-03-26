"""Hopper Shopper Telegram Bot — entry point."""

import logging
import sys

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
from bot.handlers.callbacks import handle_shop_callback, shop_command
from bot.handlers.commands import (
    add_command,
    clear_command,
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
    BotCommand("shop", "מצב קניות אינטראקטיבי"),
    BotCommand("detail", "שמירת פרטים/מותג לפריט"),
    BotCommand("price", "עדכון מחיר פריט"),
    BotCommand("help", "עזרה"),
]


async def post_init(application: Application) -> None:
    """Clear stale sessions and set bot commands on startup."""
    # Drop any existing webhook / getUpdates session so we don't 409
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Cleared any stale webhook / polling session.")

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


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors globally."""
    global _conflict_count
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
        logger.warning("Network error (will retry): %s", error)
        return

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

    # Build the application with lifecycle hooks
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
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
    app.add_handler(CommandHandler("done", done_command))
    app.add_handler(CommandHandler("undone", undone_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("sort", sort_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("detail", detail_command))
    app.add_handler(CommandHandler("shop", shop_command))

    # ── Callback query handler (shopping mode buttons) ───────────
    app.add_handler(CallbackQueryHandler(handle_shop_callback, pattern=r"^shop:"))

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
    )


if __name__ == "__main__":
    main()
