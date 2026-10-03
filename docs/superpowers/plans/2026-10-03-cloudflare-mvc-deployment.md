# Cloudflare MVC Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy only `architectures/mvc` as a Cloudflare Python Worker backed by D1, with GitHub pushes to `main` automatically deploying changes under that module.

**Architecture:** Keep the current SQLAlchemy/SQLite FastAPI app for local use. Add a separate FastAPI Worker app whose async task routes use a D1 repository, then expose it through Cloudflare's ASGI adapter. Use versioned D1 SQL migrations and Workers Builds with the MVC directory as the root and an MVC-only watch path.

**Tech Stack:** Python 3.12+, FastAPI, Pywrangler, Cloudflare Workers ASGI runtime, Cloudflare D1, Wrangler, uv, pytest, Ruff.

Run commands in Tasks 1–5 from `architectures/mvc/` unless the step says otherwise.

**Spec:** `docs/superpowers/specs/2026-10-03-cloudflare-mvc-deployment-design.md`

## Global Constraints

- Deploy only `architectures/mvc` from `aikitr/aikitr-python-template` as a Cloudflare Python Worker.
- A push to `main` should publish a new version only when files under `architectures/mvc/` change.
- Keep the task API's current HTTP behavior and persist data across Worker instances.
- Use the Worker name `aikitr-mvc-api` and D1 database name `aikitr-mvc-tasks`.
- Keep the existing SQLite URL and Alembic workflow for local development.
- Do not deploy other architecture modules, add a custom domain or frontend, change the public task API, or add a separate GitHub Actions workflow.

## Review Focus

- Whitespace-only titles are trimmed before validation and return HTTP 422 without creating a row; cover in `tests/test_worker_api.py::test_blank_title_returns_unprocessable_entity`.
- A completed task cannot be renamed and remains unchanged after HTTP 409; cover in `tests/test_worker_api.py::test_completed_task_cannot_be_renamed`.
- Completing a task more than once remains idempotent; cover in `tests/test_worker_api.py::test_complete_task_is_idempotent`.
- Missing task IDs return HTTP 404 for GET, PATCH, complete, and DELETE; cover in `tests/test_worker_api.py::test_missing_task_returns_not_found`.
- D1 stores `completed` as an integer while the API returns a JSON boolean, and list results stay ordered by ID; cover in `tests/test_d1_repository.py::test_rows_map_to_api_task_types_and_order`.

---

## File Structure

- Create `architectures/mvc/src/app/models/task_rules.py` for pure task-title and rename rules shared by the SQLAlchemy model and D1 path.
- Modify `architectures/mvc/src/app/models/task.py` to delegate rename validation to the shared rule.
- Create `architectures/mvc/src/app/repositories/d1_tasks.py` for D1 row mapping and async task queries.
- Create `architectures/mvc/src/app/controllers/d1_tasks.py` for the Worker task routes and request-scoped D1 binding dependency.
- Create `architectures/mvc/src/app/worker_app.py` for the FastAPI app that uses the D1 router and existing HTTP error handlers without creating a SQLite engine.
- Create `architectures/mvc/src/entry.py` as the Cloudflare ASGI entry point.
- Create `architectures/mvc/scripts/ensure-uv.sh`, `architectures/mvc/scripts/cloudflare-build.sh`, and `architectures/mvc/scripts/cloudflare-deploy.sh` so Workers Builds installs a pinned uv when needed, syncs the lockfile, applies remote D1 migrations, and deploys.
- Create `architectures/mvc/tests/fake_d1.py`, `architectures/mvc/tests/test_task_rules.py`, `architectures/mvc/tests/test_d1_repository.py`, and `architectures/mvc/tests/test_worker_api.py` for deterministic Python-side tests.
- Create `architectures/mvc/tests/test_d1_migrations.py` for the D1 SQL schema.
- Create `architectures/mvc/migrations/0001_create_tasks.sql` for the D1 schema.
- Create `architectures/mvc/wrangler.jsonc` for the Worker name, Python compatibility flag, D1 binding, and migration directory.
- Modify `architectures/mvc/pyproject.toml`, `architectures/mvc/uv.lock`, and `architectures/mvc/.gitignore` to add Pywrangler tooling, keep only Worker-compatible runtime packages in project dependencies, retain local-only dependencies in the default development group, exclude generated bundles from Ruff, and ignore generated bundles/local D1 state and `.cloudflare-tools/`.
- Modify `architectures/mvc/README.md` with Worker development, D1 migration, and deployment instructions.

### Task 1: Share task rename rules

**Files:**
- Create: `architectures/mvc/src/app/models/task_rules.py`
- Modify: `architectures/mvc/src/app/models/task.py`
- Test: `architectures/mvc/tests/test_task_rules.py`
- Test: `architectures/mvc/tests/test_api.py`

**Interfaces:**
- Produces: `rename_title(title: str, completed: bool) -> str`; trims whitespace, raises `ValueError("任务标题不能为空")` for an empty normalized title first, then raises `TaskConflict("已完成的任务不能修改标题")` when `completed` is true.
- The SQLAlchemy `Task.rename(title: str) -> None` method delegates to `rename_title` and assigns its returned title.

- [ ] **Step 1: Write failing tests** named `test_rename_title_trims_whitespace`, `test_rename_title_rejects_blank_value`, and `test_rename_title_rejects_completed_task` in `tests/test_task_rules.py`.
- [ ] **Step 2: Run the tests to verify they fail:** `uv run pytest tests/test_task_rules.py -v`. Expected: import or missing-function failures.
- [ ] **Step 3: Implement `rename_title` in `src/app/models/task_rules.py` and make `Task.rename` delegate to it.** Keep the current Chinese error text and exception types.
- [ ] **Step 4: Run rule and existing API tests:** `uv run pytest tests/test_task_rules.py tests/test_api.py -v`. Expected: PASS, including the existing completed-task HTTP 409 behavior.
- [ ] **Step 5: Commit** as `refactor: share task rename rules`.

### Task 2: Add the D1 task repository

**Files:**
- Create: `architectures/mvc/src/app/repositories/d1_tasks.py`
- Create: `architectures/mvc/tests/fake_d1.py`
- Test: `architectures/mvc/tests/test_d1_repository.py`

**Interfaces:**
- Produces: immutable `TaskRecord(id: int, title: str, completed: bool)`.
- Produces async functions `create_task(db, title: str) -> TaskRecord`, `list_tasks(db) -> list[TaskRecord]`, `get_task(db, task_id: int) -> TaskRecord | None`, `rename_task(db, task_id: int, title: str) -> TaskRecord | None`, `complete_task(db, task_id: int) -> TaskRecord | None`, and `delete_task(db, task_id: int) -> bool`.
- `rename_task` returns `None` only when the ID does not exist and raises `TaskConflict` for completed tasks. `complete_task` returns `None` only when the ID does not exist and is idempotent. `delete_task` returns `False` when the ID does not exist.

- [ ] **Step 1: Write failing repository tests** for create/get, ordered list, integer-to-boolean row mapping, title rename, completed-task conflict, repeat completion, and delete/missing-ID results.
- [ ] **Step 2: Run the tests to verify they fail:** `uv run pytest tests/test_d1_repository.py -v`. Expected: missing repository module or functions.
- [ ] **Step 3: Implement the async repository** using parameterized `db.prepare(...).bind(...).first()/all()/run()` calls and map D1 rows to `TaskRecord`. For rename, fetch the current row, call `rename_title`, then use a conditional update so a completed task cannot be changed.
- [ ] **Step 4: Run repository tests:** `uv run pytest tests/test_d1_repository.py -v`. Expected: PASS, including no mutation after a rejected rename.
- [ ] **Step 5: Commit** as `feat: add D1 task repository`.

### Task 3: Add the D1-backed FastAPI Worker app

**Files:**
- Create: `architectures/mvc/src/app/controllers/d1_tasks.py`
- Create: `architectures/mvc/src/app/worker_app.py`
- Create: `architectures/mvc/src/entry.py`
- Test: `architectures/mvc/tests/test_worker_api.py`
- Reuse: `architectures/mvc/src/app/views/tasks.py`, `architectures/mvc/src/app/errors.py`, and `architectures/mvc/src/app/http_errors.py`

**Interfaces:**
- Produces: `get_d1_database(request: Request) -> Any` reads `request.scope["env"].DB`, which the Cloudflare ASGI adapter supplies per request.
- Produces: `build_d1_router() -> APIRouter` exposes the same `/tasks` routes and response models as the local app.
- Produces: `create_worker_app() -> FastAPI` adds `/health`, installs the existing error handlers, and mounts the D1 router without constructing SQLAlchemy or SQLite state.
- `src/entry.py` exports `Default = asgi.entrypoint(create_worker_app())`.

- [ ] **Step 1: Write failing route tests** for the health response, create/list/get, rename, complete, delete, 422 blank title, 404 missing ID, 409 completed rename, completion idempotency, and a D1 write failure returning 500 without changing stored data. Inject `FakeD1` through `app.dependency_overrides[get_d1_database]`.
- [ ] **Step 2: Run the tests to verify they fail:** `uv run pytest tests/test_worker_api.py -v`. Expected: missing Worker app or router imports.
- [ ] **Step 3: Implement the request-scoped D1 dependency, async routes, Worker app factory, and ASGI entry point.** Return `TaskRecord` values through the existing `TaskResponse` schema and preserve the current status codes and error bodies.
- [ ] **Step 4: Run Worker API and local API tests:** `uv run pytest tests/test_worker_api.py tests/test_api.py -v`. Expected: PASS for both backends.
- [ ] **Step 5: Commit** as `feat: expose task API through D1 Worker app`.

### Task 4: Configure Python Workers and D1 migrations

**Files:**
- Create: `architectures/mvc/migrations/0001_create_tasks.sql`
- Create: `architectures/mvc/wrangler.jsonc`
- Modify: `architectures/mvc/pyproject.toml`
- Modify: `architectures/mvc/uv.lock`
- Modify: `architectures/mvc/.gitignore`
- Create: `architectures/mvc/scripts/ensure-uv.sh`
- Create: `architectures/mvc/scripts/cloudflare-build.sh`
- Create: `architectures/mvc/scripts/cloudflare-deploy.sh`
- Test: `architectures/mvc/tests/test_d1_migrations.py`

**Interfaces:**
- Wrangler `main` is `src/entry.py`, Worker name is `aikitr-mvc-api`, compatibility flag includes `python_workers`, D1 binding is named `DB`, database name is `aikitr-mvc-tasks`, and migrations live in `migrations/`.
- Wrangler compatibility date is `2026-10-03`.
- The initial SQL migration creates `tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, title VARCHAR(200) NOT NULL, completed INTEGER NOT NULL DEFAULT 0)`.
- Worker project dependencies include FastAPI; Pywrangler packages `workers-py` and `workers-runtime-sdk` remain in the development group. SQLAlchemy, Alembic, pydantic-settings, python-dotenv, and Uvicorn remain available in the default local development group but are not bundled as Worker runtime dependencies.

- [ ] **Step 1: Write a failing migration check** that applies the SQL migration to a temporary SQLite database and verifies the `tasks` columns, primary key, default `completed` value, and insert/read behavior.
- [ ] **Step 2: Run the check to verify it fails:** `uv run pytest tests/test_d1_migrations.py -v`. Expected: missing migration or Wrangler config.
- [ ] **Step 3: Add the SQL migration and Wrangler config, then adjust `pyproject.toml` dependency groups** without changing the MVC project's `requires-python = ">=3.12"` floor. Set a syntactically valid placeholder database UUID for local D1 commands; Task 6 replaces it with the created remote ID. Regenerate `uv.lock` with `uv lock`.
- [ ] **Step 4: Add the Workers Builds wrapper scripts.** `ensure-uv.sh` installs uv `0.12.6` into `.cloudflare-tools/` only when absent and exports that directory on `PATH`; `cloudflare-build.sh` sources it and runs `uv sync --locked`; `cloudflare-deploy.sh` sources it and runs remote D1 migrations before `pywrangler deploy`.
- [ ] **Step 5: Verify local SQLite remains supported:** run `uv run pytest tests/test_api.py tests/test_d1_migrations.py -v`, then run `APP_DATABASE_URL=sqlite:///./data/cloudflare-plan-smoke.db uv run alembic upgrade head`; check shell syntax with `sh -n scripts/ensure-uv.sh scripts/cloudflare-build.sh scripts/cloudflare-deploy.sh`.
- [ ] **Step 6: Validate Worker bundling and local D1 behavior:** run `uv run pywrangler d1 migrations apply aikitr-mvc-tasks --local`, then start `uv run pywrangler dev`. At `http://127.0.0.1:8787`, verify `GET /health` returns 200, `POST /tasks` returns 201, `GET /tasks` returns the created row, `POST /tasks/{id}/complete` returns 200, and `DELETE /tasks/{id}` returns 204.
- [ ] **Step 7: Commit** as `feat: configure Python Worker and D1 migrations`.

### Task 5: Document local and deployed operation

**Files:**
- Modify: `architectures/mvc/README.md`

**Interfaces:**
- Document local D1 commands `uv run pywrangler d1 migrations apply aikitr-mvc-tasks --local` and `uv run pywrangler dev`.
- Document new schema migrations with `uv run pywrangler d1 migrations create aikitr-mvc-tasks <migration-name>` followed by the local or remote apply command.
- Document that GitHub production deploys use branch `main`, root `/architectures/mvc`, and watch path `architectures/mvc/**`.
- Document the Workers Builds commands `sh scripts/cloudflare-build.sh` and `sh scripts/cloudflare-deploy.sh`.
- Keep the existing SQLite/Alembic startup instructions for local development.

- [ ] **Step 1: Add README sections** for Cloudflare local development, D1 schema migrations, the deployed Worker endpoint, and automatic GitHub deployment. Preserve and clearly label the current SQLite/Alembic workflow.
- [ ] **Step 2: Review the rendered Markdown and commands** against `wrangler.jsonc` and the Workers Builds settings specified in Task 6. Expected: each documented command and name matches the configuration.
- [ ] **Step 3: Run final checks:** `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pywrangler dev` smoke check.
- [ ] **Step 4: Commit** as `docs: document MVC Cloudflare deployment`.

### Task 6: Provision Cloudflare and enable GitHub deployments

**Files / resources:**
- Cloudflare D1 database: `aikitr-mvc-tasks`.
- Cloudflare Worker: `aikitr-mvc-api`.
- GitHub repository: `aikitr/aikitr-python-template`.
- Cloudflare Workers Builds settings for the Worker.
- Modify: `architectures/mvc/wrangler.jsonc` with the created D1 database ID.

**Interfaces:**
- Workers Builds production branch is `main` and root directory is `/architectures/mvc`.
- Included watch path is `architectures/mvc/**`; no other path is included.
- Build command is `sh scripts/cloudflare-build.sh`.
- Deploy command is `sh scripts/cloudflare-deploy.sh`; it installs the pinned uv if needed, applies `uv run pywrangler d1 migrations apply aikitr-mvc-tasks --remote`, then runs `uv run pywrangler deploy`.

- [ ] **Step 1: Create the D1 database** named `aikitr-mvc-tasks`, record the returned database ID in `wrangler.jsonc`, and verify the configured binding is `DB`.
- [ ] **Step 2: Commit and push the completed MVC implementation and D1 binding config to `main`.** Expected: the GitHub repository contains the Worker entry, Wrangler config, SQL migrations, and README before Workers Builds is connected.
- [ ] **Step 3: Apply the migration and publish once from the committed code** by running `sh scripts/cloudflare-deploy.sh` from `architectures/mvc/`. Expected: D1 is migrated first and the `aikitr-mvc-api` Worker is created and published.
- [ ] **Step 4: Connect the GitHub repository through Cloudflare Workers Builds** and set the production branch, root directory, included watch path, build command, and deploy command exactly as listed above. Keep preview deployments disabled.
- [ ] **Step 5: Verify the Workers Builds initial deployment** completes from `main`, rerunning the same migration/deploy script through its configured commands.
- [ ] **Step 6: Verify the deployed URL** with `/health` and CRUD requests; confirm the returned task remains available across separate requests and that completed-task rename returns 409.
- [ ] **Step 7: Add the deployed `workers.dev` URL to the README and push that MVC documentation change to `main`.** Expected: the README points to the actual Worker endpoint.
- [ ] **Step 8: Verify automatic redeployment** from the README commit in Workers Builds history, then confirm `/health` still returns 200 on the deployed URL.
- [ ] **Step 9: Verify the saved Workers Builds settings** show `main`, `/architectures/mvc`, and only `architectures/mvc/**`; confirm the configured filter excludes changes outside that path.

## Cloudflare references

- [FastAPI on Python Workers](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/)
- [Query D1 from Python Workers](https://developers.cloudflare.com/d1/examples/query-d1-from-python-workers/)
- [D1 migrations](https://developers.cloudflare.com/d1/reference/migrations/)
- [Workers Builds monorepos](https://developers.cloudflare.com/workers/ci-cd/builds/advanced-setups/)
- [Workers Builds watch paths](https://developers.cloudflare.com/workers/ci-cd/builds/build-watch-paths/)
