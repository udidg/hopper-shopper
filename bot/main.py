"""Hopper Shopper Telegram Bot — entry point."""

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from bot.config import settings
from bot.handlers.callbacks import handle_shop_callback, shop_command
from bot.handlers.commands import (
    add_command,
    clear_command,
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

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    logger.info("Starting Hopper Shopper bot...")

    # Build the application
    app = Application.builder().token(settings.telegram_bot_token).build()

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
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
