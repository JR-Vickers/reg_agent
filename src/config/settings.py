"""Application configuration management."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Database
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: Optional[str] = None

    # AI/ML
    openai_api_key: str

    # External APIs
    federal_register_api_key: Optional[str] = None

    # Redis (for task queue)
    redis_url: str = "redis://localhost:6379"

    # Application
    env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    port: int = 8000
    secret_key: str = "dev-secret-key"

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "https://regagent-frontend-production.up.railway.app"
    ]

    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("debug", pre=True)
    def parse_debug(cls, v):
        """Parse debug boolean from string."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL with fallback logic."""
    if settings.database_url:
        return settings.database_url

    # Construct from Supabase components if direct URL not provided
    if settings.supabase_url:
        # Extract project and construct database URL
        # Format: https://project.supabase.co -> postgresql://postgres:password@db.project.supabase.co:5432/postgres
        project = settings.supabase_url.split("//")[1].split(".")[0]
        return f"postgresql://postgres:[password]@db.{project}.supabase.co:5432/postgres"

    raise ValueError("DATABASE_URL or SUPABASE_URL must be provided")


def is_production() -> bool:
    """Check if running in production environment."""
    return settings.env.lower() == "production"


def get_log_config() -> dict:
    """Get logging configuration."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            },
        },
        "handlers": {
            "console": {
                "level": settings.log_level,
                "class": "logging.StreamHandler",
                "formatter": "standard" if is_production() else "detailed",
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
    }