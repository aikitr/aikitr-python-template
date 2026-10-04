from logging.config import fileConfig

from sqlalchemy import text

from alembic import context
from app.config import get_settings
from app.database import Base, build_engine
from app.models.task import Task  # noqa: F401 - registers the table with Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    """Limit autogenerate to the schema owned by this template."""
    if type_ == "schema":
        return name == "task_app"
    if type_ == "table":
        return parent_names.get("schema_name") == "task_app"
    return True


def configure(**kwargs):
    context.configure(
        target_metadata=target_metadata,
        version_table_schema="task_app",
        include_schemas=True,
        include_name=include_name,
        **kwargs,
    )


def run_migrations_offline() -> None:
    configure(
        url=get_settings().alembic_database_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.execute("CREATE SCHEMA IF NOT EXISTS task_app")
        context.execute("REVOKE ALL ON SCHEMA task_app FROM PUBLIC")
        context.run_migrations()


def run_migrations_online() -> None:
    engine = build_engine(get_settings().alembic_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS task_app"))
            connection.execute(text("REVOKE ALL ON SCHEMA task_app FROM PUBLIC"))
            configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
