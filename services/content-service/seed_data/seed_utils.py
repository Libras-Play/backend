"""
Idempotent Seed Script Utilities

This module provides utilities for creating idempotent seed scripts that can be
safely run multiple times without creating duplicate data or causing errors.

Usage:
    from seed_utils import (
        IdempotentSeeder, upsert_record, bulk_upsert,
        with_seeding_context, SeederError
    )
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, TypeVar, Generic, Union, Callable
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, text, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase
import json
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=DeclarativeBase)


class SeederError(Exception):
    """Base exception for seeder operations"""
    pass


class DuplicateDataError(SeederError):
    """Raised when duplicate data is detected and strict mode is enabled"""
    pass


class IdempotentSeeder(Generic[T]):
    """
    Generic idempotent seeder for database models
    
    Provides UPSERT functionality and duplicate detection for seed operations.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        model_class: type[T],
        unique_fields: List[str],
        update_fields: Optional[List[str]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize seeder
        
        Args:
            session: AsyncSession for database operations
            model_class: SQLAlchemy model class
            unique_fields: Fields that uniquely identify a record
            update_fields: Fields to update on conflict (if None, no updates)
            strict_mode: If True, raise error on duplicates instead of skipping
        """
        self.session = session
        self.model_class = model_class
        self.unique_fields = unique_fields
        self.update_fields = update_fields or []
        self.strict_mode = strict_mode
        self.stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
    async def upsert(self, data: Dict[str, Any]) -> tuple[T, str]:
        """
        Insert or update a single record
        
        Args:
            data: Dictionary containing record data
            
        Returns:
            Tuple of (record, action) where action is 'created', 'updated', or 'skipped'
            
        Raises:
            DuplicateDataError: If record exists and strict_mode is True
            SeederError: On other database errors
        """
        try:
            # Build unique constraint query
            unique_conditions = []
            for field in self.unique_fields:
                if field in data:
                    unique_conditions.append(
                        getattr(self.model_class, field) == data[field]
                    )
            
            if not unique_conditions:
                raise SeederError(f"No unique field values found in data for {self.model_class.__name__}")
            
            # Check if record exists
            query = select(self.model_class).where(and_(*unique_conditions))
            result = await self.session.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                if self.strict_mode:
                    raise DuplicateDataError(
                        f"Record already exists for {self.model_class.__name__} "
                        f"with {dict((f, data[f]) for f in self.unique_fields if f in data)}"
                    )
                
                if self.update_fields:
                    # Update existing record
                    for field in self.update_fields:
                        if field in data:
                            setattr(existing, field, data[field])
                    
                    # Update timestamp if model has updated_at field
                    if hasattr(existing, 'updated_at'):
                        existing.updated_at = datetime.utcnow()
                    
                    await self.session.flush()
                    self.stats['updated'] += 1
                    return existing, 'updated'
                else:
                    # Skip without updates
                    self.stats['skipped'] += 1
                    return existing, 'skipped'
            
            # Create new record
            record = self.model_class(**data)
            self.session.add(record)
            await self.session.flush()
            self.stats['created'] += 1
            return record, 'created'
            
        except Exception as e:
            self.stats['errors'] += 1
            if isinstance(e, (DuplicateDataError, SeederError)):
                raise
            raise SeederError(f"Error upserting {self.model_class.__name__}: {str(e)}") from e
    
    async def bulk_upsert(
        self, 
        records: List[Dict[str, Any]], 
        batch_size: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[tuple[T, str]]:
        """
        Perform bulk upsert operations
        
        Args:
            records: List of record dictionaries
            batch_size: Number of records to process in each batch
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of (record, action) tuples
        """
        results = []
        total = len(records)
        
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            
            for j, record_data in enumerate(batch):
                try:
                    result = await self.upsert(record_data)
                    results.append(result)
                    
                    if progress_callback:
                        progress_callback(i + j + 1, total)
                        
                except Exception as e:
                    logger.error(f"Error processing record {i + j + 1}: {e}")
                    if self.strict_mode:
                        raise
                    continue
            
            # Commit each batch
            await self.session.commit()
        
        return results
    
    def get_stats(self) -> Dict[str, int]:
        """Get seeding statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset seeding statistics"""
        self.stats = {'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}


async def upsert_record(
    session: AsyncSession,
    model_class: type[T],
    data: Dict[str, Any],
    unique_fields: List[str],
    update_fields: Optional[List[str]] = None
) -> tuple[T, str]:
    """
    Convenience function for single record upsert
    
    Args:
        session: AsyncSession for database operations
        model_class: SQLAlchemy model class
        data: Record data
        unique_fields: Fields that uniquely identify the record
        update_fields: Fields to update on conflict
        
    Returns:
        Tuple of (record, action)
    """
    seeder = IdempotentSeeder(session, model_class, unique_fields, update_fields)
    return await seeder.upsert(data)


async def bulk_upsert(
    session: AsyncSession,
    model_class: type[T],
    records: List[Dict[str, Any]],
    unique_fields: List[str],
    update_fields: Optional[List[str]] = None,
    batch_size: int = 100
) -> List[tuple[T, str]]:
    """
    Convenience function for bulk upsert operations
    
    Args:
        session: AsyncSession for database operations
        model_class: SQLAlchemy model class
        records: List of record dictionaries
        unique_fields: Fields that uniquely identify records
        update_fields: Fields to update on conflict
        batch_size: Batch size for processing
        
    Returns:
        List of (record, action) tuples
    """
    seeder = IdempotentSeeder(session, model_class, unique_fields, update_fields)
    return await seeder.bulk_upsert(records, batch_size)


@asynccontextmanager
async def with_seeding_context(
    session: AsyncSession,
    description: str = "Seed operation",
    rollback_on_error: bool = True
):
    """
    Context manager for seeding operations with logging and error handling
    
    Args:
        session: Database session
        description: Description of the seeding operation
        rollback_on_error: Whether to rollback on error
        
    Usage:
        async with with_seeding_context(session, "Seeding languages") as ctx:
            # seeding operations
    """
    logger.info(f"🌱 Starting {description}...")
    start_time = datetime.utcnow()
    
    class SeedingContext:
        def __init__(self):
            self.stats = {'operations': 0, 'errors': 0}
            
        def log_operation(self, operation: str):
            self.stats['operations'] += 1
            logger.debug(f"  ✅ {operation}")
            
        def log_error(self, error: str):
            self.stats['errors'] += 1
            logger.error(f"  ❌ {error}")
    
    ctx = SeedingContext()
    
    try:
        yield ctx
        
        # Commit if successful
        await session.commit()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"✅ {description} completed successfully in {duration:.2f}s "
            f"(Operations: {ctx.stats['operations']}, Errors: {ctx.stats['errors']})"
        )
        
    except Exception as e:
        if rollback_on_error:
            await session.rollback()
            logger.error(f"❌ {description} failed, rolling back: {str(e)}")
        else:
            logger.error(f"❌ {description} failed: {str(e)}")
        raise


def calculate_data_hash(data: Dict[str, Any], exclude_fields: List[str] = None) -> str:
    """
    Calculate hash for data dictionary (useful for change detection)
    
    Args:
        data: Data dictionary
        exclude_fields: Fields to exclude from hash calculation
        
    Returns:
        Hash string
    """
    exclude_fields = exclude_fields or ['created_at', 'updated_at', 'id']
    
    # Create normalized data for hashing
    normalized_data = {}
    for key, value in data.items():
        if key not in exclude_fields:
            # Normalize datetime objects
            if isinstance(value, datetime):
                normalized_data[key] = value.isoformat()
            else:
                normalized_data[key] = value
    
    # Sort keys for consistent hashing
    sorted_data = json.dumps(normalized_data, sort_keys=True, default=str)
    return hashlib.md5(sorted_data.encode()).hexdigest()


async def validate_referential_integrity(
    session: AsyncSession,
    checks: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Validate referential integrity constraints
    
    Args:
        session: Database session
        checks: List of integrity check definitions
        
    Returns:
        List of validation results
    """
    results = []
    
    for check in checks:
        check_name = check.get('name', 'Unnamed Check')
        query = check.get('query')
        expected_count = check.get('expected_count')
        
        try:
            if isinstance(query, str):
                result = await session.execute(text(query))
                count = result.scalar()
            else:
                result = await session.execute(query)
                count = len(result.fetchall())
            
            status = 'PASS' if count == expected_count else 'FAIL'
            
            results.append({
                'name': check_name,
                'status': status,
                'expected': expected_count,
                'actual': count,
                'query': str(query)
            })
            
        except Exception as e:
            results.append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'query': str(query)
            })
    
    return results


class SeedDataValidator:
    """Validator for seed data integrity and completeness"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def validate_unique_constraints(
        self,
        model_class: type[T],
        unique_fields: List[str]
    ) -> Dict[str, Any]:
        """Validate that unique constraints are not violated"""
        
        # Build query to find duplicates
        field_cols = [getattr(model_class, field) for field in unique_fields]
        
        # Use raw SQL for better performance with complex queries
        table_name = model_class.__table__.name
        fields_str = ', '.join(unique_fields)
        
        query = text(f"""
            SELECT {fields_str}, COUNT(*) as count
            FROM {table_name}
            GROUP BY {fields_str}
            HAVING COUNT(*) > 1
        """)
        
        result = await self.session.execute(query)
        duplicates = result.fetchall()
        
        return {
            'table': table_name,
            'unique_fields': unique_fields,
            'duplicates_found': len(duplicates),
            'duplicates': [dict(row._mapping) for row in duplicates]
        }
    
    async def validate_foreign_keys(
        self,
        model_class: type[T]
    ) -> List[Dict[str, Any]]:
        """Validate foreign key constraints"""
        
        results = []
        table_name = model_class.__table__.name
        
        # Get foreign key constraints
        inspector = inspect(self.session.bind)
        fks = inspector.get_foreign_keys(table_name)
        
        for fk in fks:
            constraint_name = fk['name']
            local_cols = fk['constrained_columns']
            remote_table = fk['referred_table']
            remote_cols = fk['referred_columns']
            
            # Check for orphaned records
            local_col_str = ', '.join(local_cols)
            remote_col_str = ', '.join(remote_cols)
            
            query = text(f"""
                SELECT COUNT(*)
                FROM {table_name} t1
                WHERE NOT EXISTS (
                    SELECT 1 FROM {remote_table} t2
                    WHERE t1.{local_col_str} = t2.{remote_col_str}
                )
                AND t1.{local_col_str} IS NOT NULL
            """)
            
            result = await self.session.execute(query)
            orphaned_count = result.scalar()
            
            results.append({
                'constraint': constraint_name,
                'local_table': table_name,
                'local_columns': local_cols,
                'remote_table': remote_table,
                'remote_columns': remote_cols,
                'orphaned_records': orphaned_count,
                'status': 'PASS' if orphaned_count == 0 else 'FAIL'
            })
        
        return results


# Convenience functions for common seeding patterns

async def seed_lookup_table(
    session: AsyncSession,
    model_class: type[T],
    data: List[Dict[str, Any]],
    unique_field: str = 'code',
    description: str = None
) -> List[T]:
    """
    Seed a lookup table (like languages, countries, etc.)
    
    Args:
        session: Database session
        model_class: Model class
        data: List of records to insert
        unique_field: Field to use for uniqueness check
        description: Description for logging
        
    Returns:
        List of created/found records
    """
    description = description or f"Seeding {model_class.__name__}"
    
    async with with_seeding_context(session, description) as ctx:
        seeder = IdempotentSeeder(
            session, model_class, [unique_field], update_fields=[]
        )
        
        results = []
        for record_data in data:
            record, action = await seeder.upsert(record_data)
            results.append(record)
            
            if action == 'created':
                ctx.log_operation(f"Created {model_class.__name__}: {record_data.get(unique_field)}")
            else:
                ctx.log_operation(f"Found existing {model_class.__name__}: {record_data.get(unique_field)}")
        
        return results


async def seed_with_dependencies(
    session: AsyncSession,
    operations: List[Dict[str, Any]]
) -> Dict[str, List[Any]]:
    """
    Seed multiple related tables in dependency order
    
    Args:
        session: Database session
        operations: List of seeding operations in dependency order
        
    Returns:
        Dictionary mapping operation names to results
    """
    results = {}
    
    for op in operations:
        name = op['name']
        model_class = op['model_class']
        data = op['data']
        unique_fields = op['unique_fields']
        update_fields = op.get('update_fields', [])
        
        async with with_seeding_context(session, f"Seeding {name}") as ctx:
            seeder = IdempotentSeeder(
                session, model_class, unique_fields, update_fields
            )
            
            operation_results = []
            for record_data in data:
                # Allow data to reference previous results
                if callable(record_data):
                    record_data = record_data(results)
                
                record, action = await seeder.upsert(record_data)
                operation_results.append(record)
                
                ctx.log_operation(f"{action.title()} {name}: {record.id}")
            
            results[name] = operation_results
    
    return results