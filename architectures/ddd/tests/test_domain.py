import pytest

from app.application.task_service import TaskService
from app.domain.exceptions import TaskNotFound
from app.domain.task import Task


class MemoryTaskRepository:
    def __init__(self):
        self.tasks: dict[int, Task] = {}
        self.next_id = 1

    def list(self) -> list[Task]:
        return list(self.tasks.values())

    def get(self, task_id: int) -> Task | None:
        return self.tasks.get(task_id)

    def save(self, task: Task) -> Task:
        if task.id == 0:
            task = Task.create(self.next_id, task.title, task.completed)
            self.next_id += 1
        self.tasks[task.id] = task
        return task

    def delete(self, task_id: int) -> None:
        self.tasks.pop(task_id, None)


def test_application_rules_with_an_in_memory_repository():
    repository = MemoryTaskRepository()
    service = TaskService(repository)

    task = service.create("draft")
    task = service.rename(task.id, "review")
    task = service.complete(task.id)
    service.complete(task.id)

    assert repository.list() == [task]
    assert task.completed is True
    with pytest.raises(ValueError):
        service.rename(task.id, "changed")
    assert service.get(task.id).title == "review"

    service.delete(task.id)
    with pytest.raises(TaskNotFound):
        service.get(task.id)
