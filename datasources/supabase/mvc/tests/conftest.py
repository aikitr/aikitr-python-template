import os
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from alembic import command

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def postgres_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("设置 TEST_DATABASE_URL 后运行 PostgreSQL 集成测试")
    from app.database import build_engine

    engine = build_engine(url)
    try:
        if "task_app" in inspect(engine).get_schema_names():
            pytest.fail("TEST_DATABASE_URL 必须指向不含 task_app schema 的独立测试数据库")
    finally:
        engine.dispose()
    return url


@pytest.fixture
def migrated_postgres(postgres_url, monkeypatch):
    from app.database import build_engine

    monkeypatch.setenv("APP_DATABASE_URL", postgres_url)
    monkeypatch.setenv("APP_MIGRATION_DATABASE_URL", postgres_url)
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    try:
        yield postgres_url, config
    finally:
        engine = build_engine(postgres_url)
        try:
            with engine.begin() as connection:
                connection.execute(text("DROP SCHEMA IF EXISTS task_app CASCADE"))
        finally:
            engine.dispose()


@pytest.fixture(params=["sqlite", "postgres"])
def app(request, tmp_path):
    from app.main import create_app

    if request.param == "postgres":
        url, _config = request.getfixturevalue("migrated_postgres")
        return create_app(database_url=url)
    engine = create_engine(
        f"sqlite:///{tmp_path / 'tasks.db'}",
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": {"task_app": None}},
    )
    application = create_app(engine=engine)
    application.state.metadata.create_all(engine)
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
