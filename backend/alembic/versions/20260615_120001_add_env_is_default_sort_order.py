"""add is_default and sort_order to environments

Revision ID: 20260615_120001_add_env_is_default_sort_order
Revises: 20260615_120000_add_script_output
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260615_120001_add_env_is_default_sort_order"
down_revision = "20260615_120000_add_script_output"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "environments",
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "environments",
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("environments", "sort_order")
    op.drop_column("environments", "is_default")
