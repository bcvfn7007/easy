from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.utils.logger import setup_logger

logger = setup_logger("base_handlers")

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Returns the persistent bottom keyboard for users."""
    keyboard = [
        ["⚙️ Settings", "❓ Help"],
        ["⭐ Upgrade to PRO"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

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
        "📚 *Easy English Tutor - Help Guide*\n\n"
        "💡 *How to use me:*\n"
        "• *Text Chat:* Send me a message! I will correct any mistakes you make, explain the grammar rule in your native language, and reply back in English.\n"
        "• *Voice Chat:* Send me a voice note! I will listen, transcribe, and correct you via a text message, followed instantly by a pure English voice note to train your listening skills.\n\n"
        "⚙️ *Settings & Customization (Use /settings):*\n"
        "• *Grammar Level:* Adjust how strictly I correct you (Beginner, Intermediate, Advanced).\n"
        "• *My Profile:* Track your learning progress, message counts, and trial status.\n\n"
        "👑 *Trial & PRO:*\n"
        "You get a *15-day full-access free trial*! After that, you can upgrade to PRO using Telegram Stars (10 ⭐) for unlimited voice and AI features.\n\n"
        "*Useful Commands:*\n"
        "/start - Restart the bot\n"
        "/help - Show this guide\n"
        "/settings - Open the interactive settings panel\n\n"
        "_Tip: Don't be afraid to make mistakes. That's how we learn!_"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
