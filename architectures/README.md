# Python 架构示例

每种架构都是一个可以单独复制到新仓库的 FastAPI 项目，统一使用 SQLite、SQLAlchemy 2、Alembic 和 uv。四套实现相同的任务管理 API，方便对照职责分工和依赖方向。

| 示例 | 结构 | 适用场景 |
|---|---|---|
| [MVC](mvc/README.md) | Model、View、Controller | 小型 Web 应用及传统 MVC 团队 |
| [分层架构](layered/README.md) | API、Service、Repository、Model | 职责明确、希望逐步拆分的应用 |
| [DDD](ddd/README.md) | Domain、Application、Infrastructure、Interface | 领域规则较多，需要保护领域模型的服务 |
| [六边形架构](hexagonal/README.md) | Core、Ports、Adapters、Bootstrap | 需要替换入口或基础设施的服务 |

这些架构可以组合使用。例如 DDD 项目也可以用六边形依赖方向组织技术边界。它们是可选的组织方法，按业务规则复杂度、团队熟悉度和未来变化点选择即可。

## 共同 API

- POST /tasks：创建任务。
- GET /tasks、GET /tasks/{id}：查询任务。
- PATCH /tasks/{id}：修改标题。
- POST /tasks/{id}/complete：完成任务。
- DELETE /tasks/{id}：删除任务。
- GET /health：健康检查。

空标题返回 422，任务不存在返回 404，已完成任务不能改名（409）；重复完成成功。成功创建返回 201，删除返回 204。

## 复制一个示例

例如，将 MVC 项目复制为新服务：

    cp -R architectures/mvc ../my-python-service
    cd ../my-python-service
    cp .env.example .env
    uv sync --locked
    uv run alembic upgrade head
    uv run uvicorn app.main:create_app --factory --reload

在浏览器打开 http://127.0.0.1:8000/docs 调试 API。更多步骤请看各架构 README。
