# MVC 架构：任务管理示例

本项目把 HTTP Controller、Model 和 JSON View 分开，Model 同时管理任务状态和持久化对象，适合以传统 MVC 方式组织小型 Web 应用。

## 目录和调用流程

- src/app/controllers/：FastAPI 路由和请求编排。
- src/app/models/：SQLAlchemy Task Model，包含重命名、完成任务等状态行为。
- src/app/views/：输入校验和 JSON 响应格式。
- src/app/repositories/：供 Controller 查询任务的数据库读取函数。
- src/app/database.py：SQLite 引擎和请求会话。
- alembic/：数据库迁移。

请求经过 Controller；Controller 调用 Model 和 Repository，再用 View 的响应模型输出 JSON。

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

新增 HTTP 行为时，在 Controller 中增加路由；输入、输出格式放在 View；状态行为放在 Model；复杂查询集中到 Repository。复制 mvc/ 目录即可独立开发。复制后可修改 pyproject.toml 中的项目名，再运行 uv lock 更新锁文件。

数据库结构调整后，更新 Model 并生成迁移；检查生成的迁移文件，再应用：

    uv run alembic revision --autogenerate -m "describe task schema change"
    uv run ruff format alembic/versions
    uv run alembic upgrade head

## 验证

    uv run pytest
    uv run ruff check .
    uv run ruff format --check .

测试使用临时 SQLite 文件验证 HTTP 行为、数据库重启后的持久化、迁移升降级和写入失败时的事务回滚。
