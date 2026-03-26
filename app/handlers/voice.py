import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.services import ai_service, stt_service, tts_service, cleanup_audio_file
from app.config.settings import config
from app.utils.logger import setup_logger
from app.utils.rate_limiter import is_rate_limited
import aiosqlite
from app.database.db import get_db

logger = setup_logger("voice_handlers")

def extract_conversational_text(full_text: str) -> str:
    """Removes the correction blocks so the TTS only reads the conversational part."""
    lines = full_text.split('\n')
    tts_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('❌', '✅', '💡')):
            continue
        tts_lines.append(line)
    return '\n'.join(tts_lines).strip()

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_rate_limited(user_id, cooldown_seconds=5.0):
        return await update.message.reply_text("⏳ Processing voice takes time. Please wait a bit before sending another!")
    
    # Authorization checks
    user = await models.get_user(user_id)
    if not user:
        await models.create_or_update_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
        user = await models.get_user(user_id)
        
    if not user.get('ai_enabled') or not user.get('voice_enabled'):
        return await update.message.reply_text("Your voice AI access is currently disabled.")

    # Download Voice Note
    voice_file_tg = await context.bot.get_file(update.message.voice.file_id)
    download_path = os.path.join(config.DATA_DIR, f"voice_{user_id}_{update.message.voice.file_unique_id}.ogg")
    
    await voice_file_tg.download_to_drive(download_path)
    await update.message.reply_chat_action(action='record_voice')

    # Step 1: STT
    transcription = await stt_service.transcribe_audio(download_path)
    await cleanup_audio_file(download_path)
    
    if not transcription:
         return await update.message.reply_text("Sorry, I couldn't hear what you said clearly. Could you try again?")

    # Save user transcription to DB history
    await models.add_message_to_history(user_id, 'user', f"[Voice Message] {transcription}")
    history = await models.get_message_history(user_id, limit=6)
    
    # Step 2: AI Response
    grammar_level = await models.get_user_setting(user_id, "grammar_level", "Intermediate")
    ai_reply = await ai_service.generate_response(user_id, history, transcription, grammar_level)
    
    # Save bot reply and get msg_id for the Show Text button lookup
    msg_id = await models.add_message_to_history(user_id, 'assistant', ai_reply)

    # Check trial and pro status
    trial_active = await models.is_trial_active(user_id)
    is_pro = bool(user.get("is_pro")) if user else False
    
    # Step 3: Generate TTS
    if is_pro or trial_active:
        # Only TTS the natural English conversational text!
        tts_text = extract_conversational_text(ai_reply)
        if not tts_text:
            tts_text = "Keep up the great work! Let's continue practicing."
            
        tts_audio_path = await tts_service.generate_speech(tts_text, user_id, "en")  # Hardware enforced to 'en'
        
        # Send Voice with Show Text Button
        if tts_audio_path:
            keyboard = [[InlineKeyboardButton("💬 Show Text", callback_data=f"show_txt_{msg_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                with open(tts_audio_path, 'rb') as audio_payload:
                    await update.message.reply_voice(voice=audio_payload, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Failed to send voice payload: {e}")
            finally:
                await cleanup_audio_file(tts_audio_path)
        else:
            await update.message.reply_text(ai_reply)
    else:
        # Fallback to Text for expired free users
        keyboard = [[InlineKeyboardButton("⭐ Upgrade to PRO to hear voice", callback_data="buy_pro")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = f"*(Trial Expired: Voice Replies Disabled)*\n\n{ai_reply}"
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")

async def get_message_content_by_id(msg_id: int) -> str:
    """Helper to fetch exact ai completion from DB for the Show Text button."""
    async with get_db() as db:
        async with db.execute("SELECT content FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "Message not found."

async def show_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback for 'Show Text' button on voice messages."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("show_txt_"):
        try:
            msg_id = int(data.replace("show_txt_", ""))
            content = await get_message_content_by_id(msg_id)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=content,
                reply_to_message_id=query.message.message_id
            )
            # Remove the button so they don't click it again
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Could not retrieve transcript.")
