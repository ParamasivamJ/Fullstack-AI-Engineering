"""
Level 5 — Environment Management with pydantic-settings
=========================================================

Never hardcode secrets. Never commit .env files.
Always load configuration from environment variables.

pydantic-settings reads environment variables and validates them
with the same power as Pydantic models — types, defaults, and constraints.

WHY this matters:
  - LOCAL dev:    reads from .env file
  - CI/CD:        reads from GitHub Secrets or environment variables
  - Production:   reads from cloud secret manager or container env vars
  - The CODE never changes — only the environment changes

HOW TO RUN:
  pip install pydantic-settings python-dotenv
  Create a .env file (see template at the bottom of this file)
  uvicorn 05_env_management:app --reload
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, PostgresDsn, AnyHttpUrl
from functools import lru_cache
from typing import Literal
from fastapi import FastAPI, Depends


# ─────────────────────────────────────────────
# 1. SETTINGS MODEL
# ─────────────────────────────────────────────

class Settings(BaseSettings):
    """
    All application configuration lives here.
    pydantic-settings reads values from environment variables (case-insensitive).
    If a .env file exists, it reads from that too.
    """

    # ── App settings ──────────────────────────────────────────────
    APP_NAME: str = "FastAPI AI App"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    APP_PORT: int = Field(default=8000, ge=1, le=65535)

    # ── Database ───────────────────────────────────────────────────
    # PostgresDsn validates that this is a valid PostgreSQL connection string
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/appdb"

    # ── Security ───────────────────────────────────────────────────
    # Field(...) means REQUIRED — app will not start without this
    SECRET_KEY: str = Field(..., min_length=32)
    REFRESH_SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=30)

    # ── LLM / AI Settings ──────────────────────────────────────────
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key — required for AI features")
    HUGGINGFACE_API_KEY: str = Field(default="")
    DEFAULT_MODEL: str = "gpt-4o-mini"
    MAX_TOKENS_DEFAULT: int = Field(default=1000, ge=100, le=8000)
    LLM_TIMEOUT_SECONDS: int = Field(default=30, ge=5, le=120)

    # ── Vector DB ──────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    VECTOR_COLLECTION_NAME: str = "documents"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── Rate Limiting ──────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: int = 60      # requests per minute (standard endpoints)
    RATE_LIMIT_AI: int = 10           # requests per minute (AI endpoints — stricter)

    # ── Storage ───────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = Field(default=10, ge=1, le=100)
    # In production: use S3/GCS
    USE_CLOUD_STORAGE: bool = False
    AWS_S3_BUCKET: str = ""
    AWS_REGION: str = "ap-south-1"

    # ── CORS ──────────────────────────────────────────────────────
    # Space-separated list of allowed origins (easy to set as env var)
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parses the space-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # ── Validators ────────────────────────────────────────────────

    @field_validator("APP_ENV")
    @classmethod
    def warn_if_debug_in_production(cls, v: str) -> str:
        return v

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def warn_if_no_openai_key(cls, v: str) -> str:
        if not v:
            print("⚠️  WARNING: OPENAI_API_KEY is not set. AI features will not work.")
        return v

    # ── pydantic-settings config ──────────────────────────────────
    model_config = SettingsConfigDict(
        # Read from a .env file if it exists (great for local development)
        env_file=".env",
        env_file_encoding="utf-8",
        # Variables in actual environment take priority over .env file
        # This is critical for production (container envs override .env)
        case_sensitive=False,  # APP_NAME and app_name are treated the same
        extra="ignore",        # Ignore any env vars not defined here
    )


# ─────────────────────────────────────────────
# 2. SINGLETON PATTERN (load once, reuse everywhere)
# ─────────────────────────────────────────────

@lru_cache()
def get_settings() -> Settings:
    """
    Returns the Settings instance, cached after the first call.

    @lru_cache() ensures the .env file is read ONCE at startup,
    not on every request. This is both fast and correct.

    Usage in routes:
      settings: Settings = Depends(get_settings)
    """
    return Settings()


# Type alias for clean route signatures
from typing import Annotated
SettingsDep = Annotated[Settings, Depends(get_settings)]


# ─────────────────────────────────────────────
# 3. DEMO APP
# ─────────────────────────────────────────────

# Load settings at startup
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    # In production, disable docs endpoints entirely
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url=None,
)


@app.get("/config/public", tags=["Config"])
def get_public_config(s: SettingsDep):
    """
    Returns non-sensitive configuration info.
    NEVER expose SECRET_KEY, API keys, or database passwords through an endpoint.
    """
    return {
        "app_name": s.APP_NAME,
        "environment": s.APP_ENV,
        "default_model": s.DEFAULT_MODEL,
        "max_tokens": s.MAX_TOKENS_DEFAULT,
        "max_file_size_mb": s.MAX_FILE_SIZE_MB,
        "rate_limit_per_minute": s.RATE_LIMIT_DEFAULT,
    }


@app.get("/health", tags=["System"])
def health(s: SettingsDep):
    """Health check that reports the current environment."""
    return {
        "status": "ok",
        "environment": s.APP_ENV,
        "ai_enabled": bool(s.OPENAI_API_KEY),
        "cloud_storage": s.USE_CLOUD_STORAGE,
    }


# ─────────────────────────────────────────────
# .env FILE TEMPLATE
# ─────────────────────────────────────────────
# Create this file as `.env` in your project root.
# Add `.env` to .gitignore — NEVER commit it to git.

ENV_TEMPLATE = """
# ============================================================
# .env — Local Development Configuration
# Copy this to .env and fill in your values
# NEVER commit .env to git!
# ============================================================

APP_NAME=My FastAPI AI App
APP_ENV=development
DEBUG=true
APP_PORT=8000

# Database (local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://aiuser:aipass@localhost:5432/aiapp

# Security — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-32-char-minimum-secret-key-here-change-this
REFRESH_SECRET_KEY=another-different-32-char-secret-key-here

# LLM APIs
OPENAI_API_KEY=sk-...
HUGGINGFACE_API_KEY=hf_...

# Vector DB
QDRANT_URL=http://localhost:6333

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# File uploads
UPLOAD_DIR=uploads
MAX_FILE_SIZE_MB=10
"""
