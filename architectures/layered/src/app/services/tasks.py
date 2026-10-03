from app.errors import TaskConflict, TaskNotFound
from app.models.task import Task
from app.repositories.tasks import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def create(self, title: str) -> Task:
        return self.repository.add(Task(title=self._clean_title(title), completed=False))

    def list(self) -> list[Task]:
        return self.repository.list()

    def get(self, task_id: int) -> Task:
        task = self.repository.get(task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        return task

    def rename(self, task_id: int, title: str) -> Task:
        task = self.get(task_id)
        if task.completed:
            raise TaskConflict("已完成的任务不能修改标题")
        task.title = self._clean_title(title)
        return task

    def complete(self, task_id: int) -> Task:
        task = self.get(task_id)
        task.completed = True
        return task

    def delete(self, task_id: int) -> None:
        self.repository.delete(self.get(task_id))

    @staticmethod
    def _clean_title(title: str) -> str:
        normalized = title.strip()
        if not normalized:
            raise ValueError("任务标题不能为空")
        return normalized
