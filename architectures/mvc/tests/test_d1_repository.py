import asyncio

import pytest
from fake_d1 import FakeD1

from app.errors import TaskConflict
from app.repositories.d1_tasks import (
    TaskRecord,
    complete_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    rename_task,
)


def run(coroutine):
    return asyncio.run(coroutine)


def test_create_task_and_get_task():
    database = FakeD1()

    created = run(create_task(database, "prepare release"))
    loaded = run(get_task(database, created.id))

    assert created == TaskRecord(id=1, title="prepare release", completed=False)
    assert loaded == created


def test_list_tasks_are_ordered_and_map_completed_to_boolean():
    database = FakeD1()
    first = run(create_task(database, "first"))
    second = run(create_task(database, "second"))
    run(complete_task(database, second.id))

    tasks = run(list_tasks(database))

    assert [task.id for task in tasks] == [first.id, second.id]
    assert tasks[0].completed is False
    assert tasks[1].completed is True


def test_rename_task_trims_title():
    database = FakeD1()
    created = run(create_task(database, "draft"))

    renamed = run(rename_task(database, created.id, "  review  "))

    assert renamed == TaskRecord(id=created.id, title="review", completed=False)


def test_completed_task_cannot_be_renamed_or_mutated():
    database = FakeD1()
    created = run(create_task(database, "ship"))
    run(complete_task(database, created.id))

    with pytest.raises(TaskConflict, match="已完成的任务不能修改标题"):
        run(rename_task(database, created.id, "cancelled"))

    assert run(get_task(database, created.id)) == TaskRecord(
        id=created.id, title="ship", completed=True
    )


def test_complete_task_is_idempotent():
    database = FakeD1()
    created = run(create_task(database, "ship"))

    first = run(complete_task(database, created.id))
    second = run(complete_task(database, created.id))

    assert first == second == TaskRecord(id=created.id, title="ship", completed=True)


def test_delete_task_and_missing_ids():
    database = FakeD1()
    created = run(create_task(database, "temporary"))

    assert run(delete_task(database, created.id)) is True
    assert run(delete_task(database, created.id)) is False
    assert run(get_task(database, created.id)) is None
    assert run(rename_task(database, 987654, "missing")) is None
    assert run(complete_task(database, 987654)) is None
