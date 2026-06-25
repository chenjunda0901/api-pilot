"""add refresh_tokens table + fix SQLite compatibility

Revision ID: 35bfeb425aa1
Revises: 28f4472d1bd6
Create Date: 2026-05-22 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35bfeb425aa1'
down_revision: Union[str, None] = '28f4472d1bd6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_exists(t, c):
    import sqlite3
    assert t.isidentifier(), f"Invalid table name: {t}"
    db = op.get_bind().engine.url.database.replace('+aiosqlite', '')
    conn = sqlite3.connect(db)
    try:
        return c in [x[1] for x in conn.execute(sa.text(f"PRAGMA table_info({t})")).fetchall()]
    finally:
        conn.close()


def upgrade() -> None:
    # --- Drop obsolete table (was never created in SQLite) ---
    op.execute("DROP TABLE IF EXISTS mock_expectations")

    # --- Fix debug_history NOT NULL constraints (SQLite-compatible batch mode) ---
    with op.batch_alter_table('debug_history') as batch_op:
        batch_op.alter_column('request_headers',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('request_body',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('response_headers',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('response_body',
               existing_type=sa.TEXT(),
               nullable=False)
        batch_op.alter_column('duration_ms',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=False)

    if not _col_exists('test_reports', 'share_enabled'):
        op.add_column('test_reports', sa.Column('share_enabled', sa.INTEGER(), server_default=sa.text('1'), nullable=True))

    with op.batch_alter_table('test_reports') as batch_op:
        batch_op.alter_column('share_enabled',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('1'))

    # --- Create refresh_tokens table for multi-session support ---
    op.create_table('refresh_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('token', sa.Text(), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(),
                  default=False, nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('refresh_tokens')

    with op.batch_alter_table('test_reports') as batch_op:
        batch_op.alter_column('share_enabled',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text('1'))

    with op.batch_alter_table('debug_history') as batch_op:
        batch_op.alter_column('created_at', nullable=True,
               existing_type=sa.DATETIME())
        batch_op.alter_column('duration_ms', nullable=True,
               existing_type=sa.INTEGER())
        batch_op.alter_column('response_body', nullable=True,
               existing_type=sa.TEXT())
        batch_op.alter_column('response_headers', nullable=True,
               existing_type=sa.TEXT())
        batch_op.alter_column('request_body', nullable=True,
               existing_type=sa.TEXT())
        batch_op.alter_column('request_headers', nullable=True,
               existing_type=sa.TEXT())

    op.execute("DROP TABLE IF EXISTS mock_expectations")
