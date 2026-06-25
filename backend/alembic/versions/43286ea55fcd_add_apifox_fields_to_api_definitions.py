"""add_apifox_fields_to_api_definitions

Revision ID: 43286ea55fcd
Revises: 7df5d0613ffb
Create Date: 2026-05-13 13:58:06.817935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43286ea55fcd'
down_revision: Union[str, None] = '7df5d0613ffb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import sqlite3 as _sqlite
    _db = op.get_bind().engine.url.database.replace('+aiosqlite', '')

    def _col_exists(table: str, col: str) -> bool:
        assert table.isidentifier(), f"Invalid table name: {table}"
        conn = _sqlite.connect(_db)
        exists = col in [x[1] for x in conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()]
        conn.close()
        return exists

    if not _col_exists('api_definitions', 'apifox_id'):
        op.add_column('api_definitions', sa.Column('apifox_id', sa.String(length=100), nullable=True))
    if not _col_exists('api_definitions', 'response_schema'):
        op.add_column('api_definitions', sa.Column('response_schema', sa.Text(), nullable=True))
    if not _col_exists('api_definitions', 'response_examples'):
        op.add_column('api_definitions', sa.Column('response_examples', sa.Text(), nullable=True))

    try:
        op.create_index(op.f('ix_api_definitions_apifox_id'), 'api_definitions', ['apifox_id'], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    op.drop_index(op.f('ix_api_definitions_apifox_id'), table_name='api_definitions')
    op.drop_column('api_definitions', 'response_examples')
    op.drop_column('api_definitions', 'response_schema')
    op.drop_column('api_definitions', 'apifox_id')
