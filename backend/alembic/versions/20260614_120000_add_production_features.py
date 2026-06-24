"""production-grade features: test plans, schedules, data schemas, advanced mock,
snapshots, comments, subscriptions, webhooks, dispatch history, metrics, assertions, variables.

- 新增 13 张表：api_test_plans / api_test_plan_steps / schedules / data_schemas /
  mock_expectations / mock_recordings / api_snapshots / comments / subscriptions /
  webhooks / notification_dispatches / metrics_snapshots / api_assertions / variables
- 扩展 audit_logs：previous_data_json / diff_json

Revision ID: 20260614_120000
Revises: 9ff26f18f976
Create Date: 2026-06-14 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260614_120000"
down_revision: Union[str, None] = "9ff26f18f976"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === 1. api_test_plans ===
    op.create_table(
        "api_test_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("concurrency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("failure_strategy", sa.String(length=20), nullable=False, server_default="continue"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_test_plans_project_id", "api_test_plans", ["project_id"], unique=False)
    op.create_index("ix_api_test_plans_status", "api_test_plans", ["status"], unique=False)
    op.create_index("ix_api_test_plans_project_status", "api_test_plans", ["project_id", "status"], unique=False)

    # === 2. api_test_plan_steps ===
    op.create_table(
        "api_test_plan_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("api_test_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_type", sa.String(length=20), nullable=False),
        sa.Column("step_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_test_plan_steps_plan_id", "api_test_plan_steps", ["plan_id"], unique=False)
    op.create_index("ix_api_test_plan_steps_plan_order", "api_test_plan_steps", ["plan_id", "order_index"], unique=False)

    # === 3. schedules ===
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("api_test_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cron_expression", sa.String(length=100), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedules_plan_id", "schedules", ["plan_id"], unique=False)
    op.create_index("ix_schedules_enabled", "schedules", ["enabled"], unique=False)
    op.create_index("ix_schedules_enabled_next_run", "schedules", ["enabled", "next_run_at"], unique=False)

    # === 4. data_schemas ===
    op.create_table(
        "data_schemas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("schema_json", sa.Text(), nullable=False),
        sa.Column("example_json", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_schemas_project_id", "data_schemas", ["project_id"], unique=False)
    op.create_index("ix_data_schemas_name", "data_schemas", ["name"], unique=False)
    op.create_index("ix_data_schemas_project_name", "data_schemas", ["project_id", "name"], unique=False)

    # === 5. mock_expectations ===
    op.create_table(
        "mock_expectations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("api_id", sa.Integer(), sa.ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("matchers_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("expected_status", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("expected_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mock_expectations_project_id", "mock_expectations", ["project_id"], unique=False)
    op.create_index("ix_mock_expectations_api_id", "mock_expectations", ["api_id"], unique=False)

    # === 6. mock_recordings ===
    op.create_table(
        "mock_recordings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("api_id", sa.Integer(), sa.ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mock_recordings_project_id", "mock_recordings", ["project_id"], unique=False)
    op.create_index("ix_mock_recordings_api_id", "mock_recordings", ["api_id"], unique=False)
    op.create_index("ix_mock_recordings_captured_at", "mock_recordings", ["captured_at"], unique=False)

    # === 7. api_snapshots ===
    op.create_table(
        "api_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("api_id", sa.Integer(), sa.ForeignKey("api_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_data", sa.Text(), nullable=False),
        sa.Column("change_type", sa.String(length=20), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("changed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_snapshots_api_id", "api_snapshots", ["api_id"], unique=False)
    op.create_index("ix_api_snapshots_api_created", "api_snapshots", ["api_id", "created_at"], unique=False)

    # === 8. comments ===
    # 自引用 FK 在 SQLite 下需要 use_alter；显式两步：先建表不带 self FK，再 ALTER 加约束
    with op.batch_alter_table("comments", schema=None) as batch_op:
        pass
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(length=30), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("mentions_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_project_id", "comments", ["project_id"], unique=False)
    op.create_index("ix_comments_user_id", "comments", ["user_id"], unique=False)
    op.create_index("ix_comments_resource", "comments", ["resource_type", "resource_id"], unique=False)
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"], unique=False)
    # 自引用外键：单独以 ALTER 方式添加以兼容 SQLite
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_comments_parent_id_comments",
            "comments",
            ["parent_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # === 9. subscriptions ===
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_type", sa.String(length=30), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "resource_type", "resource_id", name="uq_subscriptions_user_resource"),
    )
    op.create_index("ix_subscriptions_resource", "subscriptions", ["resource_type", "resource_id"], unique=False)

    # === 10. webhooks ===
    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("events_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("template", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhooks_project_id", "webhooks", ["project_id"], unique=False)
    op.create_index("ix_webhooks_enabled", "webhooks", ["enabled"], unique=False)
    op.create_index("ix_webhooks_channel", "webhooks", ["channel"], unique=False)

    # === 11. notification_dispatches ===
    op.create_table(
        "notification_dispatches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("event", sa.String(length=100), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_dispatches_user_id", "notification_dispatches", ["user_id"], unique=False)
    op.create_index("ix_notification_dispatches_project_id", "notification_dispatches", ["project_id"], unique=False)
    op.create_index("ix_notification_dispatches_status", "notification_dispatches", ["status"], unique=False)
    op.create_index("ix_notification_dispatches_status_created", "notification_dispatches", ["status", "created_at"], unique=False)

    # === 12. metrics_snapshots ===
    op.create_table(
        "metrics_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("metric", sa.String(length=30), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metrics_snapshots_project_id", "metrics_snapshots", ["project_id"], unique=False)
    op.create_index("ix_metrics_snapshots_scope", "metrics_snapshots", ["scope", "scope_id"], unique=False)
    op.create_index("ix_metrics_snapshots_scope_metric_time", "metrics_snapshots", ["scope", "scope_id", "metric", "recorded_at"], unique=False)

    # === 13. api_assertions ===
    op.create_table(
        "api_assertions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_type", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("assertion_type", sa.String(length=30), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_assertions_owner", "api_assertions", ["owner_type", "owner_id"], unique=False)
    op.create_index("ix_api_assertions_owner_order", "api_assertions", ["owner_type", "owner_id", "order_index"], unique=False)

    # === 14. variables ===
    op.create_table(
        "variables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_secret", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "scope_id", "name", name="uq_variables_scope_name"),
    )
    op.create_index("ix_variables_scope_name", "variables", ["scope", "name"], unique=False)

    # === 15. 扩展 audit_logs：previous_data_json / diff_json ===
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("previous_data_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("diff_json", sa.Text(), nullable=True))


def downgrade() -> None:
    # === 回滚顺序与升级相反 ===

    # 15. 移除 audit_logs 新增字段
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_column("diff_json")
        batch_op.drop_column("previous_data_json")

    # 14. variables
    op.drop_index("ix_variables_scope_name", table_name="variables")
    op.drop_table("variables")

    # 13. api_assertions
    op.drop_index("ix_api_assertions_owner_order", table_name="api_assertions")
    op.drop_index("ix_api_assertions_owner", table_name="api_assertions")
    op.drop_table("api_assertions")

    # 12. metrics_snapshots
    op.drop_index("ix_metrics_snapshots_scope_metric_time", table_name="metrics_snapshots")
    op.drop_index("ix_metrics_snapshots_scope", table_name="metrics_snapshots")
    op.drop_index("ix_metrics_snapshots_project_id", table_name="metrics_snapshots")
    op.drop_table("metrics_snapshots")

    # 11. notification_dispatches
    op.drop_index("ix_notification_dispatches_status_created", table_name="notification_dispatches")
    op.drop_index("ix_notification_dispatches_status", table_name="notification_dispatches")
    op.drop_index("ix_notification_dispatches_project_id", table_name="notification_dispatches")
    op.drop_index("ix_notification_dispatches_user_id", table_name="notification_dispatches")
    op.drop_table("notification_dispatches")

    # 10. webhooks
    op.drop_index("ix_webhooks_channel", table_name="webhooks")
    op.drop_index("ix_webhooks_enabled", table_name="webhooks")
    op.drop_index("ix_webhooks_project_id", table_name="webhooks")
    op.drop_table("webhooks")

    # 9. subscriptions
    op.drop_index("ix_subscriptions_resource", table_name="subscriptions")
    op.drop_table("subscriptions")

    # 8. comments - 先拆自引用 FK 再删表
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_constraint("fk_comments_parent_id_comments", type_="foreignkey")
    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_index("ix_comments_resource", table_name="comments")
    op.drop_index("ix_comments_user_id", table_name="comments")
    op.drop_index("ix_comments_project_id", table_name="comments")
    op.drop_table("comments")

    # 7. api_snapshots
    op.drop_index("ix_api_snapshots_api_created", table_name="api_snapshots")
    op.drop_index("ix_api_snapshots_api_id", table_name="api_snapshots")
    op.drop_table("api_snapshots")

    # 6. mock_recordings
    op.drop_index("ix_mock_recordings_captured_at", table_name="mock_recordings")
    op.drop_index("ix_mock_recordings_api_id", table_name="mock_recordings")
    op.drop_index("ix_mock_recordings_project_id", table_name="mock_recordings")
    op.drop_table("mock_recordings")

    # 5. mock_expectations
    op.drop_index("ix_mock_expectations_api_id", table_name="mock_expectations")
    op.drop_index("ix_mock_expectations_project_id", table_name="mock_expectations")
    op.drop_table("mock_expectations")

    # 4. data_schemas
    op.drop_index("ix_data_schemas_project_name", table_name="data_schemas")
    op.drop_index("ix_data_schemas_name", table_name="data_schemas")
    op.drop_index("ix_data_schemas_project_id", table_name="data_schemas")
    op.drop_table("data_schemas")

    # 3. schedules
    op.drop_index("ix_schedules_enabled_next_run", table_name="schedules")
    op.drop_index("ix_schedules_enabled", table_name="schedules")
    op.drop_index("ix_schedules_plan_id", table_name="schedules")
    op.drop_table("schedules")

    # 2. api_test_plan_steps
    op.drop_index("ix_api_test_plan_steps_plan_order", table_name="api_test_plan_steps")
    op.drop_index("ix_api_test_plan_steps_plan_id", table_name="api_test_plan_steps")
    op.drop_table("api_test_plan_steps")

    # 1. api_test_plans
    op.drop_index("ix_api_test_plans_project_status", table_name="api_test_plans")
    op.drop_index("ix_api_test_plans_status", table_name="api_test_plans")
    op.drop_index("ix_api_test_plans_project_id", table_name="api_test_plans")
    op.drop_table("api_test_plans")
