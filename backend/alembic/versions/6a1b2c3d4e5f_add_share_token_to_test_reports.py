"""add share_token to test_reports

Revision ID: 6a1b2c3d4e5f
Revises: 43286ea55fce
Create Date: 2026-05-14 11:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '6a1b2c3d4e5f'
down_revision = '43286ea55fce'
branch_labels = None
depends_on = None


def upgrade():
    import sqlite3
    conn = sqlite3.connect(op.get_bind().engine.url.database.replace('+aiosqlite', ''))
    existing = [r[1] for r in conn.execute("PRAGMA table_info(test_reports)").fetchall()]
    conn.close()
    if 'share_token' not in existing:
        with op.batch_alter_table('test_reports') as batch_op:
            batch_op.add_column(sa.Column('share_token', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('test_reports') as batch_op:
        batch_op.drop_column('share_token')