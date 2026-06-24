"""add scene_dataset table

Revision ID: 20260614_200000
Revises: 20260614_180000
Create Date: 2026-06-14 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_200000"
down_revision: Union[str, None] = "20260614_180000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scene_dataset",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scene_id", sa.Integer(), sa.ForeignKey("test_scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("type", sa.String(10), server_default="json", nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scene_dataset_scene_id", "scene_dataset", ["scene_id"])


def downgrade() -> None:
    op.drop_index("ix_scene_dataset_scene_id", table_name="scene_dataset")
    op.drop_table("scene_dataset")
