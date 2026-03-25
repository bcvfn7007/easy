from telegram import Update
from telegram.ext import ContextTypes
from app.database import models
from app.services import ai_provider
from app.utils.logger import setup_logger

logger = setup_logger("text_handlers")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
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
    
    # Retrieve history
    history = await models.get_message_history(user_id, limit=6) # Get last 6 interactions
    
    # Ask AI provider for reply
    ai_reply = await ai_provider.generate_response(user_id, history, user_text)
    
    # Save AI reply
    await models.add_message_to_history(user_id, 'assistant', ai_reply)
    
    # Send to user
    await update.message.reply_text(ai_reply)
