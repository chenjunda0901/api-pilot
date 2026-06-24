"""extend refresh_tokens for password reset support

Revision ID: 20260610_120000
Revises: 20260609_130000_add_member_permissions
Create Date: 2026-06-10 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260610_120000'
down_revision: Union[str, None] = 'c004_member_permissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('refresh_tokens') as batch_op:
        batch_op.add_column(sa.Column('purpose', sa.String(length=32), nullable=False, server_default='session'))
        batch_op.add_column(sa.Column('reset_code_hash', sa.String(length=255), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('reset_attempts', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_index('ix_refresh_tokens_purpose', ['purpose'], unique=False)
        batch_op.create_index('ix_refresh_tokens_reset_code_hash', ['reset_code_hash'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('refresh_tokens') as batch_op:
        batch_op.drop_index('ix_refresh_tokens_reset_code_hash')
        batch_op.drop_index('ix_refresh_tokens_purpose')
        batch_op.drop_column('reset_attempts')
        batch_op.drop_column('reset_code_hash')
        batch_op.drop_column('purpose')
