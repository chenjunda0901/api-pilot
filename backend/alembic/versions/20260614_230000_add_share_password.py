"""add share_password to test_reports

Revision ID: 20260614_230000_add_share_password
Revises: 20260614_220000_add_env_base_url_auth
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20260614_230000_add_share_password"
down_revision = "20260614_220000_add_env_base_url_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_reports", sa.Column("share_password", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("test_reports", "share_password")
