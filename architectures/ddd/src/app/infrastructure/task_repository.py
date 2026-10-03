from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.task import Task
from app.infrastructure.models import TaskRecord


class SqlAlchemyTaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Task]:
        records = self.session.scalars(select(TaskRecord).order_by(TaskRecord.id))
        return [self._to_domain(record) for record in records]

    def get(self, task_id: int) -> Task | None:
        record = self.session.get(TaskRecord, task_id)
        return self._to_domain(record) if record is not None else None

    def save(self, task: Task) -> Task:
        record = self.session.get(TaskRecord, task.id) if task.id else None
        if record is None:
            record = TaskRecord()
        record.title = task.title
        record.completed = task.completed
        self.session.add(record)
        self.session.flush()
        return self._to_domain(record)

    def delete(self, task_id: int) -> None:
        record = self.session.get(TaskRecord, task_id)
        if record is not None:
            self.session.delete(record)

    @staticmethod
    def _to_domain(record: TaskRecord) -> Task:
        return Task.create(
            task_id=record.id,
            title=record.title,
            completed=record.completed,
        )
