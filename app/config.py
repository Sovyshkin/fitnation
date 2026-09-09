from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import EmailStr, Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    api_key: SecretStr = Field(min_length=16)

    smtp_host: str = Field(default="smtp.yandex.ru", min_length=1, max_length=253)
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_user: EmailStr
    smtp_password: SecretStr = Field(min_length=1)
    smtp_from: EmailStr
    smtp_from_name: str = Field(default="FITNATION", min_length=1, max_length=100)
    smtp_reply_to: EmailStr
    smtp_timeout: float = Field(default=20, gt=0, le=120)

    support_url: HttpUrl = HttpUrl("https://fitnation.ru")
    logo_url: HttpUrl = HttpUrl("https://fitnation.ru/logo.png")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("smtp_from_name", "smtp_host")
    @classmethod
    def reject_header_controls(cls, value: str) -> str:
        value = value.strip()
        if "\r" in value or "\n" in value:
            raise ValueError("must not contain line breaks")
        return value

    @field_validator("support_url", "logo_url")
    @classmethod
    def require_https(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("must use HTTPS")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
