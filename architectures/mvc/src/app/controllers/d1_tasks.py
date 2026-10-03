from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status

from app.errors import TaskNotFound
from app.repositories import d1_tasks as task_repository
from app.repositories.d1_tasks import TaskRecord
from app.views.tasks import TaskInput, TaskResponse


def get_d1_database(request: Request) -> Any:
    return request.scope["env"].DB


def build_d1_router() -> APIRouter:
    router = APIRouter(prefix="/tasks", tags=["tasks"])
    Database = Annotated[Any, Depends(get_d1_database)]

    @router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
    async def create_task(payload: TaskInput, database: Database) -> TaskRecord:
        return await task_repository.create_task(database, payload.title)

    @router.get("", response_model=list[TaskResponse])
    async def list_tasks(database: Database) -> list[TaskRecord]:
        return await task_repository.list_tasks(database)

    @router.get("/{task_id}", response_model=TaskResponse)
    async def get_task(task_id: int, database: Database) -> TaskRecord:
        task = await task_repository.get_task(database, task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        return task

    @router.patch("/{task_id}", response_model=TaskResponse)
    async def rename_task(task_id: int, payload: TaskInput, database: Database) -> TaskRecord:
        task = await task_repository.rename_task(database, task_id, payload.title)
        if task is None:
            raise TaskNotFound("任务不存在")
        return task

    @router.post("/{task_id}/complete", response_model=TaskResponse)
    async def complete_task(task_id: int, database: Database) -> TaskRecord:
        task = await task_repository.complete_task(database, task_id)
        if task is None:
            raise TaskNotFound("任务不存在")
        return task

    @router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_task(task_id: int, database: Database) -> Response:
        deleted = await task_repository.delete_task(database, task_id)
        if not deleted:
            raise TaskNotFound("任务不存在")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
