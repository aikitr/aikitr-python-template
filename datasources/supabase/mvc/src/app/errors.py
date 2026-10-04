class TaskNotFound(LookupError):
    """Raised when a task does not exist."""


class TaskConflict(Exception):
    """Raised when a task action conflicts with its current state."""
