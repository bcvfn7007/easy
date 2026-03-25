from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.utils.logger import setup_logger

logger = setup_logger("settings_handlers")

def get_settings_keyboard(lang: str, is_pro: bool) -> InlineKeyboardMarkup:
    """Generates the inline keyboard for settings."""
    # Rotate language cycle: auto -> ru -> en -> auto
    next_lang = "ru" if lang == "auto" else ("en" if lang == "ru" else "auto")
    lang_display = "Auto" if lang == "auto" else ("Русский" if lang == "ru" else "English")
    
    keyboard = [
        [InlineKeyboardButton(f"🗣 Voice Language: {lang_display}", callback_data=f"set_lang_{next_lang}")]
    ]
    
    if not is_pro:
        keyboard.append([InlineKeyboardButton("⭐ Upgrade to PRO (10 Stars)", callback_data="buy_pro")])
        
    return InlineKeyboardMarkup(keyboard)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the user settings panel."""
    user_id = update.effective_user.id
    user = await models.get_user(user_id)
    
    if not user:
        return await update.message.reply_text("Please use /start to initialize your account first.")
        
    is_pro = bool(user.get("is_pro"))
    lang = await models.get_user_setting(user_id, "tts_language", "auto")
    trial_active = await models.is_trial_active(user_id)
    
    status_text = "⭐ PRO Subscription Active" if is_pro else (
        "✅ 10-Day Free Trial Active" if trial_active else "❌ Free Trial Expired"
    )
    
    msg = (
        "⚙️ *Settings & Account*\n\n"
        f"*Status:* {status_text}\n\n"
        "Customize your bot experience below:"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_settings_keyboard(lang, is_pro),
        parse_mode="Markdown"
    )

async def settings_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles settings inline button clicks."""
    query = update.callback_query
    # We don't always answer immediately if we want to show a popup later, but it's safe to answer blankly.
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    user = await models.get_user(user_id)
    is_pro = bool(user.get("is_pro")) if user else False
    
    if data.startswith("set_lang_"):
        new_lang = data.split("_")[2]
        await models.set_user_setting(user_id, "tts_language", new_lang)
        
        # update keyboard
        try:
            await query.edit_message_reply_markup(reply_markup=get_settings_keyboard(new_lang, is_pro))
        except Exception:
            pass # ignore message not modified error
