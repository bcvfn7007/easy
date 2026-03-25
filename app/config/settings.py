import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    """
    TELEGRAM_TOKEN: str = "your_telegram_bot_token_here"
    OPENROUTER_API_KEY: str = "your_openrouter_api_key_here"
    
    # Comma-separated list of admin Telegram IDs
    ADMIN_IDS: str = ""
    
    # Feature flags
    MONETIZATION_ENABLED: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///easy_english.db"
    
    # File paths
    DATA_DIR: str = "data"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Returns list of integer admin IDs."""
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]

# Instantiate settings singleton to be used across the app
config = Settings()

# Ensure necessary directories exist
os.makedirs(config.DATA_DIR, exist_ok=True)
