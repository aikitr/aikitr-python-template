# DDD 架构：任务管理示例

本项目以任务聚合维护业务规则，由应用层协调用例和仓储端口；SQLAlchemy 仅出现在基础设施中。适合业务规则较多、需要保护领域模型的服务。

## 目录和调用流程

- src/app/domain/：纯 Python 的 Task 聚合及领域异常，不依赖 Web 或数据库框架。
- src/app/application/：用例服务和 TaskRepository 协议。
- src/app/infrastructure/：SQLAlchemy 表模型、SQLite 会话和仓储适配器。
- src/app/interfaces/http/：FastAPI 输入输出和路由。
- alembic/：数据库迁移。

HTTP 接口调用应用用例，用例依赖仓储协议，基础设施提供该协议的 SQLAlchemy 实现。

## 开始开发

需要 Python 3.12 或更新版本，以及 uv。

    cp .env.example .env
    uv sync --locked
    uv run alembic upgrade head
    uv run uvicorn app.main:create_app --factory --reload

打开 http://127.0.0.1:8000/docs 调试接口。APP_DATABASE_URL 默认保存到当前项目的 data/tasks.db。

## API 示例

    curl -X POST http://127.0.0.1:8000/tasks       -H 'Content-Type: application/json'       -d '{"title":"准备发布"}'

    curl http://127.0.0.1:8000/tasks
    curl -X POST http://127.0.0.1:8000/tasks/1/complete

同时提供 GET /tasks/{id}、PATCH /tasks/{id} 和 DELETE /tasks/{id}。标题会自动去除首尾空格，空标题返回 422；找不到任务返回 404；已完成任务不能修改标题，返回 409；重复完成成功。

## 添加功能和复制

复杂规则写入 domain/ 并用纯 Python 单元测试；用例写入 application/ 并依赖仓储协议；数据库改动放入 infrastructure/，通过 Alembic 迁移。复制 ddd/ 目录即可独立开发；复制后修改 pyproject.toml 中的项目名，再运行 uv lock 更新锁文件。

数据库结构调整后，更新 infrastructure 表模型和映射，生成迁移并检查迁移内容，再应用：

    uv run alembic revision --autogenerate -m "describe task schema change"
    uv run ruff format alembic/versions
    uv run alembic upgrade head

## 验证

    uv run pytest
    uv run ruff check .
    uv run ruff format --check .

测试覆盖领域行为、HTTP 流程、持久化、迁移升降级和事务回滚。领域模型可不启动 Web 服务或数据库进行单元测试。
