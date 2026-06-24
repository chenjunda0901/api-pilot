"""add composite indexes for ApiTestHistory and AuditLog

Revision ID: 20260619_000000_add_composite_indexes
Revises: 20260617_000000_add_var_persist_target
Create Date: 2026-06-19
"""

from alembic import op

revision = "20260619_000000_add_composite_indexes"
down_revision = "20260617_000000_add_var_persist_target"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 ApiTestHistory 和 AuditLog 添加复合索引"""
    # ApiTestHistory 复合索引
    op.create_index(
        "ix_api_test_history_api_id_created_at",
        "api_test_histories",
        ["api_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_api_test_history_environment_id_created_at",
        "api_test_histories",
        ["environment_id", "created_at"],
        unique=False,
    )

    # AuditLog 复合索引
    op.create_index(
        "ix_audit_log_user_id_created_at",
        "audit_logs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_action_created_at",
        "audit_logs",
        ["action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """回滚：删除复合索引"""
    op.drop_index("ix_api_test_history_api_id_created_at", table_name="api_test_histories")
    op.drop_index("ix_api_test_history_environment_id_created_at", table_name="api_test_histories")
    op.drop_index("ix_audit_log_user_id_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_log_action_created_at", table_name="audit_logs")
