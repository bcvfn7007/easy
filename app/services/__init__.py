import os
from .ai_provider import OpenRouterAI
from .speech_to_text import WhisperSTT, GoogleSTT, WHISPER_API_KEY, WHISPER_API_URL
from .text_to_speech import GTTSTTS, cleanup_audio_file

# Singleton Instantiation Point for Dependency Injection
ai_service = OpenRouterAI()

if WHISPER_API_KEY and WHISPER_API_URL:
    stt_service = WhisperSTT(api_key=WHISPER_API_KEY, base_url=WHISPER_API_URL)
else:
    stt_service = GoogleSTT()

tts_service = GTTSTTS()

__all__ = ["ai_service", "stt_service", "tts_service", "cleanup_audio_file"]
