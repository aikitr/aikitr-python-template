from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def test_commit_failure_returns_error_and_rolls_back(app):
    def fail_commit(session):
        if session.bind is app.state.engine:
            raise OperationalError("COMMIT", {}, RuntimeError("simulated commit failure"))

    with TestClient(app, raise_server_exceptions=False) as client:
        event.listen(Session, "before_commit", fail_commit)
        try:
            failed = client.post("/tasks", json={"title": "must roll back"})
        finally:
            event.remove(Session, "before_commit", fail_commit)
        assert failed.status_code == 503
        assert client.get("/tasks").json() == []


def test_task_survives_application_restart(app):
    from app.main import create_app

    with TestClient(app) as first:
        task = first.post("/tasks", json={"title": "persistent"}).json()
    # The disposed Engine reconnects to the same database in a new application.
    restarted = create_app(engine=app.state.engine)
    with TestClient(restarted) as second:
        assert second.get(f"/tasks/{task['id']}").json() == task


def test_health_reports_database_failure(app):
    def fail_select(_connection, _cursor, statement, _parameters, _context, _many):
        if statement == "SELECT 1":
            raise OperationalError(statement, {}, RuntimeError("unavailable"))

    with TestClient(app, raise_server_exceptions=False) as client:
        event.listen(app.state.engine, "before_cursor_execute", fail_select)
        try:
            assert client.get("/health").status_code == 503
        finally:
            event.remove(app.state.engine, "before_cursor_execute", fail_select)
