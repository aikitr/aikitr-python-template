from fastapi import FastAPI

from app.controllers.d1_tasks import build_d1_router
from app.http_errors import install_error_handlers


def create_worker_app() -> FastAPI:
    app = FastAPI(
        title="MVC 任务管理示例",
        description="演示 Controller、Model 和 JSON View 的职责。",
        version="0.1.0",
    )
    install_error_handlers(app)
    app.include_router(build_d1_router())

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app
