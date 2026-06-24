"""add_notifications_table

Revision ID: 20260530_221252_add_notifications
Revises: 20260530_221252_enhance_mock_rules
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260530_221252_add_notifications'
down_revision = '20260530_221100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Integer(), server_default='0'),
        sa.Column('link', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])


def downgrade() -> None:
    op.drop_table('notifications')
