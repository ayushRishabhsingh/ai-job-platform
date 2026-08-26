"""Application configuration.

All settings are read from environment variables (or a local .env file).
See .env.example for the full list.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "AI Job Recommendation & Resume Analyzer API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # --- Database ---
    # Defaults to SQLite so the project runs with zero setup.
    # For PostgreSQL use:
    #   postgresql+psycopg2://user:password@localhost:5432/jobsdb
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'jobs.db'}"

    # --- Security / JWT ---
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # --- Uploads ---
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_MB: int = 5

    # --- Matching ---
    # overlap | tfidf | embedding
    DEFAULT_MATCH_STRATEGY: str = "overlap"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # --- Pagination ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is only parsed once per process."""
    return Settings()


settings = get_settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
