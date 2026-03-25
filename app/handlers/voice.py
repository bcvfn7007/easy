import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import models
from app.services import ai_provider, speech_to_text, text_to_speech
from app.config.settings import config
from app.utils.logger import setup_logger
import aiosqlite
from app.database.db import get_db

logger = setup_logger("voice_handlers")

async def get_message_content_by_id(msg_id: int) -> str:
    """Helper to fetch exact ai completion from DB for the Show Text button."""
    async with get_db() as db:
        async with db.execute("SELECT content FROM messages WHERE id = ?", (msg_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "Message not found."

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Authorization checks
    user = await models.get_user(user_id)
    if not user:
        await models.create_or_update_user(user_id, update.effective_user.username or "", update.effective_user.first_name or "")
        user = await models.get_user(user_id)
        
    if not user.get('ai_enabled') or not user.get('voice_enabled'):
        return await update.message.reply_text("Your voice AI access is currently disabled.")

    # Download Voice Note
    # Telegram sends voice notes usually in OGG OPUS format
    voice_file_tg = await context.bot.get_file(update.message.voice.file_id)
    download_path = os.path.join(config.DATA_DIR, f"voice_{user_id}_{update.message.voice.file_unique_id}.ogg")
    
    await voice_file_tg.download_to_drive(download_path)
    
    await update.message.reply_chat_action(action='record_voice')

    # Step 1: STT
    transcription = await speech_to_text.transcribe_audio(download_path)
    # Cleanup original user audio
    await text_to_speech.cleanup_audio_file(download_path)
    
    if not transcription:
         return await update.message.reply_text("Sorry, I couldn't hear what you said clearly. Could you try again?")

    # Save user transcription to DB history
    await models.add_message_to_history(user_id, 'user', f"[Voice Message] {transcription}")
    
    # Retrieve history
    history = await models.get_message_history(user_id, limit=6)
    
    # Step 2: AI Response
    ai_reply = await ai_provider.generate_response(user_id, history, transcription)
    
    # Save bot reply and get the msg_id for the callback!
    msg_id = await models.add_message_to_history(user_id, 'assistant', ai_reply)

    # Step 3: TTS
    tts_audio_path = await text_to_speech.generate_speech(ai_reply, user_id)
    
    if not tts_audio_path:
        # Fallback to Text if TTS fails
        return await update.message.reply_text(f"*(Audio generation failed)*\n\n{ai_reply}", parse_mode="Markdown")
        
    # Send Voice with "Show Text" Button
    keyboard = [[InlineKeyboardButton("💬 Show Text", callback_data=f"show_txt_{msg_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        with open(tts_audio_path, 'rb') as audio_payload:
            await update.message.reply_voice(
                voice=audio_payload,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Failed to send voice payload: {e}")
        await update.message.reply_text("There was an error sending the audio back to you.", parse_mode="Markdown")
    finally:
        # Step 4: Cleanup File
        await text_to_speech.cleanup_audio_file(tts_audio_path)


async def show_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback for 'Show Text' button on voice messages."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("show_txt_"):
        try:
            msg_id = int(data.replace("show_txt_", ""))
            content = await get_message_content_by_id(msg_id)
            
            # Since editing the audio's caption or sending a new message may be desired:
            # Re-sending the original AI text response below the audio is cleaner because voice messages can't easily have long captions
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📝 Transcript:\n{content}",
                reply_to_message_id=query.message.message_id
            )
            # Remove the button so they don't click it again
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Could not retrieve transcript.")
