"""Initial migration - complete schema (IDEMPOTENT VERSION)

Revision ID: 0001_initial_idempotent
Revises: 0001_initial
Create Date: 2025-01-27 12:00:00.000000

This is an idempotent replacement for the original 0001_initial migration.
It can be safely run multiple times without errors.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic_utils import (
    migration_context, create_table_if_not_exists, 
    create_index_if_not_exists, create_enum_if_not_exists,
    table_exists, enum_exists
)

# revision identifiers, used by Alembic.
revision = '0001_initial_idempotent'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema with full idempotency"""
    
    with migration_context("0001_initial_idempotent", "Create initial schema (idempotent)"):
        
        # ================================================================
        # STEP 1: Create enums if they don't exist
        # ================================================================
        print("📋 STEP 1: Creating enum types...")
        
        create_enum_if_not_exists('difficultylevel', ['BEGINNER', 'INTERMEDIATE', 'ADVANCED'])
        create_enum_if_not_exists('exercisetype', ['TEST', 'GESTURE'])
        create_enum_if_not_exists('conditiontype', [
            'EXERCISES_COMPLETED', 'LEVELS_COMPLETED', 'XP_EARNED', 
            'STREAK_DAYS', 'PERFECT_LEVELS'
        ])
        
        print("✅ STEP 1 COMPLETED: Enums created\n")
        
        # ================================================================
        # STEP 2: Create tables if they don't exist
        # ================================================================
        print("📋 STEP 2: Creating tables...")
        
        # Create languages table
        if create_table_if_not_exists(
            'languages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=10), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('flag_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        ):
            # Create indexes only if table was created
            create_index_if_not_exists('ix_languages_code', 'languages', ['code'], unique=True)
            create_index_if_not_exists('ix_languages_id', 'languages', ['id'])
        
        # Create topics table
        if create_table_if_not_exists(
            'topics',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('language_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True),
            sa.Column('icon_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['language_id'], ['languages.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        ):
            # Create indexes only if table was created
            create_index_if_not_exists('ix_topics_id', 'topics', ['id'])
            create_index_if_not_exists('ix_topics_language_id', 'topics', ['language_id'])
            create_index_if_not_exists('ix_topics_order_index', 'topics', ['order_index'])
            create_index_if_not_exists('ix_topics_language_order', 'topics', ['language_id', 'order_index'])
        
        # Create levels table
        if create_table_if_not_exists(
            'levels',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('topic_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('difficulty', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED', name='difficultylevel'), nullable=False),
            sa.Column('order_index', sa.Integer(), nullable=True),
            sa.Column('xp_reward', sa.Integer(), nullable=False),
            sa.Column('unlocks_next', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        ):
            # Create indexes only if table was created
            create_index_if_not_exists('ix_levels_id', 'levels', ['id'])
            create_index_if_not_exists('ix_levels_topic_id', 'levels', ['topic_id'])
            create_index_if_not_exists('ix_levels_order_index', 'levels', ['order_index'])
            create_index_if_not_exists('ix_levels_topic_order', 'levels', ['topic_id', 'order_index'])
        
        # Create exercises table
        if create_table_if_not_exists(
            'exercises',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('level_id', sa.Integer(), nullable=False),
            sa.Column('type', sa.Enum('TEST', 'GESTURE', name='exercisetype'), nullable=False),
            sa.Column('question_text', sa.Text(), nullable=True),
            sa.Column('correct_answer', sa.String(length=200), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('options', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('gesture_label', sa.String(length=100), nullable=True),
            sa.Column('order_index', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['level_id'], ['levels.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        ):
            # Create indexes only if table was created
            create_index_if_not_exists('ix_exercises_id', 'exercises', ['id'])
            create_index_if_not_exists('ix_exercises_level_id', 'exercises', ['level_id'])
            create_index_if_not_exists('ix_exercises_order_index', 'exercises', ['order_index'])
            create_index_if_not_exists('ix_exercises_type', 'exercises', ['type'])
            create_index_if_not_exists('ix_exercises_level_order', 'exercises', ['level_id', 'order_index'])
        
        # Create signs table
        if create_table_if_not_exists(
            'signs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('language_id', sa.Integer(), nullable=False),
            sa.Column('word', sa.String(length=200), nullable=False),
            sa.Column('video_url', sa.String(length=500), nullable=True),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('difficulty', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED', name='difficultylevel'), nullable=False),
            sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['language_id'], ['languages.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        ):
            # Create indexes only if table was created
            create_index_if_not_exists('ix_signs_difficulty', 'signs', ['difficulty'])
            create_index_if_not_exists('ix_signs_id', 'signs', ['id'])
            create_index_if_not_exists('ix_signs_language_id', 'signs', ['language_id'])
            create_index_if_not_exists('ix_signs_word', 'signs', ['word'])
            create_index_if_not_exists('ix_signs_language_word', 'signs', ['language_id', 'word'])
        
        # Create translations table
        if create_table_if_not_exists(
            'translations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('key', sa.String(length=200), nullable=False),
            sa.Column('language_id', sa.Integer(), nullable=False),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['language_id'], ['languages.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        ):
            # Create indexes only if table was created
            create_index_if_not_exists('ix_translations_id', 'translations', ['id'])
            create_index_if_not_exists('ix_translations_key', 'translations', ['key'])
            create_index_if_not_exists('ix_translations_language_id', 'translations', ['language_id'])
            create_index_if_not_exists('ix_translations_key_language', 'translations', ['key', 'language_id'], unique=True)
        
        # Create achievements table
        if create_table_if_not_exists(
            'achievements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('code', sa.String(length=50), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('condition_type', sa.Enum('EXERCISES_COMPLETED', 'LEVELS_COMPLETED', 'XP_EARNED', 'STREAK_DAYS', 'PERFECT_LEVELS', name='conditiontype'), nullable=False),
            sa.Column('condition_value', sa.Integer(), nullable=False),
            sa.Column('reward', sa.Integer(), nullable=False),
            sa.Column('icon_url', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        ):
            # Create indexes only if table was created
            create_index_if_not_exists('ix_achievements_code', 'achievements', ['code'], unique=True)
            create_index_if_not_exists('ix_achievements_id', 'achievements', ['id'])
        
        print("✅ STEP 2 COMPLETED: All tables created\n")


def downgrade() -> None:
    """
    Idempotent downgrade - drop all tables and enums if they exist
    """
    with migration_context("0001_initial_idempotent", "Drop initial schema (idempotent)"):
        
        # Drop tables in reverse order if they exist
        tables_to_drop = [
            'achievements', 'translations', 'signs', 'exercises', 
            'levels', 'topics', 'languages'
        ]
        
        print("📋 Dropping tables...")
        for table_name in tables_to_drop:
            if table_exists(table_name):
                op.drop_table(table_name)
                print(f"✅ Dropped table: {table_name}")
            else:
                print(f"ℹ️ Table {table_name} doesn't exist, skipping")
        
        # Drop enums if they exist
        enums_to_drop = ['conditiontype', 'exercisetype', 'difficultylevel']
        
        print("📋 Dropping enum types...")
        for enum_name in enums_to_drop:
            if enum_exists(enum_name):
                op.execute(f'DROP TYPE IF EXISTS {enum_name} CASCADE')
                print(f"✅ Dropped enum: {enum_name}")
            else:
                print(f"ℹ️ Enum {enum_name} doesn't exist, skipping")