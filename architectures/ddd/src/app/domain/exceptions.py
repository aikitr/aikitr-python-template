class TaskConflict(ValueError):
    """Raised when a task action conflicts with its current state."""


class TaskNotFound(LookupError):
    """Raised when a task does not exist."""
