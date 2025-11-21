"""add user exercise performance table

Revision ID: fase8_performance
Revises: 9f8e7d6c5b4a
Create Date: 2025-11-20 22:00:00.000000

FASE 8: Tabla para tracking de desempeño por usuario-ejercicio
MIGRACIÓN IDEMPOTENTE - usa IF NOT EXISTS
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'fase8_performance'
down_revision = '9f8e7d6c5b4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Crea tabla user_exercise_performance de forma IDEMPOTENTE.
    
    EVITA ERROR P: Usa CREATE TABLE IF NOT EXISTS
    """
    # Check if table exists first (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'user_exercise_performance' not in inspector.get_table_names():
        op.create_table(
            'user_exercise_performance',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.String(length=100), nullable=False),
            sa.Column('exercise_id', sa.Integer(), nullable=False),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('errors', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_result', sa.String(length=20), nullable=True),  # 'success' | 'fail'
            sa.Column('avg_response_time', sa.Float(), nullable=True),  # seconds
            sa.Column('last_timestamp', sa.DateTime(), nullable=True),
            sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.5'),  # 0.0 - 1.0
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='CASCADE'),
            sa.CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='check_confidence_range'),
            sa.CheckConstraint('attempts >= 0', name='check_attempts_positive'),
            sa.CheckConstraint('errors >= 0', name='check_errors_positive'),
        )
        
        # Indexes for fast queries
        op.create_index(
            'ix_user_exercise_performance_user_id',
            'user_exercise_performance',
            ['user_id']
        )
        op.create_index(
            'ix_user_exercise_performance_exercise_id',
            'user_exercise_performance',
            ['exercise_id']
        )
        op.create_index(
            'ix_user_exercise_performance_user_exercise',
            'user_exercise_performance',
            ['user_id', 'exercise_id'],
            unique=True
        )
        op.create_index(
            'ix_user_exercise_performance_confidence',
            'user_exercise_performance',
            ['confidence_score']
        )


def downgrade() -> None:
    """
    Elimina tabla user_exercise_performance de forma IDEMPOTENTE.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'user_exercise_performance' in inspector.get_table_names():
        op.drop_table('user_exercise_performance')
