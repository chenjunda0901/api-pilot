"""drop audit_logs table

Revision ID: 20260622_000000_drop_audit_logs
Revises: 20260620_000000_add_category_deleted_at
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260622_000000_drop_audit_logs"
down_revision = "20260620_000000_add_category_deleted_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """删除 audit_logs 表及其复合索引"""
    op.drop_index("ix_audit_log_user_id_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_log_action_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")


def downgrade() -> None:
    """重建 audit_logs 表（含原始列 + production features 扩展列 + 复合索引）"""
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
        sa.Column("previous_data_json", sa.Text(), nullable=True),
        sa.Column("diff_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_user_id_created_at", "audit_logs", ["user_id", "created_at"], unique=False)
    op.create_index("ix_audit_log_action_created_at", "audit_logs", ["action", "created_at"], unique=False)
