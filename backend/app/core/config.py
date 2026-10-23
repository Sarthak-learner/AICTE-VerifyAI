"""Application configuration loaded from environment variables."""
import json
from functools import lru_cache
from typing import List, Union

from pydantic import field_validator
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
    allowed_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://aicte-verify-ai-beta.vercel.app",
    ]

    @field_validator("allowed_origins", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).rstrip("/") for item in parsed]
            except Exception:
                pass
            return [item.strip().rstrip("/") for item in v.split(",") if item.strip()]
        return [str(item).rstrip("/") for item in v]

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
