import os
import aiohttp
from openai import AsyncOpenAI
import speech_recognition as sr
from app.config.settings import config
from app.utils.logger import setup_logger
from pydub import AudioSegment
import asyncio
from app.services.base import BaseSTTProvider

logger = setup_logger("speech_to_text")

WHISPER_API_URL = os.getenv("WHISPER_API_URL", "")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY", "")

class WhisperSTT(BaseSTTProvider):
    """Whisper API compatible STT implementation (e.g. via Groq or OpenAI)."""
    
    def __init__(self, api_key: str, base_url: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = "whisper-large-v3" if "groq" in base_url else "whisper-1"

    async def transcribe_audio(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
            
        try:
            with open(file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model=self.model, 
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            logger.error(f"Whisper STT failed: {e}")
            return ""

class GoogleSTT(BaseSTTProvider):
    """Free Google STT fallback implementation using speech_recognition."""
    
    async def transcribe_audio(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return ""
            
        wav_path = file_path
        if file_path.endswith(".ogg"):
            wav_path = file_path.replace(".ogg", ".wav")
            try:
                def _convert():
                    audio = AudioSegment.from_ogg(file_path)
                    audio.export(wav_path, format="wav")
                await asyncio.to_thread(_convert)
            except Exception as e:
                logger.error(f"Failed to convert OGG to WAV: {e}")
                return ""

        logger.info("Using free Google Speech Recognition fallback.")
        try:
            recognizer = sr.Recognizer()
            def _transcribe():
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                    return recognizer.recognize_google(audio_data)
                    
            text = await asyncio.to_thread(_transcribe)
            
            if wav_path != file_path and os.path.exists(wav_path):
                os.remove(wav_path)
                
            return text
        except sr.UnknownValueError:
            logger.warning("Google STT could not understand audio")
            return ""
        except Exception as e:
            logger.error(f"Fallback STT error: {e}")
            return ""
