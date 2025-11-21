"""create_badges_master_table

Revision ID: 2ffca5094771
Revises: 9f8e7d6c5b4a
Create Date: 2025-11-20 02:24:47.312107

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2ffca5094771'
down_revision = '9f8e7d6c5b4a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create badges_master table - NO ENUMS to avoid serialization issues
    # Use raw SQL to add IF NOT EXISTS
    from sqlalchemy import text
    
    conn = op.get_bind()
    
    # Check if table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'badges_master'
        );
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        op.create_table(
            'badges_master',
            sa.Column('badge_id', sa.String(36), primary_key=True),
            sa.Column('type', sa.String(30), nullable=False, comment='Badge type: milestone, achievement, streak, skill'),
            sa.Column('title', sa.JSON, nullable=False, comment='Multilang title: {es, en, pt}'),
            sa.Column('description', sa.JSON, nullable=False, comment='Multilang description'),
            sa.Column('icon_url', sa.Text, nullable=False),
            sa.Column('conditions', sa.JSON, nullable=False, comment='Conditions to earn badge: {metric, value, operator}'),
            sa.Column('learning_language', sa.String(10), nullable=False, comment='LSB, ASL, LSM'),
            sa.Column('is_hidden', sa.Boolean, default=False, comment='Hidden until earned'),
            sa.Column('rarity', sa.String(20), nullable=False, default='common', comment='common, rare, epic, legendary'),
            sa.Column('order_index', sa.Integer, default=0),
            sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        )
        
        # Create indexes for filtering - NO array operations
        op.create_index('idx_badges_learning_language', 'badges_master', ['learning_language'])
        op.create_index('idx_badges_type', 'badges_master', ['type'])
        op.create_index('idx_badges_rarity', 'badges_master', ['rarity'])


def downgrade() -> None:
    op.drop_index('idx_badges_rarity', 'badges_master')
    op.drop_index('idx_badges_type', 'badges_master')
    op.drop_index('idx_badges_learning_language', 'badges_master')
    op.drop_table('badges_master')
