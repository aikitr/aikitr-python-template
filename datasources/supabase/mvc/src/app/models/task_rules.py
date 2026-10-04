from app.errors import TaskConflict


def rename_title(title: str, completed: bool) -> str:
    normalized = title.strip()
    if not normalized:
        raise ValueError("任务标题不能为空")
    if completed:
        raise TaskConflict("已完成的任务不能修改标题")
    return normalized
