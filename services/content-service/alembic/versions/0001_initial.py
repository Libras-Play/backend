"""Initial migration - complete schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-11-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create languages table
    op.create_table(
        'languages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('flag_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_languages_code'), 'languages', ['code'], unique=True)
    op.create_index(op.f('ix_languages_id'), 'languages', ['id'], unique=False)

    # Create topics table
    op.create_table(
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
    )
    op.create_index(op.f('ix_topics_id'), 'topics', ['id'], unique=False)
    op.create_index(op.f('ix_topics_language_id'), 'topics', ['language_id'], unique=False)
    op.create_index(op.f('ix_topics_order_index'), 'topics', ['order_index'], unique=False)
    op.create_index('ix_topics_language_order', 'topics', ['language_id', 'order_index'], unique=False)

    # Create levels table
    op.create_table(
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
    )
    op.create_index(op.f('ix_levels_id'), 'levels', ['id'], unique=False)
    op.create_index(op.f('ix_levels_topic_id'), 'levels', ['topic_id'], unique=False)
    op.create_index(op.f('ix_levels_order_index'), 'levels', ['order_index'], unique=False)
    op.create_index('ix_levels_topic_order', 'levels', ['topic_id', 'order_index'], unique=False)

    # Create exercises table
    op.create_table(
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
    )
    op.create_index(op.f('ix_exercises_id'), 'exercises', ['id'], unique=False)
    op.create_index(op.f('ix_exercises_level_id'), 'exercises', ['level_id'], unique=False)
    op.create_index(op.f('ix_exercises_order_index'), 'exercises', ['order_index'], unique=False)
    op.create_index(op.f('ix_exercises_type'), 'exercises', ['type'], unique=False)
    op.create_index('ix_exercises_level_order', 'exercises', ['level_id', 'order_index'], unique=False)

    # Create signs table
    op.create_table(
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
    )
    op.create_index(op.f('ix_signs_difficulty'), 'signs', ['difficulty'], unique=False)
    op.create_index(op.f('ix_signs_id'), 'signs', ['id'], unique=False)
    op.create_index(op.f('ix_signs_language_id'), 'signs', ['language_id'], unique=False)
    op.create_index(op.f('ix_signs_word'), 'signs', ['word'], unique=False)
    op.create_index('ix_signs_language_word', 'signs', ['language_id', 'word'], unique=False)

    # Create translations table
    op.create_table(
        'translations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=200), nullable=False),
        sa.Column('language_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['language_id'], ['languages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_translations_id'), 'translations', ['id'], unique=False)
    op.create_index(op.f('ix_translations_key'), 'translations', ['key'], unique=False)
    op.create_index(op.f('ix_translations_language_id'), 'translations', ['language_id'], unique=False)
    op.create_index('ix_translations_key_language', 'translations', ['key', 'language_id'], unique=True)

    # Create achievements table
    op.create_table(
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
    )
    op.create_index(op.f('ix_achievements_code'), 'achievements', ['code'], unique=True)
    op.create_index(op.f('ix_achievements_id'), 'achievements', ['id'], unique=False)


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_index(op.f('ix_achievements_id'), table_name='achievements')
    op.drop_index(op.f('ix_achievements_code'), table_name='achievements')
    op.drop_table('achievements')
    
    op.drop_index('ix_translations_key_language', table_name='translations')
    op.drop_index(op.f('ix_translations_language_id'), table_name='translations')
    op.drop_index(op.f('ix_translations_key'), table_name='translations')
    op.drop_index(op.f('ix_translations_id'), table_name='translations')
    op.drop_table('translations')
    
    op.drop_index('ix_signs_language_word', table_name='signs')
    op.drop_index(op.f('ix_signs_word'), table_name='signs')
    op.drop_index(op.f('ix_signs_language_id'), table_name='signs')
    op.drop_index(op.f('ix_signs_id'), table_name='signs')
    op.drop_index(op.f('ix_signs_difficulty'), table_name='signs')
    op.drop_table('signs')
    
    op.drop_index('ix_exercises_level_order', table_name='exercises')
    op.drop_index(op.f('ix_exercises_type'), table_name='exercises')
    op.drop_index(op.f('ix_exercises_order_index'), table_name='exercises')
    op.drop_index(op.f('ix_exercises_level_id'), table_name='exercises')
    op.drop_index(op.f('ix_exercises_id'), table_name='exercises')
    op.drop_table('exercises')
    
    op.drop_index('ix_levels_topic_order', table_name='levels')
    op.drop_index(op.f('ix_levels_order_index'), table_name='levels')
    op.drop_index(op.f('ix_levels_topic_id'), table_name='levels')
    op.drop_index(op.f('ix_levels_id'), table_name='levels')
    op.drop_table('levels')
    
    op.drop_index('ix_topics_language_order', table_name='topics')
    op.drop_index(op.f('ix_topics_order_index'), table_name='topics')
    op.drop_index(op.f('ix_topics_language_id'), table_name='topics')
    op.drop_index(op.f('ix_topics_id'), table_name='topics')
    op.drop_table('topics')
    
    op.drop_index(op.f('ix_languages_id'), table_name='languages')
    op.drop_index(op.f('ix_languages_code'), table_name='languages')
    op.drop_table('languages')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS conditiontype')
    op.execute('DROP TYPE IF EXISTS exercisetype')
    op.execute('DROP TYPE IF EXISTS difficultylevel')
