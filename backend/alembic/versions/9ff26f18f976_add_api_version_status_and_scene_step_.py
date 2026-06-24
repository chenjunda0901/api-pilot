"""add API version/status fields and scene step dependency

- api_definitions: add status, version, created_by columns + index
- scene_steps: add depends_on_step_id column
- refresh_tokens: add missing indexes from previous migration

Revision ID: 9ff26f18f976
Revises: 20260610_120000
Create Date: 2026-06-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ff26f18f976'
down_revision: Union[str, None] = '20260610_120000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === api_definitions: 新增版本管理字段 ===
    with op.batch_alter_table('api_definitions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'))
        batch_op.add_column(sa.Column('version', sa.String(length=20), nullable=False, server_default='v1.0'))
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.create_index('ix_api_definitions_created_by', ['created'], unique=False)

    # === scene_steps: 新增步骤依赖字段 ===
    with op.batch_alter_table('scene_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('depends_on_step_id', sa.Integer(), nullable=True))

    # === refresh_tokens: 补充上一迁移的索引 ===
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.create_index('ix_refresh_tokens_purpose', ['purpose'], unique=False)
        batch_op.create_index('ix_refresh_tokens_reset_code_hash', ['reset_code_hash'], unique=False)


def downgrade() -> None:
    # === refresh_tokens indexes ===
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.drop_index('ix_refresh_tokens_reset_code_hash')
        batch_op.drop_index('ix_refresh_tokens_purpose')

    # === scene_steps ===
    with op.batch_alter_table('scene_steps', schema=None) as batch_op:
        batch_op.drop_column('depends_on_step_id')

    # === api_definitions ===
    with op.batch_alter_table('api_definitions', schema=None) as batch_op:
        batch_op.drop_index('ix_api_definitions_created_by')
        batch_op.drop_column('created_by')
        batch_op.drop_column('version')
        batch_op.drop_column('status')
