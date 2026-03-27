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
    pass # Deprecated by JSON structured payloads

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

    # Check Streaks
    await models.update_user_activity(user_id)
    
    # Calculate WPM
    duration = update.message.voice.duration
    word_count = len(transcription.split())
    wpm = int((word_count / duration) * 60) if duration > 0 else 0
    wpm_msg = f"\n\n🗣️ *Speaking Fluency:* {wpm} WPM"
    
    # Step 2: AI Response
    grammar_level = await models.get_user_setting(user_id, "grammar_level", "Intermediate")
    bot_mode = await models.get_user_setting(user_id, "bot_mode", "Casual")
    
    ai_reply_dict = await ai_service.generate_response(user_id, history, transcription, grammar_level, bot_mode)
    correction = ai_reply_dict.get("correction_short", "")
    explanation = ai_reply_dict.get("explanation", "")
    english_reply = ai_reply_dict.get("english_reply", "")
    
    # Append WPM to the text that the user reads in the Callback (Not what is sent to TTS)
    english_reply_with_wpm = f"{english_reply}\n\n🗣️ *Speaking Fluency:* {wpm} WPM"
    
    msg_id = await models.add_message_to_history(
        user_id, 'assistant', 
        correction or "Perfect", 
        explanation, 
        english_reply_with_wpm
    )

    if correction:
        keyboard = [[InlineKeyboardButton("Объяснить 📋", callback_data=f"explain_{msg_id}")]]
        await update.message.reply_text(correction, reply_markup=InlineKeyboardMarkup(keyboard))

    # Check trial and pro status
    trial_active = await models.is_trial_active(user_id)
    is_pro = bool(user.get("is_pro")) if user else False
    
    # Step 3: Generate TTS
    if is_pro or trial_active:
        # Generate TTS strictly from the english string
        tts_text = english_reply if english_reply else "Keep up the great work! Let's continue practicing."
            
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
            await update.message.reply_text(english_reply_with_wpm)
    else:
        # Fallback to Text for expired free users
        keyboard = [[InlineKeyboardButton("⭐ Upgrade to PRO to hear voice", callback_data="buy_pro")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg_text = f"*(Trial Expired: Voice Replies Disabled)*\n\n{english_reply_with_wpm}"
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")

async def get_message_content_by_id(msg_id: int) -> dict:
    """Helper to fetch message components from DB."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT content, explanation, english_text FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def show_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback for 'Show Text' and 'Explain' buttons."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    try:
        if data.startswith("show_txt_"):
            msg_id = int(data.replace("show_txt_", ""))
        elif data.startswith("explain_"):
            msg_id = int(data.replace("explain_", ""))
            
        msg_data = await get_message_content_by_id(msg_id)
    except Exception:
        return
        
    if not msg_data:
        return await context.bot.send_message(chat_id=update.effective_chat.id, text="Message expired from database.")
        
    if data.startswith("show_txt_"):
        try:
            english_text = msg_data.get('english_text', '') or msg_data.get('content', '')
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=english_text,
                reply_to_message_id=query.message.message_id
            )
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            
    elif data.startswith("explain_"):
        explanation = msg_data.get('explanation', '')
        if explanation:
            new_text = f"{query.message.text}\n\n*Объяснение:*\n{explanation}"
            try:
                await query.edit_message_text(new_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Explanation edit error: {e}")
