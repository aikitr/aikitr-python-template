from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.errors import TaskConflict


class Task(Base):
    """MVC model: persisted state and task state changes live together."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def rename(self, title: str) -> None:
        normalized = title.strip()
        if not normalized:
            raise ValueError("任务标题不能为空")
        if self.completed:
            raise TaskConflict("已完成的任务不能修改标题")
        self.title = normalized

    def complete(self) -> None:
        self.completed = True
