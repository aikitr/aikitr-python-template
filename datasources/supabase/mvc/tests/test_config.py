import pytest
from pydantic import ValidationError


def test_missing_database_url_fails_clearly(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("APP_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_postgres_urls_select_the_psycopg_driver(scheme):
    from app.config import Settings

    settings = Settings(database_url=f"{scheme}://user:pass@localhost/db", _env_file=None)
    assert settings.database_url == "postgresql+psycopg://user:pass@localhost/db"
    assert settings.alembic_database_url == settings.database_url


def test_migrations_can_use_a_separate_direct_connection():
    from app.config import Settings

    settings = Settings(
        database_url="postgresql://postgres.ref:pass@pooler.test/postgres",
        migration_database_url="postgresql://postgres:pass@direct.test/postgres",
        _env_file=None,
    )
    assert settings.alembic_database_url == (
        "postgresql+psycopg://postgres:pass@direct.test/postgres"
    )


def test_reject_other_database_backends_without_leaking_password():
    from app.config import Settings

    with pytest.raises(ValidationError) as error:
        Settings(database_url="mysql://user:sensitive-password@host/db", _env_file=None)
    assert "sensitive-password" not in str(error.value)


@pytest.mark.parametrize("url", ["", "not-a-url"])
def test_reject_empty_or_malformed_database_url(url):
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(database_url=url, _env_file=None)
