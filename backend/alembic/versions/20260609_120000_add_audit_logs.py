"""add audit_logs table

Revision ID: c003_audit_logs
Revises: c002_api_test_history
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "c003_audit_logs"
down_revision = "c002_api_test_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建审计日志表"""
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.Integer(), nullable=True, index=True),
        sa.Column("description", sa.Text(), nullable=False, default=""),
        sa.Column("request_data", sa.Text(), nullable=True),
        sa.Column("response_data", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="success", index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False, index=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """删除审计日志表"""
    op.drop_table("audit_logs")
