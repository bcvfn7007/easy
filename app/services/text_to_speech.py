import os
import asyncio
from gtts import gTTS
from pydub import AudioSegment
from app.config.settings import config
from app.utils.logger import setup_logger
import uuid

logger = setup_logger("text_to_speech")

async def generate_speech(text: str, user_id: int) -> str:
    """
    Converts text to speech using gTTS.
    Saves the file to the data directory and returns the file path.
    """
    if not text:
        return ""
        
    # generate a unique filename
    output_filename = f"reply_{user_id}_{uuid.uuid4().hex[:8]}.mp3"
    ogg_filename = output_filename.replace(".mp3", ".ogg")
    
    mp3_path = os.path.join(config.DATA_DIR, output_filename)
    ogg_path = os.path.join(config.DATA_DIR, ogg_filename)
        
    try:
        def _synthesize():
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(mp3_path)
            
            # Telegram requires OGG OPUS for voice notes specifically.
            audio = AudioSegment.from_mp3(mp3_path)
            # libopus codec is commonly required, but format="ogg" is native to PyDub
            audio.export(ogg_path, format="ogg", codec="libopus")
            
            # Clean up the mp3 after converting
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
            
        await asyncio.to_thread(_synthesize)
        return ogg_path
    except Exception as e:
        logger.error(f"gTTS error: {e}")
        return ""
        
async def cleanup_audio_file(file_path: str):
    """Utility to remove the audio file after sending."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Could not delete audio file {file_path}: {e}")
