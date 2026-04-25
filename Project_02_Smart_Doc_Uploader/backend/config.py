"""
Project 02 — Smart Document Uploader: Configuration
=====================================================
All settings loaded from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Smart Document Uploader"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # Database (PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql+asyncpg://appuser:apppass@localhost:5432/docuploader"
    SYNC_DATABASE_URL: str = "postgresql://appuser:apppass@localhost:5432/docuploader"

    # File uploads
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = Field(default=10, ge=1, le=100)
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt"

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    # Embedding model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Chunking
    CHUNK_SIZE: int = Field(default=512, ge=100, le=2000)
    CHUNK_OVERLAP_SENTENCES: int = Field(default=2, ge=0, le=5)

    # Search
    DEFAULT_TOP_K: int = 5
    DEFAULT_SCORE_THRESHOLD: float = 0.3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
