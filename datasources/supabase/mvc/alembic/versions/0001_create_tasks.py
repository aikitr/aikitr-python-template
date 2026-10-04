"""Create task tables in a private Supabase schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_create_tasks"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="task_app",
    )
    op.execute("ALTER TABLE task_app.tasks ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON TABLE task_app.tasks FROM PUBLIC")


def downgrade() -> None:
    op.drop_table("tasks", schema="task_app")
