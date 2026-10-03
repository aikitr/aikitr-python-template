from dataclasses import dataclass

from app.domain.exceptions import TaskConflict


@dataclass(slots=True)
class Task:
    id: int
    title: str
    completed: bool = False

    @classmethod
    def create(cls, task_id: int, title: str, completed: bool = False) -> "Task":
        return cls(task_id, cls._clean_title(title), completed)

    def rename(self, title: str) -> None:
        if self.completed:
            raise TaskConflict("已完成的任务不能修改标题")
        self.title = self._clean_title(title)

    def complete(self) -> None:
        self.completed = True

    @staticmethod
    def _clean_title(title: str) -> str:
        normalized = title.strip()
        if not normalized:
            raise ValueError("任务标题不能为空")
        return normalized
