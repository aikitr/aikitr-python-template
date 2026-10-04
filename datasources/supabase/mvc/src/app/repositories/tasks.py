from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task


def list_tasks(session: Session) -> list[Task]:
    return list(session.scalars(select(Task).order_by(Task.id)))


def get_task(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)
