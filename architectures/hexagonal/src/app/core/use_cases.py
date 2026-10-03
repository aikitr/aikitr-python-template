from app.core.errors import TaskNotFound
from app.core.task import Task
from app.ports.task_repository import TaskRepository


class TaskUseCases:
    """Core use cases talk only to the repository port."""

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def create(self, title: str) -> Task:
        return self.repository.save(Task.create(task_id=0, title=title))

    def list(self) -> list[Task]:
        return self.repository.list()

    def get(self, task_id: int) -> Task:
        task = self.repository.get(task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        return task

    def rename(self, task_id: int, title: str) -> Task:
        task = self.get(task_id)
        task.rename(title)
        return self.repository.save(task)

    def complete(self, task_id: int) -> Task:
        task = self.get(task_id)
        task.complete()
        return self.repository.save(task)

    def delete(self, task_id: int) -> None:
        self.get(task_id)
        self.repository.delete(task_id)
