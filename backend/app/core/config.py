"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: str = "development"
    debug: bool = True
    secret_key: str = "change_me_in_production_please"

    # Database
    database_url: str = "postgresql+asyncpg://budgetbo:budgetbo_secret@localhost:5432/budgetbo"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout: int = 120

    # Encryption
    encryption_key: str = "generate_a_32_byte_key_for_fernet_"

    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

    # Frontend
    frontend_url: str = "http://localhost:3000"  # Override with FRONTEND_URL env var in production

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Celery workers (psycopg2)."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()