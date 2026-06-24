"""add deleted_at for scene_steps

Revision ID: 20260622_000001_add_scene_step_deleted_at
Revises: 20260622_000000_drop_audit_logs
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260622_000001_add_scene_step_deleted_at"
down_revision = "20260622_000000_drop_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 scene_steps 添加 deleted_at 软删除字段"""
    op.add_column('scene_steps', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """回滚：删除 scene_steps.deleted_at"""
    op.drop_column('scene_steps', 'deleted_at')
