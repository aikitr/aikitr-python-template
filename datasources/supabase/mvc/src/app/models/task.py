from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.task_rules import rename_title


class Task(Base):
    """MVC model: persisted state and task state changes live together."""

    __tablename__ = "tasks"
    __table_args__ = {"schema": "task_app"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def rename(self, title: str) -> None:
        self.title = rename_title(title, completed=self.completed)

    def complete(self) -> None:
        self.completed = True
