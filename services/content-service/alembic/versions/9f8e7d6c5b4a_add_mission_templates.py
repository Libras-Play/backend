"""add mission_templates table

Revision ID: add_mission_templates
Revises: add_video_url_to_exercises
Create Date: 2025-11-19 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9f8e7d6c5b4a'
down_revision: Union[str, None] = 'c95390a6a4e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum for metric_type
    metric_type_enum = postgresql.ENUM(
        'exercises_completed',
        'camera_minutes',
        'xp_earned',
        'topic_completed',
        'practice_seconds',
        name='metric_type_enum',
        create_type=True
    )
    metric_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create mission_templates table
    op.create_table(
        'mission_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('title', postgresql.JSONB(), nullable=False),
        sa.Column('description', postgresql.JSONB(), nullable=False),
        sa.Column('learning_languages', postgresql.ARRAY(sa.String(10)), nullable=False, server_default='{}'),
        sa.Column('metric_type', metric_type_enum, nullable=False),
        sa.Column('metric_value', sa.Integer(), nullable=False),
        sa.Column('difficulty', sa.String(20), nullable=True),  # 'easy', 'medium', 'hard', null = all
        sa.Column('reward_coins', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reward_xp', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reward_gems', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint('metric_value > 0', name='positive_metric_value'),
        sa.CheckConstraint('reward_coins >= 0', name='positive_reward_coins'),
        sa.CheckConstraint('reward_xp >= 0', name='positive_reward_xp'),
        sa.CheckConstraint('reward_gems >= 0', name='positive_reward_gems'),
        sa.CheckConstraint('priority >= 0', name='positive_priority'),
    )
    
    # Create index for active missions query
    op.create_index(
        'idx_mission_templates_active_priority',
        'mission_templates',
        ['active', 'priority'],
        postgresql_where=sa.text('active = true')
    )
    
    # Create index for learning language filtering (GIN index for array)
    op.execute(
        'CREATE INDEX idx_mission_templates_languages '
        'ON mission_templates USING GIN (learning_languages)'
    )


def downgrade() -> None:
    op.drop_index('idx_mission_templates_languages', table_name='mission_templates')
    op.drop_index('idx_mission_templates_active_priority', table_name='mission_templates')
    op.drop_table('mission_templates')
    
    # Drop enum
    metric_type_enum = postgresql.ENUM(
        'exercises_completed',
        'camera_minutes',
        'xp_earned',
        'topic_completed',
        'practice_seconds',
        name='metric_type_enum'
    )
    metric_type_enum.drop(op.get_bind(), checkfirst=True)
