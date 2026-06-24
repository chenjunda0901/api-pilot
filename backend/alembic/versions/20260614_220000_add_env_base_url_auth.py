"""add base_url and auth_config to environments

Revision ID: 20260614_220000_add_env_base_url_auth
Revises: 20260614_210000
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20260614_220000_add_env_base_url_auth"
down_revision = "20260614_210000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("environments", sa.Column("base_url", sa.String(500), nullable=True))
    op.add_column("environments", sa.Column("auth_config", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("environments", "auth_config")
    op.drop_column("environments", "base_url")
