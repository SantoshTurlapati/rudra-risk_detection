import os
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseSettings):
    PROJECT_NAME: str = "RudraShield AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Required: provide a unique, randomly generated secret of at least 32 characters.
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database URL: defaults to SQLite for instant plug-and-play, supports PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./rudrashield.db")

    # CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = ["https://rudrashield-frontend.onrender.com","http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000","http://localhost:8000"]

    # Upload storage directory
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # Official brand images fail closed unless an operator selects a storage adapter.
    BRAND_IMAGE_STORAGE_BACKEND: str = "disabled"
    BRAND_IMAGE_STORAGE_DIR: str | None = None
    BRAND_IMAGE_REVIEW_THRESHOLD: float = 75.0

    # Retained for configuration compatibility; application startup never seeds demo data.
    DEMO_MODE: bool = _env_bool("DEMO_MODE", False)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        secret = value.strip()
        if len(secret) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        if any(marker in secret.casefold() for marker in ("replace", "placeholder", "change-me", "your-secret")):
            raise ValueError("SECRET_KEY must not be a placeholder value")
        return secret

    @field_validator("BRAND_IMAGE_REVIEW_THRESHOLD")
    @classmethod
    def validate_brand_image_review_threshold(cls, value: float) -> float:
        if not 0 <= value <= 100:
            raise ValueError("BRAND_IMAGE_REVIEW_THRESHOLD must be between 0 and 100")
        return value

    class Config:
        case_sensitive = True
        extra = "allow"


settings = Settings()
