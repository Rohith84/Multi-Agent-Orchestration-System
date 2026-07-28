"""
Application configuration using Pydantic Settings.

Loads values from environment variables and .env file.
All config is centralized here for clean architecture.
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Multi Agent Orchestration System"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:rohith2007@localhost:5432/multi_agent_db"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Ollama
    ollama_base_url: str = "http://localhost:11434"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Uses lru_cache so .env is read only once per process.
    """
    return Settings()
