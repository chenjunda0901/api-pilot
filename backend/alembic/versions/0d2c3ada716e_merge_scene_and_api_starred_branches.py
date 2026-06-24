"""merge scene and api starred branches

Revision ID: 0d2c3ada716e
Revises: 20260614_130000, 20260622_000001_add_scene_step_deleted_at
Create Date: 2026-06-22 18:41:30.183592

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '0d2c3ada716e'
down_revision: Union[str, None] = ('20260614_130000', '20260622_000001_add_scene_step_deleted_at')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
