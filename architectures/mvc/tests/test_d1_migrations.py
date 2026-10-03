import sqlite3
from pathlib import Path


def test_initial_d1_migration_creates_tasks_table(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    migration = (project_root / "migrations" / "0001_create_tasks.sql").read_text(encoding="utf-8")
    database = sqlite3.connect(tmp_path / "tasks.db")

    database.executescript(migration)
    columns = database.execute("PRAGMA table_info(tasks)").fetchall()

    assert [column[1] for column in columns] == ["id", "title", "completed"]
    assert columns[0][2] == "INTEGER"
    assert columns[0][5] == 1
    assert columns[1][2] == "VARCHAR(200)"
    assert columns[1][3] == 1
    assert columns[2][2] == "INTEGER"
    assert columns[2][3] == 1
    assert columns[2][4] == "0"

    database.execute("INSERT INTO tasks (title) VALUES (?)", ("prepare release",))
    assert database.execute("SELECT title, completed FROM tasks").fetchone() == (
        "prepare release",
        0,
    )
    database.close()
