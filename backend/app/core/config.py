import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve backend root path to accurately locate .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    # App Settings
    ENVIRONMENT: str = "development"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # MongoDB Atlas
    MONGO_URI: str
    DB_NAME: str = "personal_life_os"

    # AI & LangChain
    GEMINI_API_KEY: str

    # Gmail Worker
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    POLL_INTERVAL_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global singleton instance
settings = Settings()