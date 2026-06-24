"""add is_starred and sort_order to api_definitions

Revision ID: 20260614_130000
Revises: 20260614_120000
Create Date: 2026-06-14 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260614_130000"
down_revision: Union[str, None] = "20260614_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("api_definitions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_starred", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    with op.batch_alter_table("api_definitions", schema=None) as batch_op:
        batch_op.drop_column("sort_order")
        batch_op.drop_column("is_starred")
