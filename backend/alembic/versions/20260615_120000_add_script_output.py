"""add script_output and script_error to report_steps

Revision ID: 20260615_120000_add_script_output
Revises: 20260614_230000_add_share_password
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa

revision = "20260615_120000_add_script_output"
down_revision = "20260614_230000_add_share_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_steps", sa.Column("script_output", sa.Text(), nullable=True))
    op.add_column("report_steps", sa.Column("script_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("report_steps", "script_error")
    op.drop_column("report_steps", "script_output")
