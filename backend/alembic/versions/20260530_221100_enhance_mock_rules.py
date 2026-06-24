"""enhance_mock_rules: conditions, script, hit_count, mock_hit_logs

Revision ID: 20260530_221100
Revises: 20260530_220821
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260530_221100'
down_revision = '20260530_220821'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # MockRule 新增字段
    op.add_column('mock_rules', sa.Column('conditions', sa.Text(), nullable=True, comment='条件JSON数组'))
    op.add_column('mock_rules', sa.Column('script', sa.Text(), nullable=True, comment='自定义JS脚本'))
    op.add_column('mock_rules', sa.Column('hit_count', sa.Integer(), server_default='0', comment='命中次数统计'))

    # 创建 mock_hit_logs 表
    op.create_table('mock_hit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('mock_rules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('request_method', sa.String(10), nullable=False),
        sa.Column('request_path', sa.String(500), nullable=False),
        sa.Column('request_headers', sa.Text(), nullable=True),
        sa.Column('matched', sa.Boolean(), server_default='1'),
        sa.Column('response_delay_ms', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mock_hit_logs_rule_id', 'mock_hit_logs', ['rule_id'])
    op.create_index('ix_mock_hit_logs_created_at', 'mock_hit_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('mock_hit_logs')
    op.drop_column('mock_rules', 'hit_count')
    op.drop_column('mock_rules', 'script')
    op.drop_column('mock_rules', 'conditions')
