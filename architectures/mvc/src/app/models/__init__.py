from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.task import Task

__all__ = ["Task"]


def __getattr__(name: str) -> Any:
    if name == "Task":
        from app.models.task import Task

        return Task
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
