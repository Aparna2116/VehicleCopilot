"""
Application configuration.

All settings are loaded from environment variables (see .env.example).
Keeping this centralized means every service reads config the same way,
and swapping environments (local / staging / prod) is just an env change.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "AutoExplain AI"
    ENV: Literal["local", "staging", "production"] = "local"
    DEBUG: bool = True

    # --- LLM provider (interchangeable — see services/llm_provider.py) ---
    LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    LLM_MODEL: str = "claude-sonnet-4-6"

    # --- OCR ---
    OCR_ENGINE: Literal["tesseract", "paddleocr"] = "tesseract"

    # --- Database / RAG (Slice 2 turns this on for persistence too) ---
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/autoexplain"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # --- Upload limits ---
    MAX_UPLOAD_MB: int = 15
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".png", ".jpg", ".jpeg", ".heic"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
