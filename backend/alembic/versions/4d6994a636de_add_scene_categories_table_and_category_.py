"""add scene_categories table and category_id to test_scenes

Revision ID: 4d6994a636de
Revises: 43286ea55fcd
Create Date: 2026-05-13 15:02:38.024081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d6994a636de'
down_revision: Union[str, None] = '43286ea55fcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('scene_categories',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['scene_categories.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scene_categories_parent_id'), 'scene_categories', ['parent_id'], unique=False)
    op.create_index(op.f('ix_scene_categories_project_id'), 'scene_categories', ['project_id'], unique=False)

    with op.batch_alter_table('test_scenes') as batch_op:
        batch_op.add_column(sa.Column('category_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_test_scenes_category_id', ['category_id'])
        batch_op.create_foreign_key('fk_test_scenes_category_id', 'scene_categories', ['category_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('test_scenes') as batch_op:
        batch_op.drop_constraint('fk_test_scenes_category_id', type_='foreignkey')
        batch_op.drop_index('ix_test_scenes_category_id')
        batch_op.drop_column('category_id')

    op.drop_index(op.f('ix_scene_categories_project_id'), table_name='scene_categories')
    op.drop_index(op.f('ix_scene_categories_parent_id'), table_name='scene_categories')
    op.drop_table('scene_categories')
