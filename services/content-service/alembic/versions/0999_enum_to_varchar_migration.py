"""Replace Enum Columns with VARCHAR + CHECK Constraints

Revision ID: 0999_enum_to_varchar_migration
Revises: (latest)
Create Date: 2025-01-27 15:00:00.000000

CHANGES:
- Replace SQLAlchemy Enum columns with VARCHAR + CHECK constraints
- Maintain backward compatibility with existing enum values
- Enable case-insensitive API operations
- Preserve referential integrity and data validation

ENUM COLUMNS TO CONVERT:
1. exercises.difficulty (difficultylevel enum)
2. exercises.exercise_type (exercisetype enum)  
3. exercise_base.difficulty (difficultylevel enum)
4. achievements.condition_type (conditiontype enum)
5. exercise_attempts.outcome (string with check constraint)

BENEFITS:
- API can accept case-insensitive values ("EASY" or "easy")
- No enum serialization issues in API responses
- Easier to add new values without migrations
- Better compatibility with different database drivers
"""
from alembic import op
import sqlalchemy as sa
from alembic_utils import (
    migration_context, column_exists, constraint_exists,
    create_constraint_if_not_exists, drop_constraint_if_exists,
    enum_exists, drop_enum_if_exists
)

# revision identifiers, used by Alembic.
revision = '0999_enum_to_varchar_migration'
down_revision = None  # Set this to the latest revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert enum columns to VARCHAR with CHECK constraints"""
    
    with migration_context("0999_enum_to_varchar_migration", "Convert enums to VARCHAR + CHECK"):
        
        # ================================================================
        # STEP 1: Add new VARCHAR columns alongside existing enum columns
        # ================================================================
        print("📋 STEP 1: Adding new VARCHAR columns...")
        
        # Add new VARCHAR columns for exercises table
        if not column_exists('exercises', 'difficulty_varchar'):
            op.add_column('exercises', sa.Column('difficulty_varchar', sa.String(20), nullable=True))
            print("   ✅ Added exercises.difficulty_varchar")
        
        if not column_exists('exercises', 'exercise_type_varchar'):
            op.add_column('exercises', sa.Column('exercise_type_varchar', sa.String(20), nullable=True))
            print("   ✅ Added exercises.exercise_type_varchar")
        
        # Add new VARCHAR columns for exercise_base table (if it exists)
        if column_exists('exercise_base', 'difficulty'):
            if not column_exists('exercise_base', 'difficulty_varchar'):
                op.add_column('exercise_base', sa.Column('difficulty_varchar', sa.String(20), nullable=True))
                print("   ✅ Added exercise_base.difficulty_varchar")
        
        # Add new VARCHAR column for achievements table
        if not column_exists('achievements', 'condition_type_varchar'):
            op.add_column('achievements', sa.Column('condition_type_varchar', sa.String(30), nullable=True))
            print("   ✅ Added achievements.condition_type_varchar")
        
        print("✅ STEP 1 COMPLETED: New VARCHAR columns added\n")
        
        # ================================================================
        # STEP 2: Migrate data from enum columns to VARCHAR columns
        # ================================================================
        print("📋 STEP 2: Migrating enum data to VARCHAR columns...")
        
        # Migrate exercises.difficulty
        op.execute("""
            UPDATE exercises 
            SET difficulty_varchar = CASE 
                WHEN difficulty::text = 'BEGINNER' THEN 'easy'
                WHEN difficulty::text = 'INTERMEDIATE' THEN 'medium'
                WHEN difficulty::text = 'ADVANCED' THEN 'hard'
                ELSE LOWER(difficulty::text)
            END
            WHERE difficulty_varchar IS NULL
        """)
        print("   ✅ Migrated exercises.difficulty data")
        
        # Migrate exercises.exercise_type
        op.execute("""
            UPDATE exercises 
            SET exercise_type_varchar = LOWER(exercise_type::text)
            WHERE exercise_type_varchar IS NULL
        """)
        print("   ✅ Migrated exercises.exercise_type data")
        
        # Migrate exercise_base.difficulty (if table exists)
        try:
            op.execute("""
                UPDATE exercise_base 
                SET difficulty_varchar = CASE 
                    WHEN difficulty::text = 'BEGINNER' THEN 'easy'
                    WHEN difficulty::text = 'INTERMEDIATE' THEN 'medium'
                    WHEN difficulty::text = 'ADVANCED' THEN 'hard'
                    ELSE LOWER(difficulty::text)
                END
                WHERE difficulty_varchar IS NULL
            """)
            print("   ✅ Migrated exercise_base.difficulty data")
        except Exception as e:
            print(f"   ℹ️ exercise_base table not found or already migrated: {e}")
        
        # Migrate achievements.condition_type
        op.execute("""
            UPDATE achievements 
            SET condition_type_varchar = LOWER(condition_type::text)
            WHERE condition_type_varchar IS NULL
        """)
        print("   ✅ Migrated achievements.condition_type data")
        
        print("✅ STEP 2 COMPLETED: Data migration finished\n")
        
        # ================================================================
        # STEP 3: Drop old enum columns and rename VARCHAR columns
        # ================================================================
        print("📋 STEP 3: Replacing enum columns with VARCHAR columns...")
        
        # Drop foreign key constraints first (if any)
        try:
            drop_constraint_if_exists('exercises_difficulty_fkey', 'exercises', 'foreignkey')
            drop_constraint_if_exists('exercises_exercise_type_fkey', 'exercises', 'foreignkey')
            drop_constraint_if_exists('achievements_condition_type_fkey', 'achievements', 'foreignkey')
        except Exception as e:
            print(f"   ℹ️ No foreign key constraints to drop: {e}")
        
        # Drop and recreate exercises columns
        op.drop_column('exercises', 'difficulty')
        op.alter_column('exercises', 'difficulty_varchar', new_column_name='difficulty')
        print("   ✅ Replaced exercises.difficulty with VARCHAR")
        
        op.drop_column('exercises', 'exercise_type')
        op.alter_column('exercises', 'exercise_type_varchar', new_column_name='exercise_type')
        print("   ✅ Replaced exercises.exercise_type with VARCHAR")
        
        # Drop and recreate exercise_base columns (if table exists)
        try:
            if column_exists('exercise_base', 'difficulty'):
                op.drop_column('exercise_base', 'difficulty')
                op.alter_column('exercise_base', 'difficulty_varchar', new_column_name='difficulty')
                print("   ✅ Replaced exercise_base.difficulty with VARCHAR")
        except Exception as e:
            print(f"   ℹ️ exercise_base.difficulty not found: {e}")
        
        # Drop and recreate achievements columns
        op.drop_column('achievements', 'condition_type')
        op.alter_column('achievements', 'condition_type_varchar', new_column_name='condition_type')
        print("   ✅ Replaced achievements.condition_type with VARCHAR")
        
        print("✅ STEP 3 COMPLETED: Enum columns replaced\n")
        
        # ================================================================
        # STEP 4: Add CHECK constraints for data validation
        # ================================================================
        print("📋 STEP 4: Adding CHECK constraints...")
        
        # Add CHECK constraint for exercises.difficulty
        create_constraint_if_not_exists(
            'check_exercises_difficulty_valid',
            'exercises',
            'check',
            sa.text("difficulty IN ('easy', 'medium', 'hard')")
        )
        
        # Add CHECK constraint for exercises.exercise_type
        create_constraint_if_not_exists(
            'check_exercises_exercise_type_valid',
            'exercises',
            'check',
            sa.text("exercise_type IN ('test', 'camera')")
        )
        
        # Add CHECK constraint for exercise_base.difficulty (if table exists)
        if column_exists('exercise_base', 'difficulty'):
            create_constraint_if_not_exists(
                'check_exercise_base_difficulty_valid',
                'exercise_base',
                'check',
                sa.text("difficulty IN ('easy', 'medium', 'hard')")
            )
        
        # Add CHECK constraint for achievements.condition_type
        create_constraint_if_not_exists(
            'check_achievements_condition_type_valid',
            'achievements',
            'check',
            sa.text("""condition_type IN (
                'exercises_completed', 'levels_completed', 'xp_earned',
                'streak_days', 'perfect_levels'
            )""")
        )
        
        # Ensure exercise_attempts.outcome has proper CHECK constraint
        create_constraint_if_not_exists(
            'check_exercise_attempts_outcome_valid',
            'exercise_attempts',
            'check',
            sa.text("outcome IN ('correct', 'incorrect', 'skipped')")
        )
        
        print("   ✅ Added all CHECK constraints")
        print("✅ STEP 4 COMPLETED: Data validation ensured\n")
        
        # ================================================================
        # STEP 5: Add NOT NULL constraints and indexes
        # ================================================================
        print("📋 STEP 5: Adding NOT NULL constraints and indexes...")
        
        # Make new columns NOT NULL
        op.alter_column('exercises', 'difficulty', nullable=False)
        op.alter_column('exercises', 'exercise_type', nullable=False)
        op.alter_column('achievements', 'condition_type', nullable=False)
        
        if column_exists('exercise_base', 'difficulty'):
            op.alter_column('exercise_base', 'difficulty', nullable=False)
        
        # Recreate indexes on new VARCHAR columns
        if not constraint_exists('ix_exercises_difficulty', 'exercises'):
            op.create_index('ix_exercises_difficulty', 'exercises', ['difficulty'])
        
        if not constraint_exists('ix_exercises_exercise_type', 'exercises'):
            op.create_index('ix_exercises_exercise_type', 'exercises', ['exercise_type'])
        
        if column_exists('exercise_base', 'difficulty'):
            if not constraint_exists('ix_exercise_base_difficulty', 'exercise_base'):
                op.create_index('ix_exercise_base_difficulty', 'exercise_base', ['difficulty'])
        
        print("   ✅ Added NOT NULL constraints and indexes")
        print("✅ STEP 5 COMPLETED: Constraints and indexes restored\n")
        
        # ================================================================
        # STEP 6: Clean up old enum types
        # ================================================================
        print("📋 STEP 6: Cleaning up old enum types...")
        
        # Drop old enum types (if they exist and are not referenced)
        enum_types = ['difficultylevel', 'exercisetype', 'conditiontype']
        
        for enum_type in enum_types:
            try:
                if enum_exists(enum_type):
                    drop_enum_if_exists(enum_type)
                    print(f"   ✅ Dropped enum type: {enum_type}")
            except Exception as e:
                print(f"   ⚠️ Could not drop enum {enum_type}: {e}")
        
        print("✅ STEP 6 COMPLETED: Enum cleanup finished\n")


def downgrade() -> None:
    """
    Revert VARCHAR columns back to enums
    
    WARNING: This is a complex downgrade that may lose data precision.
    Only use in development environments.
    """
    
    with migration_context("0999_enum_to_varchar_migration", "Revert VARCHAR to enums (DESTRUCTIVE)"):
        
        print("⚠️ WARNING: This downgrade is destructive and may lose data!")
        
        # ================================================================
        # STEP 1: Recreate enum types
        # ================================================================
        print("📋 STEP 1: Recreating enum types...")
        
        # Recreate enum types
        op.execute("CREATE TYPE difficultylevel AS ENUM ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')")
        op.execute("CREATE TYPE exercisetype AS ENUM ('TEST', 'GESTURE')")  
        op.execute("CREATE TYPE conditiontype AS ENUM ('EXERCISES_COMPLETED', 'LEVELS_COMPLETED', 'XP_EARNED', 'STREAK_DAYS', 'PERFECT_LEVELS')")
        
        print("   ✅ Recreated enum types")
        
        # ================================================================
        # STEP 2: Add temporary enum columns
        # ================================================================
        print("📋 STEP 2: Adding temporary enum columns...")
        
        op.add_column('exercises', sa.Column('difficulty_enum', sa.Enum('BEGINNER', 'INTERMEDIATE', 'ADVANCED', name='difficultylevel'), nullable=True))
        op.add_column('exercises', sa.Column('exercise_type_enum', sa.Enum('TEST', 'GESTURE', name='exercisetype'), nullable=True))
        op.add_column('achievements', sa.Column('condition_type_enum', sa.Enum('EXERCISES_COMPLETED', 'LEVELS_COMPLETED', 'XP_EARNED', 'STREAK_DAYS', 'PERFECT_LEVELS', name='conditiontype'), nullable=True))
        
        print("   ✅ Added temporary enum columns")
        
        # ================================================================
        # STEP 3: Migrate data back to enums
        # ================================================================
        print("📋 STEP 3: Migrating VARCHAR data back to enums...")
        
        # Map new values back to old enum values
        op.execute("""
            UPDATE exercises 
            SET difficulty_enum = CASE 
                WHEN difficulty = 'easy' THEN 'BEGINNER'::difficultylevel
                WHEN difficulty = 'medium' THEN 'INTERMEDIATE'::difficultylevel
                WHEN difficulty = 'hard' THEN 'ADVANCED'::difficultylevel
                ELSE 'BEGINNER'::difficultylevel
            END
        """)
        
        op.execute("""
            UPDATE exercises 
            SET exercise_type_enum = CASE 
                WHEN exercise_type = 'test' THEN 'TEST'::exercisetype
                WHEN exercise_type = 'camera' THEN 'GESTURE'::exercisetype
                ELSE 'TEST'::exercisetype
            END
        """)
        
        op.execute("""
            UPDATE achievements 
            SET condition_type_enum = UPPER(condition_type)::conditiontype
        """)
        
        print("   ✅ Migrated data back to enums")
        
        # ================================================================
        # STEP 4: Replace VARCHAR columns with enum columns
        # ================================================================
        print("📋 STEP 4: Replacing VARCHAR columns with enum columns...")
        
        # Drop CHECK constraints
        drop_constraint_if_exists('check_exercises_difficulty_valid', 'exercises', 'check')
        drop_constraint_if_exists('check_exercises_exercise_type_valid', 'exercises', 'check')
        drop_constraint_if_exists('check_achievements_condition_type_valid', 'achievements', 'check')
        
        # Replace columns
        op.drop_column('exercises', 'difficulty')
        op.alter_column('exercises', 'difficulty_enum', new_column_name='difficulty')
        
        op.drop_column('exercises', 'exercise_type')
        op.alter_column('exercises', 'exercise_type_enum', new_column_name='exercise_type')
        
        op.drop_column('achievements', 'condition_type')
        op.alter_column('achievements', 'condition_type_enum', new_column_name='condition_type')
        
        # Make columns NOT NULL
        op.alter_column('exercises', 'difficulty', nullable=False)
        op.alter_column('exercises', 'exercise_type', nullable=False)
        op.alter_column('achievements', 'condition_type', nullable=False)
        
        print("   ✅ Replaced VARCHAR columns with enum columns")
        print("✅ DOWNGRADE COMPLETED: Reverted to enum columns")