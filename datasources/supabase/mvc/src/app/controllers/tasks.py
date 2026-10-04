from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import make_session_dependency
from app.errors import TaskNotFound
from app.models.task import Task
from app.repositories import tasks as task_repository
from app.views.tasks import TaskInput, TaskResponse


def build_router(engine) -> APIRouter:
    router = APIRouter(prefix="/tasks", tags=["tasks"])
    get_session = make_session_dependency(engine)
    Database = Annotated[Session, Depends(get_session, scope="function")]

    @router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskInput, session: Database) -> Task:
        task = Task(title=payload.title)
        session.add(task)
        session.flush()
        return task

    @router.get("", response_model=list[TaskResponse])
    def list_tasks(session: Database) -> list[Task]:
        return task_repository.list_tasks(session)

    @router.get("/{task_id}", response_model=TaskResponse)
    def get_task(task_id: int, session: Database) -> Task:
        task = task_repository.get_task(session, task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        return task

    @router.patch("/{task_id}", response_model=TaskResponse)
    def rename_task(task_id: int, payload: TaskInput, session: Database) -> Task:
        task = task_repository.get_task(session, task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        task.rename(payload.title)
        return task

    @router.post("/{task_id}/complete", response_model=TaskResponse)
    def complete_task(task_id: int, session: Database) -> Task:
        task = task_repository.get_task(session, task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        task.complete()
        return task

    @router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_task(task_id: int, session: Database) -> Response:
        task = task_repository.get_task(session, task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        session.delete(task)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
