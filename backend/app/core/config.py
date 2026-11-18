"""
Core Application Configuration
Loads environment variables from .env using Pydantic Settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings class.
    Each attribute corresponds to an environment variable in the .env file.
    If an environment variable is present, Pydantic overrides the default value.
    """

    # Application Info
    APP_NAME: str = "ResumeRAG"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Google Gemini API Key
    GEMINI_API_KEY: str = ""

    # ChromaDB Vector Store Settings
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "resume_job_docs"

    # AI Model Settings
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    LLM_MODEL: str = "gemini-1.5-flash"

    # Relational Database (SQLAlchemy) Settings
    # Default is local SQLite for seamless setup; can be swapped for PostgreSQL in .env
    DATABASE_URL: str = "sqlite:///./resumerag.db"

    # Pydantic v2 Settings configuration:
    # - env_file: Look for a file named .env in the current working directory
    # - env_file_encoding: UTF-8 encoding support
    # - extra: 'ignore' silently ignores unknown variables in .env without raising an error
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of application settings.
    
    Why @lru_cache?
    Reading files from a hard drive (.env) is a slow I/O operation.
    With @lru_cache, Python loads and validates the settings once,
    stores the resulting object in RAM, and returns the exact same
    cached object on every subsequent call.
    """
    return Settings()
