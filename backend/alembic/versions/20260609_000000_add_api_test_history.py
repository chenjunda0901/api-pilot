"""add api_test_histories table

Revision ID: c002_api_test_history
Revises: c001_seed_notes
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = "c002_api_test_history"
down_revision = "c001_seed_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建接口测试历史表"""
    op.create_table(
        "api_test_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("api_id", sa.Integer(), sa.ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("environment_id", sa.Integer(), sa.ForeignKey("environments.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("executor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_url", sa.String(500), default="", nullable=False),
        sa.Column("request_method", sa.String(10), nullable=False, default="GET"),
        sa.Column("request_headers", sa.Text(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("response_status", sa.Integer(), default=0, nullable=False),
        sa.Column("response_headers", sa.Text(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("duration", sa.Float(), default=0.0, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), default="unknown", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False, index=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """删除接口测试历史表"""
    op.drop_table("api_test_histories")
