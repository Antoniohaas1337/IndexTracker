"""Application configuration using environment variables."""

from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

# Get the backend directory path
BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    CSMARKET_API_KEY: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./index.db"
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = str(BACKEND_DIR / ".env")
        env_file_encoding = 'utf-8'
        case_sensitive = True


settings = Settings()
