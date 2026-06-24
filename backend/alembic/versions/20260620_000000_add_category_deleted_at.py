"""add deleted_at for api_categories

Revision ID: 20260620_000000_add_category_deleted_at
Revises: 20260619_000000_add_composite_indexes
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260620_000000_add_category_deleted_at"
down_revision = "20260619_000000_add_composite_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """为 api_categories 添加 deleted_at 软删除字段"""
    op.add_column('api_categories', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """回滚：删除 api_categories.deleted_at"""
    op.drop_column('api_categories', 'deleted_at')
