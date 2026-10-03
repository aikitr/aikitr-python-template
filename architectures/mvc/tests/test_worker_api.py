import os
import subprocess
import sys
from pathlib import Path

import pytest
from fake_d1 import FakeD1
from fastapi.testclient import TestClient

from app.controllers.d1_tasks import get_d1_database
from app.worker_app import create_worker_app


def test_worker_bootstrap_does_not_require_sqlalchemy():
    project_root = Path(__file__).resolve().parents[1]
    script = """
import builtins

original_import = builtins.__import__

def import_without_sqlalchemy(name, *args, **kwargs):
    if name == "sqlalchemy" or name.startswith("sqlalchemy."):
        raise ModuleNotFoundError("No module named 'sqlalchemy'")
    return original_import(name, *args, **kwargs)

builtins.__import__ = import_without_sqlalchemy
from app.worker_app import create_worker_app
create_worker_app()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env={**os.environ, "PYTHONPATH": str(project_root / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


@pytest.fixture
def worker_client():
    app = create_worker_app()
    database = FakeD1()
    app.dependency_overrides[get_d1_database] = lambda: database
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, database


def test_worker_health_check(worker_client):
    client, _database = worker_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_worker_create_list_and_get_task(worker_client):
    client, _database = worker_client

    created = client.post("/tasks", json={"title": "  prepare release  "})

    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "prepare release"
    assert task["completed"] is False
    assert client.get("/tasks").json() == [task]
    assert client.get(f"/tasks/{task['id']}").json() == task


def test_worker_rename_task(worker_client):
    client, _database = worker_client
    task = client.post("/tasks", json={"title": "draft"}).json()

    renamed = client.patch(f"/tasks/{task['id']}", json={"title": "  review "})

    assert renamed.status_code == 200
    assert renamed.json()["title"] == "review"


def test_worker_complete_task_is_idempotent(worker_client):
    client, _database = worker_client
    task = client.post("/tasks", json={"title": "ship"}).json()

    first = client.post(f"/tasks/{task['id']}/complete")
    second = client.post(f"/tasks/{task['id']}/complete")

    assert first.status_code == 200
    assert first.json()["completed"] is True
    assert second.status_code == 200
    assert second.json() == first.json()


def test_worker_delete_task(worker_client):
    client, _database = worker_client
    task = client.post("/tasks", json={"title": "temporary"}).json()

    deleted = client.delete(f"/tasks/{task['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def test_blank_title_returns_unprocessable_entity(worker_client):
    client, database = worker_client

    response = client.post("/tasks", json={"title": " \t\n "})

    assert response.status_code == 422
    assert client.get("/tasks").json() == []
    assert database.connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/tasks/987654", None),
        ("patch", "/tasks/987654", {"title": "missing"}),
        ("post", "/tasks/987654/complete", None),
        ("delete", "/tasks/987654", None),
    ],
)
def test_missing_task_returns_not_found(worker_client, method, path, payload):
    client, _database = worker_client
    request = getattr(client, method)

    response = request(path, json=payload) if payload else request(path)

    assert response.status_code == 404
    assert response.json() == {"detail": "任务不存在"}


def test_completed_task_cannot_be_renamed(worker_client):
    client, _database = worker_client
    task = client.post("/tasks", json={"title": "ship"}).json()
    client.post(f"/tasks/{task['id']}/complete")

    response = client.patch(f"/tasks/{task['id']}", json={"title": "cancelled"})

    assert response.status_code == 409
    assert response.json() == {"detail": "已完成的任务不能修改标题"}
    assert client.get(f"/tasks/{task['id']}").json()["title"] == "ship"


def test_worker_write_failure_returns_500_without_storing_task(worker_client):
    client, database = worker_client
    database.fail_next_write = True

    response = client.post("/tasks", json={"title": "must not persist"})

    assert response.status_code == 500
    assert client.get("/tasks").json() == []
