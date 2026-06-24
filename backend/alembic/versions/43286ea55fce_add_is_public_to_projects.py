"""add is_public to projects

Revision ID: 43286ea55fce
Revises: 4d6994a636de
Create Date: 2026-05-13 23:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '43286ea55fce'
down_revision = '4d6994a636de'
branch_labels = None
depends_on = None


def upgrade():
    import sqlite3
    conn = sqlite3.connect(op.get_bind().engine.url.database.replace('+aiosqlite', ''))
    existing = [r[1] for r in conn.execute("PRAGMA table_info(projects)").fetchall()]
    conn.close()
    if 'global_demo' not in existing:
        op.add_column('projects', sa.Column('global_demo', sa.Integer(), server_default=sa.text('0'), nullable=False))
    if 'is_public' not in existing:
        op.add_column('projects', sa.Column('is_public', sa.Boolean(), server_default=sa.text('0'), nullable=False))
        op.execute("UPDATE projects SET is_public = 1 WHERE global_demo = 1")


def downgrade():
    op.drop_column('projects', 'is_public')
