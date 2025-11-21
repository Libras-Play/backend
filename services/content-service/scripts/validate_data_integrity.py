#!/usr/bin/env python3
"""
Database Data Sanity Validation Script

This script provides comprehensive validation of database integrity including:
- Referential integrity checks
- Constraint validation
- Orphaned record detection
- Data consistency verification
- Performance and health metrics

Usage:
    python validate_data_integrity.py --check-all
    python validate_data_integrity.py --check-referential
    python validate_data_integrity.py --check-constraints
    python validate_data_integrity.py --check-orphans
    python validate_data_integrity.py --check-consistency
    python validate_data_integrity.py --fix-issues (DANGEROUS - development only)
"""

import asyncio
import argparse
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import sys
import os

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from sqlalchemy import text, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_database
from app.models import *  # Import all models

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_validation.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    passed: bool
    error_count: int
    warnings: List[str]
    errors: List[str]
    details: Dict[str, Any]
    execution_time_ms: float


class DatabaseValidator:
    """Comprehensive database validation engine"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.results: List[ValidationResult] = []
        self.total_errors = 0
        self.total_warnings = 0
    
    async def validate_all(self) -> List[ValidationResult]:
        """Run all validation checks"""
        logger.info("🔍 Starting comprehensive database validation...")
        
        checks = [
            self.check_referential_integrity,
            self.check_constraint_violations,
            self.check_orphaned_records,
            self.check_data_consistency,
            self.check_enum_values,
            self.check_jsonb_structure,
            self.check_performance_metrics
        ]
        
        for check in checks:
            try:
                result = await check()
                self.results.append(result)
                if result.error_count > 0:
                    self.total_errors += result.error_count
                if result.warnings:
                    self.total_warnings += len(result.warnings)
            except Exception as e:
                logger.error(f"❌ Check {check.__name__} failed with exception: {e}")
                self.results.append(ValidationResult(
                    check_name=check.__name__,
                    passed=False,
                    error_count=1,
                    warnings=[],
                    errors=[f"Exception during check: {str(e)}"],
                    details={},
                    execution_time_ms=0.0
                ))
        
        self.print_summary()
        return self.results
    
    async def check_referential_integrity(self) -> ValidationResult:
        """Check foreign key constraints and referential integrity"""
        logger.info("🔗 Checking referential integrity...")
        start_time = datetime.now()
        errors = []
        warnings = []
        details = {}
        
        # Check exercises -> topics foreign key
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises e
            LEFT JOIN topics t ON e.topic_id = t.id
            WHERE t.id IS NULL
        """))
        orphaned_exercises = result.scalar()
        if orphaned_exercises > 0:
            errors.append(f"{orphaned_exercises} exercises reference non-existent topics")
            details['orphaned_exercises'] = orphaned_exercises
        
        # Check exercises -> sign_languages foreign key
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises e
            LEFT JOIN sign_languages sl ON e.learning_language = sl.code
            WHERE sl.code IS NULL
        """))
        orphaned_sign_refs = result.scalar()
        if orphaned_sign_refs > 0:
            errors.append(f"{orphaned_sign_refs} exercises reference non-existent sign languages")
            details['orphaned_sign_language_refs'] = orphaned_sign_refs
        
        # Check exercise_attempts -> exercise_variants foreign key
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercise_attempts ea
            LEFT JOIN exercise_variants ev ON ea.exercise_variant_id = ev.id
            WHERE ev.id IS NULL
        """))
        orphaned_attempts = result.scalar()
        if orphaned_attempts > 0:
            errors.append(f"{orphaned_attempts} exercise attempts reference non-existent variants")
            details['orphaned_exercise_attempts'] = orphaned_attempts
        
        # Check exercise_variants -> exercise_base foreign key
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercise_variants ev
            LEFT JOIN exercise_base eb ON ev.exercise_base_id = eb.id
            WHERE eb.id IS NULL
        """))
        orphaned_variants = result.scalar()
        if orphaned_variants > 0:
            errors.append(f"{orphaned_variants} exercise variants reference non-existent base exercises")
            details['orphaned_exercise_variants'] = orphaned_variants
        
        # Check life_events -> user_stats foreign key
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM life_events le
            LEFT JOIN user_stats us ON le.user_id = us.user_id
            WHERE us.user_id IS NULL
        """))
        orphaned_life_events = result.scalar()
        if orphaned_life_events > 0:
            errors.append(f"{orphaned_life_events} life events reference non-existent users")
            details['orphaned_life_events'] = orphaned_life_events
        
        # Check for circular dependencies in topics (if any)
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count FROM topics WHERE id = order_index
        """))
        circular_topics = result.scalar()
        if circular_topics > 0:
            warnings.append(f"{circular_topics} topics might have circular order references")
            details['potential_circular_topics'] = circular_topics
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            check_name="referential_integrity",
            passed=len(errors) == 0,
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            details=details,
            execution_time_ms=execution_time
        )
    
    async def check_constraint_violations(self) -> ValidationResult:
        """Check CHECK constraints and data validation rules"""
        logger.info("✅ Checking constraint violations...")
        start_time = datetime.now()
        errors = []
        warnings = []
        details = {}
        
        # Check difficulty values (after enum migration)
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises 
            WHERE difficulty NOT IN ('easy', 'medium', 'hard')
        """))
        invalid_difficulties = result.scalar()
        if invalid_difficulties > 0:
            errors.append(f"{invalid_difficulties} exercises have invalid difficulty values")
            details['invalid_exercise_difficulties'] = invalid_difficulties
        
        # Check exercise_type values
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises 
            WHERE exercise_type NOT IN ('test', 'camera')
        """))
        invalid_types = result.scalar()
        if invalid_types > 0:
            errors.append(f"{invalid_types} exercises have invalid exercise_type values")
            details['invalid_exercise_types'] = invalid_types
        
        # Check exercise_attempts outcome values
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercise_attempts 
            WHERE outcome NOT IN ('correct', 'incorrect', 'skipped')
        """))
        invalid_outcomes = result.scalar()
        if invalid_outcomes > 0:
            errors.append(f"{invalid_outcomes} exercise attempts have invalid outcome values")
            details['invalid_attempt_outcomes'] = invalid_outcomes
        
        # Check achievements condition_type values
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM achievements 
            WHERE condition_type NOT IN ('exercises_completed', 'levels_completed', 'xp_earned', 'streak_days', 'perfect_levels')
        """))
        invalid_conditions = result.scalar()
        if invalid_conditions > 0:
            errors.append(f"{invalid_conditions} achievements have invalid condition_type values")
            details['invalid_achievement_conditions'] = invalid_conditions
        
        # Check life_events event_type values
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM life_events 
            WHERE event_type NOT IN ('lost', 'gained', 'reset')
        """))
        invalid_life_events = result.scalar()
        if invalid_life_events > 0:
            errors.append(f"{invalid_life_events} life events have invalid event_type values")
            details['invalid_life_event_types'] = invalid_life_events
        
        # Check for required fields in test exercises
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises 
            WHERE exercise_type = 'test' AND answers IS NULL
        """))
        test_without_answers = result.scalar()
        if test_without_answers > 0:
            errors.append(f"{test_without_answers} test exercises are missing answers")
            details['test_exercises_without_answers'] = test_without_answers
        
        # Check for required fields in camera exercises
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises 
            WHERE exercise_type = 'camera' AND expected_sign IS NULL
        """))
        camera_without_sign = result.scalar()
        if camera_without_sign > 0:
            errors.append(f"{camera_without_sign} camera exercises are missing expected_sign")
            details['camera_exercises_without_sign'] = camera_without_sign
        
        # Check negative values where they shouldn't exist
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM user_stats 
            WHERE xp_total < 0 OR level < 1 OR lives < 0 OR max_lives < 1
        """))
        invalid_user_stats = result.scalar()
        if invalid_user_stats > 0:
            errors.append(f"{invalid_user_stats} user stats have invalid negative/zero values")
            details['invalid_user_stats'] = invalid_user_stats
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            check_name="constraint_violations",
            passed=len(errors) == 0,
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            details=details,
            execution_time_ms=execution_time
        )
    
    async def check_orphaned_records(self) -> ValidationResult:
        """Check for orphaned records and dangling references"""
        logger.info("🏝️ Checking for orphaned records...")
        start_time = datetime.now()
        errors = []
        warnings = []
        details = {}
        
        # Find exercise_variants without any attempts (might be normal)
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercise_variants ev
            LEFT JOIN exercise_attempts ea ON ev.id = ea.exercise_variant_id
            WHERE ea.id IS NULL
        """))
        unused_variants = result.scalar()
        if unused_variants > 0:
            warnings.append(f"{unused_variants} exercise variants have no attempts (might be new content)")
            details['unused_exercise_variants'] = unused_variants
        
        # Find topics without exercises (might be normal for new topics)
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM topics t
            LEFT JOIN exercises e ON t.id = e.topic_id
            WHERE e.id IS NULL
        """))
        empty_topics = result.scalar()
        if empty_topics > 0:
            warnings.append(f"{empty_topics} topics have no exercises (might be placeholders)")
            details['empty_topics'] = empty_topics
        
        # Find achievements that are impossible to unlock
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM achievements a
            WHERE a.condition_type = 'xp_earned' 
            AND a.condition_value > (
                SELECT COALESCE(MAX(xp_total), 0) FROM user_stats
            ) * 10  -- More than 10x the current max XP
        """))
        impossible_achievements = result.scalar()
        if impossible_achievements > 0:
            warnings.append(f"{impossible_achievements} achievements may be impossible to unlock")
            details['impossible_achievements'] = impossible_achievements
        
        # Find user_stats without any recent activity
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM user_stats us
            WHERE us.last_activity_date < CURRENT_DATE - INTERVAL '90 days'
            OR us.last_activity_date IS NULL
        """))
        inactive_users = result.scalar()
        if inactive_users > 0:
            warnings.append(f"{inactive_users} users have no activity in 90+ days")
            details['inactive_users'] = inactive_users
        
        # Find sign languages not used in any exercises
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM sign_languages sl
            LEFT JOIN exercises e ON sl.code = e.learning_language
            WHERE e.id IS NULL AND sl.is_active = true
        """))
        unused_sign_languages = result.scalar()
        if unused_sign_languages > 0:
            warnings.append(f"{unused_sign_languages} active sign languages have no exercises")
            details['unused_sign_languages'] = unused_sign_languages
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            check_name="orphaned_records",
            passed=len(errors) == 0,
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            details=details,
            execution_time_ms=execution_time
        )
    
    async def check_data_consistency(self) -> ValidationResult:
        """Check logical data consistency and business rules"""
        logger.info("🔄 Checking data consistency...")
        start_time = datetime.now()
        errors = []
        warnings = []
        details = {}
        
        # Check if user XP matches sum of exercise attempts
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM user_stats us
            WHERE us.xp_total != (
                SELECT COALESCE(SUM(ea.xp_earned), 0)
                FROM exercise_attempts ea
                WHERE ea.user_id = us.user_id
            )
        """))
        xp_mismatches = result.scalar()
        if xp_mismatches > 0:
            errors.append(f"{xp_mismatches} users have XP total that doesn't match attempt history")
            details['xp_mismatches'] = xp_mismatches
        
        # Check if user level makes sense for their XP
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM user_stats
            WHERE level > (xp_total / 100) + 1  -- Assuming 100 XP per level
            OR level < 1
        """))
        level_inconsistencies = result.scalar()
        if level_inconsistencies > 0:
            errors.append(f"{level_inconsistencies} users have inconsistent level vs XP")
            details['level_inconsistencies'] = level_inconsistencies
        
        # Check if life events make sense
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM life_events
            WHERE lives_after = lives_before
            OR (event_type = 'lost' AND lives_after >= lives_before)
            OR (event_type = 'gained' AND lives_after <= lives_before)
        """))
        inconsistent_life_events = result.scalar()
        if inconsistent_life_events > 0:
            errors.append(f"{inconsistent_life_events} life events have inconsistent before/after values")
            details['inconsistent_life_events'] = inconsistent_life_events
        
        # Check exercise order within topics
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises e1
            WHERE EXISTS (
                SELECT 1 FROM exercises e2
                WHERE e2.topic_id = e1.topic_id
                AND e2.id != e1.id
                AND e2.order_index = e1.order_index
            )
        """))
        duplicate_orders = result.scalar()
        if duplicate_orders > 0:
            errors.append(f"{duplicate_orders} exercises have duplicate order_index within their topics")
            details['duplicate_exercise_orders'] = duplicate_orders
        
        # Check JSONB structure in exercises (basic validation)
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises
            WHERE exercise_type = 'test' 
            AND (
                answers IS NULL
                OR NOT (answers ? 'correct')
                OR NOT (answers ? 'options')
            )
        """))
        malformed_test_answers = result.scalar()
        if malformed_test_answers > 0:
            errors.append(f"{malformed_test_answers} test exercises have malformed answers JSON")
            details['malformed_test_answers'] = malformed_test_answers
        
        # Check if all topics have reasonable number of exercises
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM topics t
            WHERE (
                SELECT COUNT(*) FROM exercises e WHERE e.topic_id = t.id
            ) > 1000  -- More than 1000 exercises in one topic seems excessive
        """))
        oversized_topics = result.scalar()
        if oversized_topics > 0:
            warnings.append(f"{oversized_topics} topics have unusually high number of exercises (>1000)")
            details['oversized_topics'] = oversized_topics
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            check_name="data_consistency",
            passed=len(errors) == 0,
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            details=details,
            execution_time_ms=execution_time
        )
    
    async def check_enum_values(self) -> ValidationResult:
        """Validate enum values after migration from PostgreSQL enums to VARCHAR"""
        logger.info("🔤 Checking enum values...")
        start_time = datetime.now()
        errors = []
        warnings = []
        details = {}
        
        # Get all unique values for each enum field to validate
        enum_checks = [
            ("exercises", "difficulty", ["easy", "medium", "hard"]),
            ("exercises", "exercise_type", ["test", "camera"]),
            ("exercise_attempts", "outcome", ["correct", "incorrect", "skipped"]),
            ("achievements", "condition_type", ["exercises_completed", "levels_completed", "xp_earned", "streak_days", "perfect_levels"]),
            ("life_events", "event_type", ["lost", "gained", "reset"])
        ]
        
        for table, column, valid_values in enum_checks:
            # Check for invalid values
            placeholders = ','.join([f"'{v}'" for v in valid_values])
            result = await self.session.execute(text(f"""
                SELECT COUNT(*) as count
                FROM {table}
                WHERE {column} NOT IN ({placeholders})
            """))
            invalid_count = result.scalar()
            
            if invalid_count > 0:
                errors.append(f"{invalid_count} records in {table}.{column} have invalid enum values")
                details[f'invalid_{table}_{column}'] = invalid_count
            
            # Get actual unique values for debugging
            result = await self.session.execute(text(f"""
                SELECT DISTINCT {column} as value, COUNT(*) as count
                FROM {table}
                GROUP BY {column}
                ORDER BY count DESC
            """))
            actual_values = {row.value: row.count for row in result}
            details[f'{table}_{column}_distribution'] = actual_values
            
            # Check for case sensitivity issues (values that differ only in case)
            for value in actual_values:
                if value.lower() in [v.lower() for v in valid_values] and value not in valid_values:
                    warnings.append(f"Found case-variant '{value}' in {table}.{column} (should be lowercase)")
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            check_name="enum_values",
            passed=len(errors) == 0,
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            details=details,
            execution_time_ms=execution_time
        )
    
    async def check_jsonb_structure(self) -> ValidationResult:
        """Validate JSONB column structures and required fields"""
        logger.info("📋 Checking JSONB structure...")
        start_time = datetime.now()
        errors = []
        warnings = []
        details = {}
        
        # Check exercises.title JSONB structure
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises
            WHERE title IS NULL 
            OR NOT (title ? 'es' OR title ? 'en' OR title ? 'pt')
        """))
        invalid_titles = result.scalar()
        if invalid_titles > 0:
            errors.append(f"{invalid_titles} exercises have invalid title JSONB structure")
            details['invalid_exercise_titles'] = invalid_titles
        
        # Check exercises.statement JSONB structure
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises
            WHERE statement IS NULL 
            OR NOT (statement ? 'es' OR statement ? 'en' OR statement ? 'pt')
        """))
        invalid_statements = result.scalar()
        if invalid_statements > 0:
            errors.append(f"{invalid_statements} exercises have invalid statement JSONB structure")
            details['invalid_exercise_statements'] = invalid_statements
        
        # Check topics.name JSONB structure
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM topics
            WHERE name IS NULL 
            OR NOT (name ? 'es' OR name ? 'en' OR name ? 'pt')
        """))
        invalid_topic_names = result.scalar()
        if invalid_topic_names > 0:
            errors.append(f"{invalid_topic_names} topics have invalid name JSONB structure")
            details['invalid_topic_names'] = invalid_topic_names
        
        # Check test exercises answers structure
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises
            WHERE exercise_type = 'test'
            AND (
                answers IS NULL
                OR NOT (answers ? 'correct')
                OR NOT (answers ? 'options')
                OR jsonb_array_length(answers->'options') < 2
            )
        """))
        invalid_test_structure = result.scalar()
        if invalid_test_structure > 0:
            errors.append(f"{invalid_test_structure} test exercises have invalid answers JSONB structure")
            details['invalid_test_answers_structure'] = invalid_test_structure
        
        # Check for empty JSONB objects where content is expected
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM exercises
            WHERE title = '{}'::jsonb OR statement = '{}'::jsonb
        """))
        empty_jsonb = result.scalar()
        if empty_jsonb > 0:
            warnings.append(f"{empty_jsonb} exercises have empty JSONB objects for title/statement")
            details['empty_jsonb_content'] = empty_jsonb
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            check_name="jsonb_structure",
            passed=len(errors) == 0,
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            details=details,
            execution_time_ms=execution_time
        )
    
    async def check_performance_metrics(self) -> ValidationResult:
        """Check database performance and health metrics"""
        logger.info("⚡ Checking performance metrics...")
        start_time = datetime.now()
        errors = []
        warnings = []
        details = {}
        
        # Check table sizes
        result = await self.session.execute(text("""
            SELECT 
                schemaname,
                tablename,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 10
        """))
        table_sizes = [dict(row._mapping) for row in result]
        details['largest_tables'] = table_sizes
        
        # Check for tables without primary keys
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.tables t
            LEFT JOIN information_schema.table_constraints tc 
                ON t.table_name = tc.table_name 
                AND tc.constraint_type = 'PRIMARY KEY'
            WHERE t.table_schema = 'public' 
            AND tc.constraint_name IS NULL
        """))
        tables_without_pk = result.scalar()
        if tables_without_pk > 0:
            errors.append(f"{tables_without_pk} tables lack primary keys")
            details['tables_without_primary_keys'] = tables_without_pk
        
        # Check for missing indexes on foreign keys
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.table_constraints tc 
                ON kcu.constraint_name = tc.constraint_name
            LEFT JOIN pg_indexes pi 
                ON kcu.table_name = pi.tablename 
                AND kcu.column_name = ANY(string_to_array(replace(pi.indexdef, 'CREATE INDEX', ''), ','))
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND pi.indexname IS NULL
        """))
        unindexed_fks = result.scalar()
        if unindexed_fks > 0:
            warnings.append(f"{unindexed_fks} foreign keys might benefit from indexes")
            details['potentially_unindexed_foreign_keys'] = unindexed_fks
        
        # Check record counts
        tables_to_count = ['exercises', 'topics', 'exercise_attempts', 'user_stats', 'achievements']
        record_counts = {}
        
        for table in tables_to_count:
            try:
                result = await self.session.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
                count = result.scalar()
                record_counts[table] = count
            except Exception as e:
                warnings.append(f"Could not count records in {table}: {e}")
        
        details['record_counts'] = record_counts
        
        # Check for very large transactions or connections
        result = await self.session.execute(text("""
            SELECT COUNT(*) as count
            FROM pg_stat_activity 
            WHERE state = 'active' 
            AND query_start < NOW() - INTERVAL '5 minutes'
        """))
        long_running_queries = result.scalar()
        if long_running_queries > 0:
            warnings.append(f"{long_running_queries} queries have been running for >5 minutes")
            details['long_running_queries'] = long_running_queries
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return ValidationResult(
            check_name="performance_metrics",
            passed=len(errors) == 0,
            error_count=len(errors),
            warnings=warnings,
            errors=errors,
            details=details,
            execution_time_ms=execution_time
        )
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*80)
        print("🔍 DATABASE VALIDATION SUMMARY")
        print("="*80)
        
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        failed_checks = total_checks - passed_checks
        
        print(f"📊 Total Checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"❌ Failed: {failed_checks}")
        print(f"⚠️  Total Warnings: {self.total_warnings}")
        print(f"🚨 Total Errors: {self.total_errors}")
        
        if self.total_errors == 0:
            print("\n🎉 ALL CHECKS PASSED! Database integrity is excellent.")
        else:
            print(f"\n🔧 ISSUES FOUND: {self.total_errors} errors need attention.")
        
        print("\n" + "-"*80)
        print("DETAILED RESULTS:")
        print("-"*80)
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"\n{status} {result.check_name} ({result.execution_time_ms:.1f}ms)")
            
            if result.errors:
                for error in result.errors:
                    print(f"  🚨 ERROR: {error}")
            
            if result.warnings:
                for warning in result.warnings:
                    print(f"  ⚠️  WARNING: {warning}")
            
            if result.details and any(isinstance(v, (int, float)) for v in result.details.values()):
                print("  📊 Metrics:", end=" ")
                metrics = []
                for k, v in result.details.items():
                    if isinstance(v, (int, float)) and not k.endswith('_distribution'):
                        metrics.append(f"{k}={v}")
                print(", ".join(metrics))
        
        print("\n" + "="*80)


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Database Data Sanity Validation')
    parser.add_argument('--check-all', action='store_true', help='Run all validation checks')
    parser.add_argument('--check-referential', action='store_true', help='Check referential integrity only')
    parser.add_argument('--check-constraints', action='store_true', help='Check constraint violations only')
    parser.add_argument('--check-orphans', action='store_true', help='Check orphaned records only')
    parser.add_argument('--check-consistency', action='store_true', help='Check data consistency only')
    parser.add_argument('--check-enums', action='store_true', help='Check enum values only')
    parser.add_argument('--check-jsonb', action='store_true', help='Check JSONB structure only')
    parser.add_argument('--check-performance', action='store_true', help='Check performance metrics only')
    parser.add_argument('--fix-issues', action='store_true', help='Attempt to fix issues (DANGEROUS)')
    
    args = parser.parse_args()
    
    # Default to check-all if no specific checks requested
    if not any([args.check_referential, args.check_constraints, args.check_orphans, 
               args.check_consistency, args.check_enums, args.check_jsonb, args.check_performance]):
        args.check_all = True
    
    try:
        # Get database session
        db = get_database()
        async with db.get_session() as session:
            validator = DatabaseValidator(session)
            
            if args.check_all:
                results = await validator.validate_all()
            else:
                results = []
                if args.check_referential:
                    results.append(await validator.check_referential_integrity())
                if args.check_constraints:
                    results.append(await validator.check_constraint_violations())
                if args.check_orphans:
                    results.append(await validator.check_orphaned_records())
                if args.check_consistency:
                    results.append(await validator.check_data_consistency())
                if args.check_enums:
                    results.append(await validator.check_enum_values())
                if args.check_jsonb:
                    results.append(await validator.check_jsonb_structure())
                if args.check_performance:
                    results.append(await validator.check_performance_metrics())
                
                validator.results = results
                validator.total_errors = sum(r.error_count for r in results)
                validator.total_warnings = sum(len(r.warnings) for r in results)
                validator.print_summary()
            
            # Exit with error code if issues found
            if validator.total_errors > 0:
                sys.exit(1)
            else:
                sys.exit(0)
                
    except Exception as e:
        logger.error(f"❌ Validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())