from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.models.task_rules import rename_title


@dataclass(frozen=True, slots=True)
class TaskRecord:
    id: int
    title: str
    completed: bool


def _to_python(value: Any) -> Any:
    convert = getattr(value, "to_py", None)
    return convert() if callable(convert) else value


def _field(value: Any, name: str) -> Any:
    value = _to_python(value)
    if isinstance(value, Mapping):
        return value[name]
    return getattr(value, name)


def _record(row: Any) -> TaskRecord:
    row = _to_python(row)
    if not isinstance(row, Mapping):
        row = {name: _field(row, name) for name in ("id", "title", "completed")}
    return TaskRecord(
        id=int(row["id"]),
        title=str(row["title"]),
        completed=bool(row["completed"]),
    )


async def create_task(db: Any, title: str) -> TaskRecord:
    result = await (
        db.prepare("INSERT INTO tasks (title, completed) VALUES (?, 0)").bind(title).run()
    )
    task_id = int(_field(_field(result, "meta"), "last_row_id"))
    task = await get_task(db, task_id)
    if task is None:
        raise RuntimeError("D1 did not return the task created by the insert")
    return task


async def list_tasks(db: Any) -> list[TaskRecord]:
    result = await db.prepare("SELECT id, title, completed FROM tasks ORDER BY id").all()
    rows = _to_python(_field(result, "results"))
    return [_record(row) for row in rows]


async def get_task(db: Any, task_id: int) -> TaskRecord | None:
    row = await (
        db.prepare("SELECT id, title, completed FROM tasks WHERE id = ? LIMIT 1")
        .bind(task_id)
        .first()
    )
    return _record(row) if row is not None else None


async def rename_task(db: Any, task_id: int, title: str) -> TaskRecord | None:
    current = await get_task(db, task_id)
    if current is None:
        return None

    normalized_title = rename_title(title, completed=current.completed)
    await (
        db.prepare("UPDATE tasks SET title = ? WHERE id = ? AND completed = 0")
        .bind(normalized_title, task_id)
        .run()
    )

    updated = await get_task(db, task_id)
    if updated is None:
        return None
    if updated.completed:
        rename_title(title, completed=True)
    return updated


async def complete_task(db: Any, task_id: int) -> TaskRecord | None:
    current = await get_task(db, task_id)
    if current is None:
        return None

    await db.prepare("UPDATE tasks SET completed = 1 WHERE id = ?").bind(task_id).run()
    return await get_task(db, task_id)


async def delete_task(db: Any, task_id: int) -> bool:
    result = await db.prepare("DELETE FROM tasks WHERE id = ?").bind(task_id).run()
    return int(_field(_field(result, "meta"), "changes")) > 0
