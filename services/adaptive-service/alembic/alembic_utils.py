"""
Alembic Migration Idempotency Utilities

This module provides utilities for creating idempotent Alembic migrations
that can be safely run multiple times without errors.

Usage in migration files:
    from alembic_utils import (
        table_exists, column_exists, index_exists, constraint_exists,
        create_table_if_not_exists, add_column_if_not_exists,
        create_index_if_not_exists, create_constraint_if_not_exists
    )
"""
from alembic import op
from sqlalchemy import text, MetaData, inspect
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_connection():
    """Get current Alembic database connection"""
    return op.get_bind()


def table_exists(table_name: str, schema: str = 'public') -> bool:
    """
    Check if table exists in database
    
    Args:
        table_name: Name of the table to check
        schema: Schema name (default: 'public')
        
    Returns:
        bool: True if table exists, False otherwise
    """
    conn = get_connection()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = '{schema}' 
            AND table_name = '{table_name}'
        )
    """))
    return result.scalar()


def column_exists(table_name: str, column_name: str, schema: str = 'public') -> bool:
    """
    Check if column exists in table
    
    Args:
        table_name: Name of the table
        column_name: Name of the column to check
        schema: Schema name (default: 'public')
        
    Returns:
        bool: True if column exists, False otherwise
    """
    conn = get_connection()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = '{schema}'
            AND table_name = '{table_name}' 
            AND column_name = '{column_name}'
        )
    """))
    return result.scalar()


def index_exists(index_name: str, table_name: Optional[str] = None) -> bool:
    """
    Check if index exists
    
    Args:
        index_name: Name of the index to check
        table_name: Optional table name for additional validation
        
    Returns:
        bool: True if index exists, False otherwise
    """
    conn = get_connection()
    
    if table_name:
        result = conn.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE indexname = '{index_name}'
                AND tablename = '{table_name}'
            )
        """))
    else:
        result = conn.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE indexname = '{index_name}'
            )
        """))
    return result.scalar()


def constraint_exists(constraint_name: str, table_name: str) -> bool:
    """
    Check if constraint exists on table
    
    Args:
        constraint_name: Name of the constraint
        table_name: Name of the table
        
    Returns:
        bool: True if constraint exists, False otherwise
    """
    conn = get_connection()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.table_constraints 
            WHERE constraint_name = '{constraint_name}'
            AND table_name = '{table_name}'
        )
    """))
    return result.scalar()


def enum_exists(enum_name: str) -> bool:
    """
    Check if PostgreSQL enum type exists
    
    Args:
        enum_name: Name of the enum type
        
    Returns:
        bool: True if enum exists, False otherwise
    """
    conn = get_connection()
    result = conn.execute(text(f"""
        SELECT EXISTS (
            SELECT FROM pg_type 
            WHERE typname = '{enum_name}'
            AND typtype = 'e'
        )
    """))
    return result.scalar()


def create_table_if_not_exists(table_name: str, *args, **kwargs) -> bool:
    """
    Create table only if it doesn't exist
    
    Args:
        table_name: Name of the table to create
        *args: Arguments to pass to op.create_table()
        **kwargs: Keyword arguments to pass to op.create_table()
        
    Returns:
        bool: True if table was created, False if it already existed
    """
    if not table_exists(table_name):
        op.create_table(table_name, *args, **kwargs)
        logger.info(f"✅ Created table: {table_name}")
        return True
    else:
        logger.info(f"ℹ️ Table {table_name} already exists, skipping creation")
        return False


def add_column_if_not_exists(table_name: str, column) -> bool:
    """
    Add column to table only if it doesn't exist
    
    Args:
        table_name: Name of the table
        column: SQLAlchemy Column object
        
    Returns:
        bool: True if column was added, False if it already existed
    """
    column_name = column.name
    
    if not column_exists(table_name, column_name):
        op.add_column(table_name, column)
        logger.info(f"✅ Added column {column_name} to {table_name}")
        return True
    else:
        logger.info(f"ℹ️ Column {table_name}.{column_name} already exists, skipping")
        return False


def drop_column_if_exists(table_name: str, column_name: str) -> bool:
    """
    Drop column from table only if it exists
    
    Args:
        table_name: Name of the table
        column_name: Name of the column to drop
        
    Returns:
        bool: True if column was dropped, False if it didn't exist
    """
    if column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)
        logger.info(f"✅ Dropped column {column_name} from {table_name}")
        return True
    else:
        logger.info(f"ℹ️ Column {table_name}.{column_name} doesn't exist, skipping drop")
        return False


def create_index_if_not_exists(index_name: str, table_name: str, columns: List[str], 
                             unique: bool = False, **kwargs) -> bool:
    """
    Create index only if it doesn't exist
    
    Args:
        index_name: Name of the index
        table_name: Name of the table
        columns: List of column names
        unique: Whether index should be unique
        **kwargs: Additional arguments for op.create_index()
        
    Returns:
        bool: True if index was created, False if it already existed
    """
    if not index_exists(index_name, table_name):
        op.create_index(index_name, table_name, columns, unique=unique, **kwargs)
        logger.info(f"✅ Created index: {index_name} on {table_name}({', '.join(columns)})")
        return True
    else:
        logger.info(f"ℹ️ Index {index_name} already exists, skipping creation")
        return False


def drop_index_if_exists(index_name: str, table_name: Optional[str] = None) -> bool:
    """
    Drop index only if it exists
    
    Args:
        index_name: Name of the index to drop
        table_name: Optional table name
        
    Returns:
        bool: True if index was dropped, False if it didn't exist
    """
    if index_exists(index_name, table_name):
        op.drop_index(index_name, table_name=table_name)
        logger.info(f"✅ Dropped index: {index_name}")
        return True
    else:
        logger.info(f"ℹ️ Index {index_name} doesn't exist, skipping drop")
        return False


def create_constraint_if_not_exists(constraint_name: str, table_name: str, 
                                   constraint_type: str, *args, **kwargs) -> bool:
    """
    Create constraint only if it doesn't exist
    
    Args:
        constraint_name: Name of the constraint
        table_name: Name of the table
        constraint_type: Type of constraint ('foreignkey', 'primary', 'unique', 'check')
        *args: Arguments for constraint creation
        **kwargs: Keyword arguments for constraint creation
        
    Returns:
        bool: True if constraint was created, False if it already existed
    """
    if not constraint_exists(constraint_name, table_name):
        if constraint_type == 'foreignkey':
            op.create_foreign_key(constraint_name, table_name, *args, **kwargs)
        elif constraint_type == 'unique':
            op.create_unique_constraint(constraint_name, table_name, *args, **kwargs)
        elif constraint_type == 'check':
            op.create_check_constraint(constraint_name, table_name, *args, **kwargs)
        elif constraint_type == 'primary':
            op.create_primary_key(constraint_name, table_name, *args, **kwargs)
        else:
            raise ValueError(f"Unknown constraint type: {constraint_type}")
            
        logger.info(f"✅ Created {constraint_type} constraint: {constraint_name}")
        return True
    else:
        logger.info(f"ℹ️ Constraint {constraint_name} already exists, skipping creation")
        return False


def drop_constraint_if_exists(constraint_name: str, table_name: str, 
                             constraint_type: str = 'foreignkey') -> bool:
    """
    Drop constraint only if it exists
    
    Args:
        constraint_name: Name of the constraint to drop
        table_name: Name of the table
        constraint_type: Type of constraint to drop
        
    Returns:
        bool: True if constraint was dropped, False if it didn't exist
    """
    if constraint_exists(constraint_name, table_name):
        op.drop_constraint(constraint_name, table_name, type_=constraint_type)
        logger.info(f"✅ Dropped constraint: {constraint_name}")
        return True
    else:
        logger.info(f"ℹ️ Constraint {constraint_name} doesn't exist, skipping drop")
        return False


def create_enum_if_not_exists(enum_name: str, values: List[str]) -> bool:
    """
    Create PostgreSQL enum type only if it doesn't exist
    
    Args:
        enum_name: Name of the enum type
        values: List of enum values
        
    Returns:
        bool: True if enum was created, False if it already existed
    """
    if not enum_exists(enum_name):
        values_str = "', '".join(values)
        conn = get_connection()
        conn.execute(text(f"CREATE TYPE {enum_name} AS ENUM ('{values_str}')"))
        logger.info(f"✅ Created enum: {enum_name} with values: {values}")
        return True
    else:
        logger.info(f"ℹ️ Enum {enum_name} already exists, skipping creation")
        return False


def drop_enum_if_exists(enum_name: str) -> bool:
    """
    Drop PostgreSQL enum type only if it exists
    
    Args:
        enum_name: Name of the enum type to drop
        
    Returns:
        bool: True if enum was dropped, False if it didn't exist
    """
    if enum_exists(enum_name):
        conn = get_connection()
        conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
        logger.info(f"✅ Dropped enum: {enum_name}")
        return True
    else:
        logger.info(f"ℹ️ Enum {enum_name} doesn't exist, skipping drop")
        return False


def safe_execute(sql: str, description: str = "SQL operation") -> bool:
    """
    Safely execute SQL with error handling and logging
    
    Args:
        sql: SQL statement to execute
        description: Description of the operation for logging
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        conn = get_connection()
        conn.execute(text(sql))
        logger.info(f"✅ {description} completed successfully")
        return True
    except Exception as e:
        logger.warning(f"⚠️ {description} failed: {e}")
        return False


def migration_context(migration_name: str, description: str = ""):
    """
    Context manager for migration logging
    
    Args:
        migration_name: Name of the migration
        description: Optional description
        
    Usage:
        with migration_context("0001_initial", "Create initial schema"):
            # migration operations
    """
    class MigrationContext:
        def __enter__(self):
            print(f"\n{'='*70}")
            print(f"🚀 STARTING MIGRATION: {migration_name}")
            if description:
                print(f"📝 Description: {description}")
            print(f"{'='*70}\n")
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                print(f"\n{'='*70}")
                print(f"✅ MIGRATION COMPLETED: {migration_name}")
                print(f"{'='*70}\n")
            else:
                print(f"\n{'='*70}")
                print(f"❌ MIGRATION FAILED: {migration_name}")
                print(f"Error: {exc_val}")
                print(f"{'='*70}\n")
            return False
            
    return MigrationContext()


# Validation utilities
def validate_migration_idempotency(migration_file: str) -> Dict[str, Any]:
    """
    Analyze migration file for idempotency issues
    
    Args:
        migration_file: Path to migration file
        
    Returns:
        Dict containing validation results
    """
    results = {
        'file': migration_file,
        'issues': [],
        'score': 0,
        'recommendations': []
    }
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for common idempotency issues
        if 'op.create_table(' in content and 'table_exists(' not in content:
            results['issues'].append('Non-idempotent table creation')
            
        if 'op.create_index(' in content and 'index_exists(' not in content:
            results['issues'].append('Non-idempotent index creation')
            
        if 'op.add_column(' in content and 'column_exists(' not in content:
            results['issues'].append('Non-idempotent column addition')
            
        if 'CREATE TYPE' in content and 'enum_exists(' not in content:
            results['issues'].append('Non-idempotent enum creation')
            
        # Calculate score
        total_checks = 4
        passed_checks = total_checks - len(results['issues'])
        results['score'] = (passed_checks / total_checks) * 10
        
        # Generate recommendations
        if results['issues']:
            results['recommendations'] = [
                'Use idempotent utilities from alembic_utils',
                'Add existence checks before CREATE operations',
                'Test migration in both clean and dirty states'
            ]
            
    except Exception as e:
        results['issues'].append(f'File analysis error: {e}')
        
    return results