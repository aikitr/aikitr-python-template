from io import StringIO
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from alembic import command


def test_offline_migration_emits_postgres_schema_and_rls(monkeypatch):
    from conftest import PROJECT_ROOT

    monkeypatch.setenv("APP_DATABASE_URL", "postgresql://user:pass@host/postgres")
    monkeypatch.delenv("APP_MIGRATION_DATABASE_URL", raising=False)
    output = StringIO()
    config = Config(str(PROJECT_ROOT / "alembic.ini"), output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE task_app.tasks" in sql
    assert "SERIAL" in sql
    assert "CREATE TABLE task_app.alembic_version" in sql
    assert "ALTER TABLE task_app.tasks ENABLE ROW LEVEL SECURITY" in sql


def test_migration_upgrade_downgrade_and_schema_isolation(migrated_postgres):
    from app.database import build_engine

    url, config = migrated_postgres
    engine = build_engine(url)
    unrelated = f"unrelated_{uuid4().hex}"
    try:
        with engine.begin() as connection:
            connection.execute(text(f"CREATE TABLE public.{unrelated} (id INTEGER PRIMARY KEY)"))
        assert "tasks" in inspect(engine).get_table_names(schema="task_app")
        command.check(config)
        command.downgrade(config, "base")
        assert "tasks" not in inspect(engine).get_table_names(schema="task_app")
        assert unrelated in inspect(engine).get_table_names(schema="public")
        command.upgrade(config, "head")
        assert "tasks" in inspect(engine).get_table_names(schema="task_app")
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS public.{unrelated}"))
        engine.dispose()


def test_rls_denies_access_to_non_owner_even_with_table_grants(migrated_postgres):
    from app.database import build_engine

    url, _config = migrated_postgres
    engine = build_engine(url)
    role = f"template_reader_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(text(f"CREATE ROLE {role}"))
        connection.execute(text(f"GRANT USAGE ON SCHEMA task_app TO {role}"))
        connection.execute(text(f"GRANT SELECT, INSERT ON task_app.tasks TO {role}"))
        connection.execute(text(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA task_app TO {role}"))
        connection.execute(text("INSERT INTO task_app.tasks (title) VALUES ('private')"))
    try:
        with engine.begin() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM task_app.tasks")) == 1
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            assert connection.scalar(text("SELECT COUNT(*) FROM task_app.tasks")) == 0
        with pytest.raises(DBAPIError) as error, engine.begin() as connection:
            connection.execute(text(f"SET LOCAL ROLE {role}"))
            connection.execute(text("INSERT INTO task_app.tasks (title) VALUES ('forbidden')"))
        assert error.value.orig.sqlstate == "42501"
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP OWNED BY {role}"))
            connection.execute(text(f"DROP ROLE {role}"))
        engine.dispose()
