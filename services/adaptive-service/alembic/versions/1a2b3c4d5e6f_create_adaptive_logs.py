"""
Create adaptive_logs table for ML training dataset (FULLY IDEMPOTENT)

CRITICAL: IDEMPOTENT MIGRATION
✔ Usa SELECT EXISTS antes de CREATE TABLE
✔ NO romper si tabla ya existe
✔ Indexes también son idempotentes

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2025-11-20 06:15:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from alembic_utils import (
    migration_context, create_table_if_not_exists,
    create_index_if_not_exists, table_exists
)

# revision identifiers, used by Alembic
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create adaptive_logs table if not exists
    
    FULLY IDEMPOTENT MIGRATION:
    ✔ Verificar existencia antes de crear tabla
    ✔ Verificar existencia antes de crear índices
    ✔ Migration completamente idempotente
    """
    
    with migration_context("1a2b3c4d5e6f", "Create adaptive_logs table (idempotent)"):
        
        # Create table only if it doesn't exist
        if create_table_if_not_exists(
            'adaptive_logs',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.String(length=255), nullable=False),
            sa.Column('learning_language', sa.String(length=10), nullable=False),
            sa.Column('exercise_type', sa.String(length=50), nullable=False),
            sa.Column('current_difficulty', sa.Integer, nullable=False),
            sa.Column('next_difficulty', sa.Integer, nullable=False),
            sa.Column('mastery_score', sa.Float, nullable=False),
            sa.Column('time_spent', sa.Float, nullable=True),
            sa.Column('correct', sa.Boolean, nullable=True),
            sa.Column('error_rate', sa.Float, nullable=True),
            sa.Column('consistency_adjustment', sa.Integer, default=0),
            sa.Column('error_adjustment', sa.Integer, default=0),
            sa.Column('speed_adjustment', sa.Integer, default=0),
            sa.Column('model_used', sa.Boolean, default=False),
            sa.Column('model_prediction', sa.Integer, nullable=True),
            sa.Column('timestamp', sa.DateTime, nullable=False),
        ):
            print("✅ Table adaptive_logs created successfully")
        else:
            print("ℹ️ Table adaptive_logs already exists, checking indexes...")
        
        # Create indexes only if they don't exist (idempotent)
        create_index_if_not_exists('ix_adaptive_logs_user_id', 'adaptive_logs', ['user_id'])
        create_index_if_not_exists('ix_adaptive_logs_learning_language', 'adaptive_logs', ['learning_language'])
        create_index_if_not_exists('ix_adaptive_logs_timestamp', 'adaptive_logs', ['timestamp'])
        create_index_if_not_exists('idx_user_lang_time', 'adaptive_logs', 
                                 ['user_id', 'learning_language', 'timestamp'])
        create_index_if_not_exists('idx_model_used', 'adaptive_logs', ['model_used'])
        
        print("✅ All indexes ensured for adaptive_logs")


def downgrade() -> None:
    """Drop adaptive_logs table (idempotent)"""
    from alembic_utils import drop_index_if_exists, table_exists
    
    with migration_context("1a2b3c4d5e6f", "Drop adaptive_logs table (idempotent)"):
        
        if table_exists('adaptive_logs'):
            print("📋 Dropping indexes...")
            drop_index_if_exists('idx_model_used', 'adaptive_logs')
            drop_index_if_exists('idx_user_lang_time', 'adaptive_logs')
            drop_index_if_exists('ix_adaptive_logs_user_id', 'adaptive_logs')
            drop_index_if_exists('ix_adaptive_logs_learning_language', 'adaptive_logs')
            drop_index_if_exists('ix_adaptive_logs_timestamp', 'adaptive_logs')
            
            print("📋 Dropping table...")
            op.drop_table('adaptive_logs')
            print("✅ Table adaptive_logs dropped successfully")
        else:
            print("ℹ️ Table adaptive_logs doesn't exist, skipping drop")
