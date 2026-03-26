from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.utils.logger import setup_logger

logger = setup_logger("settings_handlers")

def get_settings_keyboard(grammar_level: str, bot_mode: str, is_pro: bool) -> InlineKeyboardMarkup:
    """Generates the inline keyboard for settings."""
    grammar_levels = ["Beginner", "Intermediate", "Advanced"]
    try:
        current_idx = grammar_levels.index(grammar_level)
        next_grammar = grammar_levels[(current_idx + 1) % len(grammar_levels)]
    except ValueError:
        next_grammar = "Intermediate"

    bot_modes = ["Casual", "IELTS", "Interview", "Travel"]
    try:
        mode_idx = bot_modes.index(bot_mode)
        next_mode = bot_modes[(mode_idx + 1) % len(bot_modes)]
    except ValueError:
        next_mode = "Casual"
    
    keyboard = [
        [InlineKeyboardButton("👤 My Profile", callback_data="settings_profile")],
        [InlineKeyboardButton(f"📚 Grammar Level: {grammar_level}", callback_data=f"set_grammar_{next_grammar}")],
        [InlineKeyboardButton(f"🎭 Roleplay Mode: {bot_mode}", callback_data=f"set_mode_{next_mode}")]
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
    grammar_level = await models.get_user_setting(user_id, "grammar_level", "Intermediate")
    bot_mode = await models.get_user_setting(user_id, "bot_mode", "Casual")
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
        reply_markup=get_settings_keyboard(grammar_level, bot_mode, is_pro),
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
        
    if data.startswith("set_grammar_"):
        new_grammar = data.split("_", 2)[2]
        await models.set_user_setting(user_id, "grammar_level", new_grammar)
        await models.update_user_grammar_level(user_id, new_grammar)
        
    elif data.startswith("set_mode_"):
        new_mode = data.split("_", 2)[2]
        await models.set_user_setting(user_id, "bot_mode", new_mode)
        
    elif data == "settings_profile":
        stats = await models.get_user_stats(user_id)
        trial_active = await models.is_trial_active(user_id)
        
        status_str = "⭐ PRO Subscription" if is_pro else (
            f"✅ {stats['trial_days_left']} Days Trial Left" if trial_active else "❌ Free Trial Expired"
        )
        
        streak = user.get("streak_count", 0) if user else 0
        
        profile_msg = (
            "👤 *Your Profile*\n\n"
            f"📛 *Name:* {update.effective_user.first_name}\n"
            f"🆔 *ID:* `{user_id}`\n\n"
            f"🔥 *Daily Streak:* {streak} Days\n"
            f"💬 *Messages Sent:* {stats['messages_sent']}\n"
            f"👑 *Account Status:* {status_str}\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Settings", callback_data="settings_back")]]
        return await query.edit_message_text(profile_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "settings_back":
        pass 

    # Re-render settings
    grammar_level = await models.get_user_setting(user_id, "grammar_level", "Intermediate")
    bot_mode = await models.get_user_setting(user_id, "bot_mode", "Casual")
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
            reply_markup=get_settings_keyboard(grammar_level, bot_mode, is_pro),
            parse_mode="Markdown"
        )
    except Exception:
        pass
