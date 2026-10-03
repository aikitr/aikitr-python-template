import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.http_errors import install_error_handlers
from app.infrastructure.database import Base, build_engine
from app.infrastructure.models import TaskRecord  # noqa: F401 - registers the table
from app.interfaces.http.tasks import build_router


def create_app(database_url: str | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    engine = build_engine(database_url or get_settings().database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="DDD 任务管理示例", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    app.state.metadata = Base.metadata
    install_error_handlers(app)
    app.include_router(build_router(engine))

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app
