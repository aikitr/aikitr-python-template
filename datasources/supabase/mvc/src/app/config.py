from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def normalize_database_url(value: str) -> str:
    try:
        url = make_url(value)
    except (ArgumentError, ValueError):
        raise ValueError("请使用有效的 Supabase PostgreSQL 连接串") from None
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("请使用 Supabase PostgreSQL 连接串")
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: str
    migration_database_url: str | None = None

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @field_validator("migration_database_url")
    @classmethod
    def validate_migration_database_url(cls, value: str | None) -> str | None:
        return normalize_database_url(value) if value else None

    @property
    def alembic_database_url(self) -> str:
        return self.migration_database_url or self.database_url


def get_settings() -> Settings:
    return Settings()
