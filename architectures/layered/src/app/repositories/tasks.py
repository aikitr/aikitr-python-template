from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Task]:
        return list(self.session.scalars(select(Task).order_by(Task.id)))

    def get(self, task_id: int) -> Task | None:
        return self.session.get(Task, task_id)

    def add(self, task: Task) -> Task:
        self.session.add(task)
        self.session.flush()
        return task

    def delete(self, task: Task) -> None:
        self.session.delete(task)
