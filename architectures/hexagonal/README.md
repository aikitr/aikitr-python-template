# 六边形架构：任务管理示例

本项目把业务核心和外围技术隔开。核心用例只依赖仓储端口，HTTP 与 SQLite 分别通过输入、输出适配器接入，适合需要替换接口或基础设施的服务。

## 目录和调用流程

- src/app/core/：纯 Python 任务模型、业务规则和用例。
- src/app/ports/：核心需要的仓储协议。
- src/app/adapters/input/http/：FastAPI 请求和路由适配器。
- src/app/adapters/output/sqlite/：SQLAlchemy 表模型、SQLite 会话和仓储适配器。
- src/app/bootstrap.py：构建 FastAPI、数据库和适配器。
- alembic/：数据库迁移。

HTTP 输入适配器调用核心用例；核心只通过仓储端口读写任务；SQLite 输出适配器实现该端口。

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
    curl -X PATCH http://127.0.0.1:8000/tasks/1       -H 'Content-Type: application/json'       -d '{"title":"开始验收"}'

同时提供 GET /tasks/{id}、POST /tasks/{id}/complete 和 DELETE /tasks/{id}。标题会自动去除首尾空格，空标题返回 422；找不到任务返回 404；已完成任务不能修改标题，返回 409；重复完成成功。

## 添加功能和复制

新业务规则留在 core/；如果核心需要另一种能力，先定义端口，再添加实现该端口的适配器。复制 hexagonal/ 目录即可独立开发；复制后修改 pyproject.toml 中的项目名，再运行 uv lock 更新锁文件。

数据库结构调整后，更新 SQLite 输出适配器的表模型，生成迁移并检查迁移内容，再应用：

    uv run alembic revision --autogenerate -m "describe task schema change"
    uv run ruff format alembic/versions
    uv run alembic upgrade head

## 验证

    uv run pytest
    uv run ruff check .
    uv run ruff format --check .

测试覆盖核心业务、HTTP 流程、持久化、迁移升降级和事务回滚。核心和端口只依赖 Python 标准库，可单独导入和测试。
