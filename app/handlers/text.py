from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.services import ai_service
from app.utils.logger import setup_logger
from app.utils.rate_limiter import is_rate_limited

logger = setup_logger("text_handlers")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Intercept persistent keyboard buttons
    if user_text == "⚙️ Settings":
        from .settings import settings_command
        return await settings_command(update, context)
    elif user_text == "❓ Help":
        from .base import help_command
        return await help_command(update, context)
    elif user_text == "⭐ Upgrade to PRO":
        from .payments import send_pro_invoice_to_user
        return await send_pro_invoice_to_user(context, update.effective_chat.id)
    
    if is_rate_limited(user_id, cooldown_seconds=3.0):
        return await update.message.reply_text("⏳ Please wait a few seconds before sending another message.")
    
    # Check if user exists and is allowed to use AI
    user = await models.get_user(user_id)
    if not user:
        await models.create_or_update_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
        user = await models.get_user(user_id)
        
    if not user.get('ai_enabled'):
        return await update.message.reply_text("Your AI access has been disabled by the administrator.")

    # Send a typing action using context bot
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Save user message
    await models.add_message_to_history(user_id, 'user', user_text)
    
    # Check trial and pro status
    trial_active = await models.is_trial_active(user_id)
    is_pro = bool(user.get("is_pro")) if user else False
    
    # Retrieve history (Limit context memory for expired free users)
    history_limit = 6 if (is_pro or trial_active) else 2
    history = await models.get_message_history(user_id, limit=history_limit) # Get last 6 interactions
    
    # Update Daily Streak & Stats
    await models.update_user_activity(user_id)
    
    # Ask AI provider for reply
    grammar_level = await models.get_user_setting(user_id, "grammar_level", "Intermediate")
    bot_mode = await models.get_user_setting(user_id, "bot_mode", "Casual")
    
    ai_reply_dict = await ai_service.generate_response(user_id, history, user_text, grammar_level, bot_mode)
    correction = ai_reply_dict.get("correction_short", "")
    explanation = ai_reply_dict.get("explanation", "")
    english_reply = ai_reply_dict.get("english_reply", "")
    
    # Save to history
    msg_id = await models.add_message_to_history(
        user_id, 'assistant', 
        correction or "Perfect", 
        explanation, 
        english_reply
    )
    
    # Send short correction if a mistake was made
    if correction:
        keyboard = [[InlineKeyboardButton("Объяснить 📋", callback_data=f"explain_{msg_id}")]]
        await update.message.reply_text(correction, reply_markup=InlineKeyboardMarkup(keyboard))
        
    # Send english reply text
    await update.message.reply_text(english_reply)
