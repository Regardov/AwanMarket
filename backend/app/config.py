from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lunora Market"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./lunora.db"
    secret_key: str = "development-secret-change-before-production"
    access_token_expire_minutes: int = 1440
    admin_email: str = "admin@lunora.shop"
    admin_password: str = "ChangeMe123!"
    cors_origins: list[str] | str = ["http://localhost:8080"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

