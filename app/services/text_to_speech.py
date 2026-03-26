import os
import asyncio
from gtts import gTTS
from pydub import AudioSegment
from app.config.settings import config
from app.utils.logger import setup_logger
from app.services.base import BaseTTSProvider
import uuid
import re

logger = setup_logger("text_to_speech")

class GTTSTTS(BaseTTSProvider):
    """Google TTS free implementation."""
    
    async def generate_speech(self, text: str, user_id: int, override_lang: str = "auto") -> str:
        if not text:
            return ""
            
        output_filename = f"reply_{user_id}_{uuid.uuid4().hex[:8]}.mp3"
        ogg_filename = output_filename.replace(".mp3", ".ogg")
        
        mp3_path = os.path.join(config.DATA_DIR, output_filename)
        ogg_path = os.path.join(config.DATA_DIR, ogg_filename)
            
        try:
            def _synthesize():
                if override_lang in ["en", "ru"]:
                    lang = override_lang
                else:
                    lang = "ru" if re.search(r'[А-Яа-я]', text) else "en"
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(mp3_path)
                
                audio = AudioSegment.from_mp3(mp3_path)
                audio.export(ogg_path, format="ogg", codec="libopus")
                
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
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Could not delete audio file {file_path}: {e}")
