import pytest

from app.core.errors import TaskNotFound
from app.core.task import Task
from app.core.use_cases import TaskUseCases


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


def test_core_use_cases_with_an_in_memory_repository():
    repository = MemoryTaskRepository()
    use_cases = TaskUseCases(repository)

    task = use_cases.create("draft")
    task = use_cases.rename(task.id, "review")
    task = use_cases.complete(task.id)
    use_cases.complete(task.id)

    assert repository.list() == [task]
    assert task.completed is True
    with pytest.raises(ValueError):
        use_cases.rename(task.id, "changed")
    assert use_cases.get(task.id).title == "review"

    use_cases.delete(task.id)
    with pytest.raises(TaskNotFound):
        use_cases.get(task.id)
