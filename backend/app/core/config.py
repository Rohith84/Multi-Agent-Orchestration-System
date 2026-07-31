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
    model_name: str = "qwen2.5-coder:7b"
    ollama_timeout: int = 120

    # Agent specific models
    model_planner: str = "llama3.1:8b"
    model_research: str = "llama3.1:8b"
    model_coder: str = "qwen2.5-coder:7b"
    model_tester: str = "qwen2.5-coder:7b"
    model_reviewer: str = "llama3.1:8b"

    # RAG Settings
    vector_db_path: str = "chroma_db"
    embedding_model: str = "nomic-embed-text"

    # AI Assistant
    system_prompt: str = (
        "You are a helpful AI assistant integrated into the Multi Agent Orchestration System. "
        "You provide clear, accurate, and well-structured responses. "
        "When writing code, use proper formatting with markdown code blocks. "
        "Be concise but thorough."
    )

    # MCP Settings
    github_token: str = ""
    mcp_workspace_path: str = str(BASE_DIR.parent)
    mcp_max_timeout: int = 60
    mcp_terminal_timeout: int = 30


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance.
    Uses lru_cache so .env is read only once per process.
    """
    return Settings()
