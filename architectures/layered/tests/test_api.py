from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def make_app(database_url: str):
    try:
        from app.main import create_app
    except (ImportError, ModuleNotFoundError):
        from fastapi import FastAPI

        return FastAPI()
    return create_app(database_url=database_url)


@pytest.fixture
def client(tmp_path):
    app = make_app(f"sqlite:///{tmp_path / 'tasks.db'}")
    app.state.metadata.create_all(app.state.engine)
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_list_and_get_task(client: TestClient):
    created = client.post("/tasks", json={"title": "  prepare release  "})

    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "prepare release"
    assert task["completed"] is False

    assert client.get("/tasks").json() == [task]
    assert client.get(f"/tasks/{task['id']}").json() == task


def test_reject_blank_task_title(client: TestClient):
    response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 422


def test_update_task_title(client: TestClient):
    task = client.post("/tasks", json={"title": "draft"}).json()

    response = client.patch(f"/tasks/{task['id']}", json={"title": "review"})

    assert response.status_code == 200
    assert response.json()["title"] == "review"


def test_complete_task_is_idempotent(client: TestClient):
    task = client.post("/tasks", json={"title": "ship"}).json()

    first = client.post(f"/tasks/{task['id']}/complete")
    second = client.post(f"/tasks/{task['id']}/complete")

    assert first.status_code == 200
    assert first.json()["completed"] is True
    assert second.status_code == 200
    assert second.json() == first.json()


def test_completed_task_cannot_be_renamed(client: TestClient):
    task = client.post("/tasks", json={"title": "ship"}).json()
    client.post(f"/tasks/{task['id']}/complete")

    response = client.patch(f"/tasks/{task['id']}", json={"title": "cancelled"})

    assert response.status_code == 409
    assert client.get(f"/tasks/{task['id']}").json()["title"] == "ship"


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/tasks/987654", None),
        ("patch", "/tasks/987654", {"title": "missing"}),
        ("post", "/tasks/987654/complete", None),
        ("delete", "/tasks/987654", None),
    ],
)
def test_missing_task_returns_not_found(client: TestClient, method, path, payload):
    request = getattr(client, method)
    response = request(path, json=payload) if payload else request(path)

    assert response.status_code == 404


def test_delete_task(client: TestClient):
    task = client.post("/tasks", json={"title": "temporary"}).json()

    deleted = client.delete(f"/tasks/{task['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_task_survives_application_restart(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'persistent.db'}"
    first_app = make_app(database_url)
    first_app.state.metadata.create_all(first_app.state.engine)
    with TestClient(first_app) as first_client:
        created = first_client.post("/tasks", json={"title": "persistent"})
        task_id = created.json()["id"]

    second_app = make_app(database_url)
    with TestClient(second_app) as second_client:
        restored = second_client.get(f"/tasks/{task_id}")

    assert restored.status_code == 200
    assert restored.json()["title"] == "persistent"


def test_alembic_migration_can_upgrade_and_downgrade(tmp_path, monkeypatch):
    from alembic.config import Config
    from sqlalchemy import inspect

    from alembic import command

    project_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("APP_DATABASE_URL", database_url)
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))

    command.upgrade(config, "head")
    engine = make_app(database_url).state.engine
    assert "tasks" in inspect(engine).get_table_names()
    engine.dispose()

    command.downgrade(config, "base")
    engine = make_app(database_url).state.engine
    assert "tasks" not in inspect(engine).get_table_names()
    engine.dispose()


def test_failed_write_rolls_back_request_transaction(tmp_path):
    from sqlalchemy import event

    app = make_app(f"sqlite:///{tmp_path / 'rollback.db'}")
    app.state.metadata.create_all(app.state.engine)

    def fail_task_insert(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("INSERT INTO TASKS"):
            raise RuntimeError("simulated database write failure")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        event.listen(app.state.engine, "before_cursor_execute", fail_task_insert)
        failed = test_client.post("/tasks", json={"title": "must roll back"})
        event.remove(app.state.engine, "before_cursor_execute", fail_task_insert)

        assert failed.status_code == 500
        assert test_client.get("/tasks").json() == []


def test_alembic_can_generate_a_follow_up_migration(tmp_path, monkeypatch):
    import shutil
    import subprocess
    from pathlib import Path

    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    from alembic import command

    project_root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite:///{tmp_path / 'autogenerate.db'}"
    monkeypatch.setenv("APP_DATABASE_URL", database_url)
    copied_migrations = tmp_path / "migration_scripts"
    shutil.copytree(project_root / "alembic", copied_migrations)

    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(copied_migrations))

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE stale_table (id INTEGER PRIMARY KEY)"))
    engine.dispose()

    command.revision(config, "verify_template", autogenerate=True)

    generated = list((copied_migrations / "versions").glob("*_verify_template.py"))
    assert generated
    assert "drop_table" in generated[0].read_text(encoding="utf-8")
    result = subprocess.run(
        ["ruff", "format", str(generated[0])],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert "stale_table" not in inspect(engine).get_table_names()
    engine.dispose()

    result = subprocess.run(
        ["ruff", "check", str(generated[0])],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(
        ["ruff", "format", "--check", str(generated[0])],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
