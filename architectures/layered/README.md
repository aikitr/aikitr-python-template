# 分层架构：任务管理示例

本项目将接口、业务、数据访问和数据模型分层，适合希望快速定位职责、逐步拆分较大应用的团队。

## 目录和调用流程

- src/app/api/：HTTP 路由与输入、输出格式。
- src/app/services/：任务业务规则和用例编排。
- src/app/repositories/：SQLAlchemy 数据访问。
- src/app/models/：持久化模型。
- src/app/database.py：SQLite 引擎和请求会话。
- alembic/：数据库迁移。

请求由 API 路由传给 Service，Service 使用 Repository 操作 Model，响应再由 API schema 序列化。

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

新增用例先加在 Service，再通过 Repository 访问数据，并在 API 层暴露需要的接口。复制 layered/ 目录即可独立开发；复制后修改 pyproject.toml 中的项目名，再运行 uv lock 更新锁文件。

数据库结构调整后，更新持久化 Model 并生成迁移；检查生成的迁移文件，再应用：

    uv run alembic revision --autogenerate -m "describe task schema change"
    uv run ruff format alembic/versions
    uv run alembic upgrade head

## 验证

    uv run pytest
    uv run ruff check .
    uv run ruff format --check .

测试使用临时 SQLite 文件验证 HTTP 行为、数据库重启后的持久化、迁移升降级和写入失败时的事务回滚。
