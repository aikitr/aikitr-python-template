import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine, text

from app.config import get_settings
from app.controllers.tasks import build_router
from app.database import Base, build_engine
from app.http_errors import install_error_handlers
from app.models import Task  # noqa: F401 - registers the model with SQLAlchemy


def create_app(database_url: str | None = None, *, engine: Engine | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    if engine is None:
        engine = build_engine(database_url or get_settings().database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Supabase MVC 任务管理示例",
        description="FastAPI MVC + Supabase PostgreSQL（SQLAlchemy / Psycopg）。",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.metadata = Base.metadata
    install_error_handlers(app)
    app.include_router(build_router(engine))

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app
