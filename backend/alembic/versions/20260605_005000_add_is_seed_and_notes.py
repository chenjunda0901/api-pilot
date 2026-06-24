"""add is_seed columns and test_reports.notes

Revision ID: c001_seed_notes
Revises: 20260530_221252
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "c001_seed_notes"
down_revision = "20260530_221252_add_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_reports", sa.Column("notes", sa.Text(), server_default="", nullable=False))
    for table in ("api_categories", "api_definitions", "test_cases", "test_scenes"):
        op.add_column(table, sa.Column("is_seed", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    for table in ("api_categories", "api_definitions", "test_cases", "test_scenes"):
        op.drop_column(table, "is_seed")
    op.drop_column("test_reports", "notes")