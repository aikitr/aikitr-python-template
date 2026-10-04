# Supabase PostgreSQL MVC 示例

可独立复制的 FastAPI 任务管理项目，使用 Python 3.12、uv、SQLAlchemy 2、Psycopg 3 和 Alembic。Supabase 提供 PostgreSQL 数据库；本示例通过原生数据库连接实现每次请求的事务提交与回滚，配置项是数据库连接串，无需 Supabase URL 或 API Key。

## 目录职责与调用链

```text
src/app/
├── main.py            # 应用工厂、健康检查和连接池生命周期
├── config.py          # 环境配置及 PostgreSQL URL 校验
├── database.py        # Engine、Session 和事务边界
├── controllers/       # 接收请求、调用 Model 和 Repository
├── models/            # 任务持久化模型及改名、完成规则
├── repositories/      # SQLAlchemy 查询
├── views/             # 输入校验及 JSON 输出模型
└── http_errors.py     # 404、409、数据库错误响应
alembic/               # 私有 schema 的数据库迁移
tests/                 # HTTP、配置、事务和 PostgreSQL 迁移测试
```

调用链为 `HTTP → Controller → Model / Repository → SQLAlchemy Session → Supabase PostgreSQL → JSON View`。Model 封装业务规则，Controller 协调请求，View 校验并输出 JSON。适合需要使用 Supabase 托管数据库的小型服务，以及熟悉 MVC 的团队。

## 复制与连接配置

从仓库根目录复制：

```bash
cp -R datasources/supabase/mvc ../my-supabase-service
cd ../my-supabase-service
uv sync --locked
cp .env.example .env
```

如果曾经运行过原示例，可以删除复制目录里的 `.venv`、`*.egg-info` 和缓存后再安装。修改 `pyproject.toml` 中的项目名、描述和 `src/app/main.py` 中的 API 标题；改名后运行 `uv lock` 更新锁文件。Python 包名 `app` 可以直接保留；若修改包名，同时修改内部导入、Alembic 导入及启动命令。

在 Supabase 控制台打开项目顶部的 **Connect**，复制连接串并替换密码。密码中的 `@`、`#`、`%`、`/` 等保留字符需要 URL 编码；主机、端口和用户名以控制台给出的内容为准。将协议改为 `postgresql+psycopg://`，在 `.env` 中填写：

```dotenv
APP_DATABASE_URL=postgresql+psycopg://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@SESSION_POOLER_HOST:5432/postgres?sslmode=require
```

连接方式：

| 场景 | 连接方式 | 配置 |
|---|---|---|
| 本地开发或仅支持 IPv4 的常驻 FastAPI 服务 | Session pooler，通常为 5432 端口 | `APP_DATABASE_URL` |
| 支持 IPv6 或启用 IPv4 add-on 的常驻服务 | Direct connection，5432 端口 | `APP_DATABASE_URL` |
| Alembic 迁移 | 优先 Direct connection；IPv4 环境可用 Session pooler | 可设置 `APP_MIGRATION_DATABASE_URL` |

迁移连接串未配置时使用 `APP_DATABASE_URL`。不要把 6543 端口的 Transaction pooler 用于迁移。应用连接池启用连接存活检查，最多 5 个连接，默认要求 SSL，并关闭 Psycopg 自动预编译以兼容连接池。需要验证服务器证书时，在连接串中设置 `sslmode=verify-full&sslrootcert=/绝对路径/证书.crt`。

连接串只放在服务端 `.env` 或环境变量中，`.env` 已被忽略。迁移创建 `task_app` schema，任务表及 Alembic 版本表均位于其中；自动生成迁移仅检查这个 schema，不会把 Supabase 的 `auth`、`storage` 或其他业务 schema 当成待删除对象。

任务表启用 RLS，并撤销 `PUBLIC` 的访问权限。示例使用拥有 `task_app` schema 和任务表的数据库所有者连接（控制台默认的 `postgres` 用户），通过 FastAPI 操作任务；PostgreSQL 表所有者可绕过 RLS。非所有者没有放行策略，因此即使拥有表访问授权，也无法读写任务行。无需将 `task_app` 加入 Supabase Data API 的 exposed schemas。参见 [连接指南](https://supabase.com/docs/guides/database/connecting-to-postgres) 和 [RLS 指南](https://supabase.com/docs/guides/database/postgres/row-level-security)。

## 迁移与启动

在示例项目目录中执行：

```bash
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload
```

浏览器打开 http://127.0.0.1:8000/docs 调试接口。应用启动不会自动建表，先运行迁移。`/health` 执行 `SELECT 1` 检查数据库连接，连接失败返回 503。

每次请求成功时提交事务，异常时回滚。事务提交在成功响应发送之前完成，数据库操作或提交失败统一返回 503，不把数据库错误细节返回给客户端。

## 接口与可执行示例

| 接口 | 功能 | 成功状态 |
|---|---|---|
| `POST /tasks` | 创建任务 | 201 |
| `GET /tasks` | 按 ID 升序列出任务 | 200 |
| `GET /tasks/{id}` | 查询任务 | 200 |
| `PATCH /tasks/{id}` | 修改标题 | 200 |
| `POST /tasks/{id}/complete` | 完成任务，重复完成成功 | 200 |
| `DELETE /tasks/{id}` | 删除任务 | 204 |
| `GET /health` | 检查应用和数据库 | 200 |

标题自动去除两端空白，长度为 1–200 个字符。参数错误返回 422，任务不存在返回 404，已完成任务修改标题返回 409。

保持服务运行，在项目目录的另一个终端执行：

```bash
curl -fsS http://127.0.0.1:8000/health
TASK_ID=$(curl -fsS -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' -d '{"title":"学习 Supabase MVC"}' \
  | uv run python -c 'import json, sys; print(json.load(sys.stdin)["id"])')
curl -fsS http://127.0.0.1:8000/tasks
curl -fsS "http://127.0.0.1:8000/tasks/$TASK_ID"
curl -fsS -X PATCH "http://127.0.0.1:8000/tasks/$TASK_ID" \
  -H 'Content-Type: application/json' -d '{"title":"完成任务示例"}'
curl -fsS -X POST "http://127.0.0.1:8000/tasks/$TASK_ID/complete"
curl -fsS -X POST "http://127.0.0.1:8000/tasks/$TASK_ID/complete"
curl -i -X PATCH "http://127.0.0.1:8000/tasks/$TASK_ID" \
  -H 'Content-Type: application/json' -d '{"title":"不允许修改"}'
curl -i -X DELETE "http://127.0.0.1:8000/tasks/$TASK_ID"
```

## 测试与检查

无需 Supabase 凭据即可执行：

```bash
uv run pytest
uv run ruff check
uv run ruff format --check
```

默认通过注入临时 SQLite Engine 验证 HTTP 业务、提交失败回滚、重启持久化等行为，并测试连接配置与 PostgreSQL 离线迁移。SQLite 只用于隔离测试；正常启动从 `.env` 加载 Supabase PostgreSQL 配置。未设置测试数据库时，真实 PostgreSQL 用例会明确标记为 skipped。

完整集成测试使用一个**空的、可丢弃的 PostgreSQL 测试数据库**（不要使用业务数据库）：

```bash
TEST_DATABASE_URL='postgresql+psycopg://postgres:password@127.0.0.1:5432/task_template_test?sslmode=disable' \
  uv run pytest
```

测试连接需要创建 schema、表和测试角色的权限。测试会先拒绝已存在 `task_app` schema 的数据库，每个测试创建并清理自己的 `task_app` schema；验证真实 PostgreSQL HTTP 流程、迁移升降级、自动迁移的 schema 范围、RLS 和事务。示例里的 `sslmode=disable` 仅用于本地测试数据库。

## 新增业务与迁移

1. 在 `models/` 添加 SQLAlchemy Model，并封装业务规则；表使用 `__table_args__ = {"schema": "task_app"}`。
2. 在 `repositories/` 添加查询，在 `views/` 添加输入与输出模型，在 `controllers/` 添加路由。
3. 在 `models/__init__.py` 注册模型，并在 `main.py` 注册路由。Alembic 必须导入新模型，使其进入 `Base.metadata`。
4. 生成、审阅并应用迁移：

```bash
uv run alembic revision --autogenerate -m add_business_table
uv run ruff format alembic/versions
uv run alembic upgrade head
```

自动生成迁移不管理 RLS 和授权；新增表时，像初始迁移一样加入启用 RLS 和撤销公共访问的 SQL。新增接口需测试成功流程、校验失败、业务冲突和事务回滚。

回退一个迁移使用 `uv run alembic downgrade -1`。回退至初始状态使用 `uv run alembic downgrade base`，会删除示例任务表及其中数据，保留 `task_app` schema 和 Alembic 版本表。
