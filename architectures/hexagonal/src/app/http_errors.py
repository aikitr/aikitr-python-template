from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import TaskConflict, TaskNotFound


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TaskNotFound)
    async def not_found_handler(_request: Request, exc: TaskNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TaskConflict)
    async def conflict_handler(_request: Request, exc: TaskConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
