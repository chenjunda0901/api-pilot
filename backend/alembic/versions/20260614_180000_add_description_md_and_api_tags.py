"""add description_md to api_definitions and create api_tags / api_tag_relations

Revision ID: 20260614_180000
Revises: 20260614_120000
Create Date: 2026-06-14 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260614_180000"
down_revision: Union[str, None] = "20260614_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. api_definitions 添加 description_md 列
    op.add_column("api_definitions", sa.Column("description_md", sa.Text(), server_default="", nullable=True))

    # 2. 创建 api_tags 表
    op.create_table(
        "api_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(20), nullable=True, server_default="#7a8fd0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_api_tag_project_name"),
    )
    op.create_index("ix_api_tags_project_id", "api_tags", ["project_id"])

    # 3. 创建 api_tag_relations 表
    op.create_table(
        "api_tag_relations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("api_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["api_id"], ["api_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["api_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_id", "tag_id", name="uq_api_tag_relation"),
    )
    op.create_index("ix_api_tag_relations_api_id", "api_tag_relations", ["api_id"])
    op.create_index("ix_api_tag_relations_tag_id", "api_tag_relations", ["tag_id"])


def downgrade() -> None:
    op.drop_table("api_tag_relations")
    op.drop_table("api_tags")
    op.drop_column("api_definitions", "description_md")
