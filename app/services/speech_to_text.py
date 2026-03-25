import os
import aiohttp
from openai import AsyncOpenAI
import speech_recognition as sr
from app.config.settings import config
from app.utils.logger import setup_logger
import asyncio

logger = setup_logger("speech_to_text")

# If you have a free Whisper-compatible endpoint (like Groq), configure it here
# E.g. WHISPER_API_URL = "https://api.groq.com/openai/v1"
# WHISPER_API_KEY = "your-groq-key"
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "")
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY", "")

async def transcribe_audio(file_path: str) -> str:
    """
    Transcribes audio to text using a Whisper-compatible endpoint if configured.
    Otherwise, falls back to the free Google Speech Recognition API.
    """
    if not os.path.exists(file_path):
        logger.error(f"Audio file to transcribe not found: {file_path}")
        return ""

    if WHISPER_API_KEY and WHISPER_API_URL:
        # Use Whisper Compatible provider
        try:
            client = AsyncOpenAI(api_key=WHISPER_API_KEY, base_url=WHISPER_API_URL)
            with open(file_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-large-v3" if "groq" in WHISPER_API_URL else "whisper-1", 
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            logger.error(f"Whisper STT failed: {e}")
            return ""
            
    # Fallback to free Google STT via SpeechRecognition library
    logger.info("Using free Google Speech Recognition fallback.")
    try:
        # Pydub or similar might be needed to convert OGG to WAV if telegram sends OGG
        # For simplicity, assuming the incoming file is WAV (converted prior)
        recognizer = sr.Recognizer()
        
        # We need a small wrapper because SR is blocking
        def _transcribe():
            with sr.AudioFile(file_path) as source:
                audio_data = recognizer.record(source)
                return recognizer.recognize_google(audio_data)
                
        text = await asyncio.to_thread(_transcribe)
        return text
    except sr.UnknownValueError:
        logger.warning("Google STT could not understand audio")
        return ""
    except Exception as e:
        logger.error(f"Fallback STT error: {e}")
        return ""
