import asyncio
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, PreCheckoutQueryHandler
)
from app.config.settings import config
from app.database.db import init_db
from app.utils.logger import setup_logger
from app.handlers import (
    start_command, help_command, handle_text_message,
    handle_voice_message, show_text_callback,
    settings_command, settings_callbacks,
    send_invoice_callback, precheckout_callback, successful_payment_callback
)
from app.admin import (
    admin_command, admin_callbacks, stats_command, broadcast_command,
    ban_command, unban_command, toggle_ai_command, toggle_voice_command,
    grant_pro_command, toggle_monetization_command
)

logger = setup_logger("main")

async def init_services():
    """Initializes external dependencies and database."""
    await init_db()

def main():
    if not config.TELEGRAM_TOKEN or config.TELEGRAM_TOKEN.startswith("your_"):
        logger.error("TELEGRAM_TOKEN is missing or not configured in .env!")
        return

    logger.info("Starting Easy English Bot...")

    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Base Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))

    # Admin Handlers
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("toggle_ai", toggle_ai_command))
    application.add_handler(CommandHandler("toggle_voice", toggle_voice_command))
    application.add_handler(CommandHandler("toggle_monetization", toggle_monetization_command))
    application.add_handler(CommandHandler("grant_pro", grant_pro_command))

    # Voice & Text Handlers
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Callback Handlers
    application.add_handler(CallbackQueryHandler(show_text_callback, pattern=r"^show_txt_.*"))
    application.add_handler(CallbackQueryHandler(admin_callbacks, pattern=r"^admin_.*"))
    application.add_handler(CallbackQueryHandler(settings_callbacks, pattern=r"^(set_lang_|set_grammar_|settings_.*)"))
    application.add_handler(CallbackQueryHandler(send_invoice_callback, pattern=r"^buy_pro$"))
    
    # Payments
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # Since we can't easily use await inside synchronous main without altering PTB loop behavior, 
    # we tie our database initialization to post_init hook.
    async def post_init(app):
        await init_services()
        logger.info("Bot is ready and polling.")
        
    application.post_init = post_init

    # Start the Bot
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
