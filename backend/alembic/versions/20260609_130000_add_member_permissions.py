"""add permissions column to project_members

Revision ID: c004_member_permissions
Revises: c003_audit_logs
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "c004_member_permissions"
down_revision = "c003_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为project_members表添加permissions字段"""
    op.add_column("project_members", sa.Column("permissions", sa.Text(), nullable=True))


def downgrade() -> None:
    """删除permissions字段"""
    op.drop_column("project_members", "permissions")
