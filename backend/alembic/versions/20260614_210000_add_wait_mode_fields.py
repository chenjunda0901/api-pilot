"""add wait mode fields to scene_steps

Revision ID: 20260614_210000
Revises: 20260614_200001
Create Date: 2026-06-14 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_210000"
down_revision: Union[str, None] = "20260614_200001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scene_steps", sa.Column("wait_mode", sa.String(10), server_default="fixed", nullable=True))
    op.add_column("scene_steps", sa.Column("wait_min", sa.Integer(), nullable=True))
    op.add_column("scene_steps", sa.Column("wait_max", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("scene_steps", "wait_max")
    op.drop_column("scene_steps", "wait_min")
    op.drop_column("scene_steps", "wait_mode")
