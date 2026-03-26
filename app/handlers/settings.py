from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.utils.logger import setup_logger

logger = setup_logger("settings_handlers")

def get_settings_keyboard(lang: str, grammar_level: str, is_pro: bool) -> InlineKeyboardMarkup:
    """Generates the inline keyboard for settings."""
    next_lang = "ru" if lang == "auto" else ("en" if lang == "ru" else "auto")
    lang_display = "Auto" if lang == "auto" else ("Русский" if lang == "ru" else "English")
    
    grammar_levels = ["Beginner", "Intermediate", "Advanced"]
    try:
        current_idx = grammar_levels.index(grammar_level)
        next_grammar = grammar_levels[(current_idx + 1) % len(grammar_levels)]
    except ValueError:
        next_grammar = "Intermediate"
    
    keyboard = [
        [InlineKeyboardButton("👤 My Profile", callback_data="settings_profile")],
        [
            InlineKeyboardButton(f"🗣 Voice: {lang_display}", callback_data=f"set_lang_{next_lang}"),
            InlineKeyboardButton(f"📚 Grammar: {grammar_level}", callback_data=f"set_grammar_{next_grammar}")
        ]
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
    grammar_level = await models.get_user_setting(user_id, "grammar_level", "Intermediate")
    trial_active = await models.is_trial_active(user_id)
    
    status_text = "⭐ PRO" if is_pro else (
        "✅ Trial Active" if trial_active else "❌ Trial Expired"
    )
    
    msg = (
        "⚙️ *Settings & Preferences*\n\n"
        f"*Status:* {status_text}\n\n"
        "Customize your bot experience below:"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_settings_keyboard(lang, grammar_level, is_pro),
        parse_mode="Markdown"
    )

async def settings_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles settings inline button clicks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    user = await models.get_user(user_id)
    is_pro = bool(user.get("is_pro")) if user else False
    
    if data.startswith("set_lang_"):
        new_lang = data.split("_", 2)[2]
        await models.set_user_setting(user_id, "tts_language", new_lang)
        
    elif data.startswith("set_grammar_"):
        new_grammar = data.split("_", 2)[2]
        await models.set_user_setting(user_id, "grammar_level", new_grammar)
        await models.update_user_grammar_level(user_id, new_grammar)
        
    elif data == "settings_profile":
        stats = await models.get_user_stats(user_id)
        trial_active = await models.is_trial_active(user_id)
        
        status_str = "⭐ PRO Subscription" if is_pro else (
            f"✅ {stats['trial_days_left']} Days Trial Left" if trial_active else "❌ Free Trial Expired"
        )
        
        profile_msg = (
            "👤 *Your Profile*\n\n"
            f"📛 *Name:* {update.effective_user.first_name}\n"
            f"🆔 *ID:* `{user_id}`\n\n"
            f"💬 *Messages Sent:* {stats['messages_sent']}\n"
            f"👑 *Account Status:* {status_str}\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back")]]
        return await query.edit_message_text(profile_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "settings_back":
        pass 

    # Re-render settings
    lang = await models.get_user_setting(user_id, "tts_language", "auto")
    grammar_level = await models.get_user_setting(user_id, "grammar_level", "Intermediate")
    trial_active = await models.is_trial_active(user_id)
    
    status_text = "⭐ PRO" if is_pro else (
        "✅ Trial Active" if trial_active else "❌ Trial Expired"
    )
    
    msg = (
        "⚙️ *Settings & Preferences*\n\n"
        f"*Status:* {status_text}\n\n"
        "Customize your bot experience below:"
    )
    
    try:
        await query.edit_message_text(
            msg, 
            reply_markup=get_settings_keyboard(lang, grammar_level, is_pro),
            parse_mode="Markdown"
        )
    except Exception:
        pass
