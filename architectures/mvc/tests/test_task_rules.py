import pytest

from app.errors import TaskConflict
from app.models.task_rules import rename_title


def test_rename_title_trims_whitespace():
    assert rename_title("  prepare release  ", completed=False) == "prepare release"


def test_rename_title_rejects_blank_value():
    with pytest.raises(ValueError, match="任务标题不能为空"):
        rename_title(" \t\n ", completed=True)


def test_rename_title_rejects_completed_task():
    with pytest.raises(TaskConflict, match="已完成的任务不能修改标题"):
        rename_title("cancelled", completed=True)
