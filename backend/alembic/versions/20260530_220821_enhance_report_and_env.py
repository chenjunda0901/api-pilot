"""enhance report and environment models

Revision ID: 20260530_220821
Revises: 20260530_220606
Create Date: 2026-05-30
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260530_220821"
down_revision: Union[str, None] = "20260530_220606"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import sqlite3 as _sqlite
    _db = op.get_bind().engine.url.database.replace('+aiosqlite', '')
    def _col_exists(t, c):
        assert t.isidentifier(), f"Invalid table name: {t}"
        conn = _sqlite.connect(_db)
        r = c in [x[1] for x in conn.execute(sa.text(f"PRAGMA table_info({t})")).fetchall()]
        conn.close()
        return r
    if not _col_exists("test_reports", "compare_with"):
        op.add_column("test_reports", sa.Column("compare_with", sa.Integer, nullable=True))
    if not _col_exists("test_reports", "tags"):
        op.add_column("test_reports", sa.Column("tags", sa.Text, nullable=True))
    if not _col_exists("test_reports", "share_token"):
        op.add_column("test_reports", sa.Column("share_token", sa.String(64), unique=True, nullable=True))
    if not _col_exists("test_reports", "share_enabled"):
        op.add_column("test_reports", sa.Column("share_enabled", sa.Boolean, default=False))
    if not _col_exists("environments", "is_default"):
        op.add_column("environments", sa.Column("is_default", sa.Boolean, default=False))
    if not _col_exists("environments", "sort_order"):
        op.add_column("environments", sa.Column("sort_order", sa.Integer, default=0))


def downgrade() -> None:
    op.drop_column("environments", "sort_order")
    op.drop_column("environments", "is_default")
    op.drop_column("test_reports", "share_enabled")
    op.drop_column("test_reports", "share_token")
    op.drop_column("test_reports", "tags")
    op.drop_column("test_reports", "compare_with")