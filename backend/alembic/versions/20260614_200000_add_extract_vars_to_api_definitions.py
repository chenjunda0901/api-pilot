"""add extract_vars to api_definitions

Revision ID: 20260614_200001
Revises: 20260614_200000
Create Date: 2026-06-14 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260614_200001"
down_revision: Union[str, None] = "20260614_200000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_definitions", sa.Column("extract_vars", sa.Text(), server_default="[]", nullable=True))


def downgrade() -> None:
    op.drop_column("api_definitions", "extract_vars")
