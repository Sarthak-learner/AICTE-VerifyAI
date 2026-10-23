"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://verifyai:changeme@localhost:5432/verifyai_db"

    # Security
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Storage
    upload_dir: str = "../storage/uploads"
    processed_dir: str = "../storage/processed"
    max_upload_size_mb: int = 50
    max_pdf_pages: int = 500

    # OCR
    tesseract_cmd: str = "tesseract"

    # CORS
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
