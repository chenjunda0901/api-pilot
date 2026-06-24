"""add_debug_history

Revision ID: 28f4472d1bd6
Revises: badded1ae03b
Create Date: 2026-05-17 09:39:46.930082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28f4472d1bd6'
down_revision: Union[str, None] = 'badded1ae03b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'debug_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_id', sa.Integer(), nullable=False, index=True),
        sa.Column('project_id', sa.Integer(), nullable=False, index=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('request_headers', sa.Text(), nullable=True),
        sa.Column('request_body', sa.Text(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_headers', sa.Text(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('debug_history')
