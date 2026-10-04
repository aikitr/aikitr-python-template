import pytest
from fastapi.testclient import TestClient


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


@pytest.mark.parametrize("title", ["", "   ", None, 42, "a" * 201])
def test_reject_invalid_task_title(client: TestClient, title):
    response = client.post("/tasks", json={"title": title})

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
