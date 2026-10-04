# Python 数据源示例

按数据库组织可直接复制的完整项目；每个架构示例都自包含，使用 Python 3.12 和 uv。

```text
datasources/
└── supabase/
    └── mvc/           # FastAPI MVC + Supabase PostgreSQL
```

| 数据源 | 架构 | 数据库访问 | 项目入口 |
|---|---|---|---|
| Supabase PostgreSQL | MVC | SQLAlchemy 2 + Psycopg 3，同步事务 | [启动和复制说明](supabase/mvc/README.md) |

以任务管理业务展示创建、查询、修改、完成和删除。选择通用架构时，也可以参考根目录的 [架构示例](../architectures/README.md)。

从仓库根目录复制 Supabase MVC 示例：

```bash
cp -R datasources/supabase/mvc ../my-supabase-service
cd ../my-supabase-service
cp .env.example .env
uv sync --locked
```

填写 `.env` 中的 Supabase 数据库连接串后，执行示例 README 中的迁移和启动命令。
