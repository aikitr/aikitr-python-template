# MVC 架构：任务管理示例

本项目把 HTTP Controller、Model 和 JSON View 分开，演示如何以传统 MVC 方式组织 FastAPI 应用。SQLite/Alembic 用于本地开发；Cloudflare Worker 使用独立的异步 D1 Repository 保存线上任务。

## 目录和调用流程

- `src/app/controllers/`：FastAPI 路由和请求编排。
- `src/app/models/`：SQLAlchemy Task Model 和共享的任务状态规则。
- `src/app/repositories/`：SQLite 查询和 Worker 使用的 D1 查询。
- `src/app/views/`：输入校验和 JSON 响应格式。
- `src/app/worker_app.py`、`src/entry.py`：D1-backed FastAPI 应用和 Cloudflare ASGI 入口。
- `alembic/`：SQLite 迁移；`migrations/`：D1 SQL 迁移。

## 本地 SQLite 开发

需要 Python 3.12 或更新版本，以及 uv。默认本地后端仍然使用 SQLite：

```sh
cp .env.example .env
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload
```

打开 http://127.0.0.1:8000/docs 调试接口。`APP_DATABASE_URL` 默认将数据保存到 `data/tasks.db`。

数据库结构调整后，更新 Model 并生成 SQLite 迁移；检查迁移文件，再应用：

```sh
uv run alembic revision --autogenerate -m "describe task schema change"
uv run ruff format alembic/versions
uv run alembic upgrade head
```

## Cloudflare Worker 本地开发

Worker 使用 Python Workers、FastAPI 和绑定名为 `DB` 的 Cloudflare D1 数据库。运行这些命令需要 Node.js/npm、Python 和 uv：

```sh
uv sync --locked
uv run pywrangler d1 migrations apply aikitr-mvc-tasks --local
uv run pywrangler dev
```

本地 Worker 地址是 `http://127.0.0.1:8787`。本地 D1 数据与 SQLite 文件分开保存。

### D1 数据库迁移

新增 D1 schema 迁移后，先在本地创建并应用，再将其纳入代码评审：

```sh
uv run pywrangler d1 migrations create aikitr-mvc-tasks add_task_field
uv run pywrangler d1 migrations apply aikitr-mvc-tasks --local
```

生产部署脚本会先应用远程 D1 迁移，再发布 Worker。需要手动应用时，可运行：

```sh
uv run pywrangler d1 migrations apply aikitr-mvc-tasks --remote
```

## 已部署的 Worker

Worker 名称为 `aikitr-mvc-api`。首次部署后，Cloudflare 会提供对应的 `workers.dev` URL；将该 URL 设为 `WORKER_URL` 后，可以这样调用：

```sh
export WORKER_URL="https://<deployed-workers.dev-url>"
curl "$WORKER_URL/health"
curl -X POST "$WORKER_URL/tasks" \
  -H 'Content-Type: application/json' \
  -d '{"title":"准备发布"}'
curl "$WORKER_URL/tasks"
```

Worker 保持现有任务接口：`GET /health`、`POST /tasks`、`GET /tasks`、`GET /tasks/{id}`、`PATCH /tasks/{id}`、`POST /tasks/{id}/complete` 和 `DELETE /tasks/{id}`。D1 保存的任务会跨 Worker 请求保留。

## 添加功能与复制

新增 HTTP 行为时，在 Controller 中增加路由；输入和输出格式放在 View；任务状态规则放在 Model；数据库查询放在 Repository。复制本目录即可独立开发，复制后可以修改 `pyproject.toml` 中的项目名并运行 `uv lock` 更新依赖锁文件。

SQLite 结构变化使用 Alembic；Cloudflare Worker 的 D1 结构变化使用上面的 D1 SQL 迁移。两套迁移各自管理对应的数据库。

## GitHub 自动部署

在 Cloudflare Workers Builds 中连接 `aikitr/aikitr-python-template`，并设置：

- 生产分支：`main`
- Root directory：`/architectures/mvc`
- Included watch path：`architectures/mvc/**`
- Build command：`sh scripts/cloudflare-build.sh`
- Deploy command：`sh scripts/cloudflare-deploy.sh`
- Preview deployments：关闭

这样，推送到 `main` 且改动命中 `architectures/mvc/**` 时会应用 D1 迁移并自动部署 Worker；其他目录的改动不会触发这个 Worker 的构建。部署脚本固定使用 uv 0.12.6，并从 `uv.lock` 安装项目环境。

## API 行为和验证

标题会自动去除首尾空格；空标题返回 422；找不到任务返回 404；已完成任务不能修改标题，返回 409；重复完成成功。

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

测试使用临时 SQLite 数据库和 D1 双重验证 HTTP 行为、迁移、持久化、任务状态规则，以及写入失败时不保存数据。
