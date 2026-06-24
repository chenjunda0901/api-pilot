"""add var_persist_target to test_scenes

Revision ID: 20260617_000000_add_var_persist_target
Revises: 20260615_120001_add_env_is_default_sort_order
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260617_000000_add_var_persist_target"
down_revision = "20260615_120001_add_env_is_default_sort_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_scenes",
        sa.Column(
            "var_persist_target",
            sa.String(length=20),
            server_default=sa.text("'environment'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("test_scenes", "var_persist_target")
