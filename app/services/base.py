from abc import ABC, abstractmethod
from typing import List, Dict

class BaseAIProvider(ABC):
    """Abstract base class for all AI conversational providers."""
    
    @abstractmethod
    async def generate_response(self, user_id: int, history: List[Dict[str, str]], new_message: str, grammar_level: str) -> str:
        """
        Takes conversation history, the new message, and expected grammar level.
        Returns the AI text response.
        """
        pass

class BaseSTTProvider(ABC):
    """Abstract base class for Speech-To-Text providers."""
    
    @abstractmethod
    async def transcribe_audio(self, file_path: str) -> str:
        """Transcribes an audio file and returns the string."""
        pass

class BaseTTSProvider(ABC):
    """Abstract base class for Text-To-Speech providers."""
    
    @abstractmethod
    async def generate_speech(self, text: str, user_id: int, override_lang: str = "auto") -> str:
        """Converts text to speech and returns the file path of the saved audio."""
        pass
