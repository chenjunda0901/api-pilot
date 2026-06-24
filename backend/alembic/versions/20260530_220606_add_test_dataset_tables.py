"""add test dataset tables

Revision ID: 20260530_220606
Revises: 35bfeb425aa1
Create Date: 2026-05-30 22:06:06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260530_220606"
down_revision: Union[str, None] = "35bfeb425aa1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name):
    import sqlite3
    conn = sqlite3.connect(op.get_bind().engine.url.database.replace('+aiosqlite', ''))
    result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
    conn.close()
    return result is not None


def upgrade() -> None:
    if _table_exists("test_datasets"):
        return

    op.create_table(
        "test_datasets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "test_dataset_rows",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("dataset_id", sa.Integer, sa.ForeignKey("test_datasets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("data", sa.Text, nullable=True),
        sa.Column("enabled", sa.Boolean, default=True),
        sa.Column("sort_order", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("test_dataset_rows")
    op.drop_table("test_datasets")
