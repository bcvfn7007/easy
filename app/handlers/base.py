from telegram import Update
from telegram.ext import ContextTypes
from app.database import models
from app.utils.logger import setup_logger

logger = setup_logger("base_handlers")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    
    # Register or update user in DB
    await models.create_or_update_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or ""
    )
    
    welcome_text = (
        f"Hello {user.first_name} 👋\n\n"
        f"I am Easy English, your AI-powered English tutor and conversation partner.\n"
        f"You can practice your English with me by sending text or voice messages.\n"
        f"I will gently correct any mistakes and help you improve!\n\n"
        f"Send me a message to start our conversation or use /help to see what else I can do."
    )
    await update.message.reply_text(welcome_text)
    logger.info(f"User {user.id} started the bot.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    help_text = (
        "📚 *Easy English Help*\n\n"
        "*Core Features:*\n"
        "• *Text Chat:* Just send me a message in English or your native language. I will correct you and reply in English.\n"
        "• *Voice Chat:* Send me a voice message! I will listen, correct your grammar, and send a voice reply back to you.\n\n"
        "*Commands:*\n"
        "/start - Restart the bot and see the welcome message\n"
        "/help - Show this help menu\n\n"
        "_Tip: Don't be afraid to make mistakes. That's how we learn!_"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
