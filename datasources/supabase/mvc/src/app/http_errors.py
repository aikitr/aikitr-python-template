import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.errors import TaskConflict, TaskNotFound


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TaskNotFound)
    async def not_found_handler(_request: Request, exc: TaskNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TaskConflict)
    async def conflict_handler(_request: Request, exc: TaskConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logging.getLogger(__name__).warning("数据库操作失败：%s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "数据库暂时不可用"})
