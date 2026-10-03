from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.schemas import TaskInput, TaskResponse
from app.database import make_session_dependency
from app.repositories.tasks import TaskRepository
from app.services.tasks import TaskService


def build_router(engine) -> APIRouter:
    router = APIRouter(prefix="/tasks", tags=["tasks"])
    get_session = make_session_dependency(engine)
    Database = Annotated[Session, Depends(get_session)]

    def service(session: Session) -> TaskService:
        return TaskService(TaskRepository(session))

    @router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskInput, session: Database):
        return service(session).create(payload.title)

    @router.get("", response_model=list[TaskResponse])
    def list_tasks(session: Database):
        return service(session).list()

    @router.get("/{task_id}", response_model=TaskResponse)
    def get_task(task_id: int, session: Database):
        return service(session).get(task_id)

    @router.patch("/{task_id}", response_model=TaskResponse)
    def rename_task(task_id: int, payload: TaskInput, session: Database):
        return service(session).rename(task_id, payload.title)

    @router.post("/{task_id}/complete", response_model=TaskResponse)
    def complete_task(task_id: int, session: Database):
        return service(session).complete(task_id)

    @router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_task(task_id: int, session: Database) -> Response:
        service(session).delete(task_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
