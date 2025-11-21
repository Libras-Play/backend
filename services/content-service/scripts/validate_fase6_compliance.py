#!/usr/bin/env python3
"""
FASE 6 Database Safety Comprehensive Validation Suite

This script validates all FASE 6 database safety improvements:
1. Migration idempotency using alembic_utils
2. Seed script safety using IdempotentSeeder
3. Enum migration compatibility with VARCHAR + CHECK constraints
4. Data integrity validation with comprehensive checks
5. CI integration testing readiness

Usage:
    python validate_fase6_compliance.py --all
    python validate_fase6_compliance.py --migration-safety
    python validate_fase6_compliance.py --seed-safety  
    python validate_fase6_compliance.py --enum-migration
    python validate_fase6_compliance.py --data-integrity
    python validate_fase6_compliance.py --ci-readiness
"""

import asyncio
import argparse
import logging
import os
import sys
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Fase6Validator:
    """Comprehensive FASE 6 database safety validator"""
    
    def __init__(self, service_path: Path):
        self.service_path = service_path
        self.results = {}
        self.total_score = 0
        self.max_score = 0
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all FASE 6 validation checks"""
        logger.info("🔍 Starting FASE 6 Database Safety Validation...")
        
        checks = [
            ("migration_safety", self.validate_migration_safety),
            ("seed_safety", self.validate_seed_safety),
            ("enum_migration", self.validate_enum_migration),
            ("data_integrity", self.validate_data_integrity_tools),
            ("ci_readiness", self.validate_ci_integration)
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"Running {check_name} validation...")
                result = check_func()
                self.results[check_name] = result
                self.total_score += result.get('score', 0)
                self.max_score += result.get('max_score', 0)
            except Exception as e:
                logger.error(f"❌ {check_name} validation failed: {e}")
                self.results[check_name] = {
                    'passed': False,
                    'score': 0,
                    'max_score': 10,
                    'errors': [f"Exception: {str(e)}"],
                    'details': {}
                }
                self.max_score += 10
        
        self.print_comprehensive_report()
        return self.results
    
    def validate_migration_safety(self) -> Dict[str, Any]:
        """Validate migration idempotency and safety utilities"""
        logger.info("🗄️ Validating migration safety...")
        
        score = 0
        max_score = 20
        errors = []
        warnings = []
        details = {}
        
        # Check for alembic_utils.py existence
        alembic_utils_path = self.service_path / "alembic" / "alembic_utils.py"
        if alembic_utils_path.exists():
            score += 5
            details['alembic_utils_exists'] = True
            
            # Check for key idempotent functions
            content = alembic_utils_path.read_text()
            required_functions = [
                'table_exists',
                'column_exists', 
                'constraint_exists',
                'create_table_if_not_exists',
                'create_constraint_if_not_exists',
                'migration_context'
            ]
            
            found_functions = []
            for func in required_functions:
                if f"def {func}" in content:
                    found_functions.append(func)
                    score += 1
            
            details['idempotent_functions'] = found_functions
            details['missing_functions'] = list(set(required_functions) - set(found_functions))
            
            if len(found_functions) >= 5:
                score += 3
            elif len(found_functions) >= 3:
                score += 1
        else:
            errors.append("alembic_utils.py not found - migration idempotency not implemented")
            details['alembic_utils_exists'] = False
        
        # Check for migration files using idempotent patterns
        alembic_versions_path = self.service_path / "alembic" / "versions"
        if alembic_versions_path.exists():
            migration_files = list(alembic_versions_path.glob("*.py"))
            idempotent_migrations = 0
            
            for migration_file in migration_files:
                content = migration_file.read_text()
                if any(pattern in content for pattern in [
                    'if_not_exists',
                    'table_exists',
                    'column_exists',
                    'constraint_exists'
                ]):
                    idempotent_migrations += 1
            
            details['total_migrations'] = len(migration_files)
            details['idempotent_migrations'] = idempotent_migrations
            
            if len(migration_files) > 0:
                idempotent_percentage = (idempotent_migrations / len(migration_files)) * 100
                if idempotent_percentage >= 80:
                    score += 5
                elif idempotent_percentage >= 50:
                    score += 3
                elif idempotent_percentage >= 25:
                    score += 1
                else:
                    warnings.append(f"Only {idempotent_percentage:.1f}% of migrations use idempotent patterns")
                
                details['idempotent_percentage'] = idempotent_percentage
        
        return {
            'passed': score >= (max_score * 0.7),  # 70% threshold
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def validate_seed_safety(self) -> Dict[str, Any]:
        """Validate seed script idempotency and safety"""
        logger.info("🌱 Validating seed script safety...")
        
        score = 0
        max_score = 15
        errors = []
        warnings = []
        details = {}
        
        # Check for seed_utils.py
        seed_utils_path = self.service_path / "scripts" / "seed_utils.py"
        if seed_utils_path.exists():
            score += 5
            details['seed_utils_exists'] = True
            
            content = seed_utils_path.read_text()
            
            # Check for IdempotentSeeder class
            if "class IdempotentSeeder" in content:
                score += 3
                details['idempotent_seeder_exists'] = True
                
                # Check for UPSERT methods
                if "upsert" in content:
                    score += 2
                    details['upsert_support'] = True
                
                # Check for conflict handling
                if any(pattern in content for pattern in [
                    'ON CONFLICT',
                    'on_conflict_do_nothing',
                    'on_conflict_do_update'
                ]):
                    score += 2
                    details['conflict_handling'] = True
            else:
                errors.append("IdempotentSeeder class not found in seed_utils.py")
        else:
            errors.append("seed_utils.py not found - seed idempotency not implemented")
            details['seed_utils_exists'] = False
        
        # Check for seed scripts using idempotent patterns
        scripts_path = self.service_path / "scripts"
        if scripts_path.exists():
            seed_files = list(scripts_path.glob("seed_*.py"))
            idempotent_seeds = 0
            
            for seed_file in seed_files:
                content = seed_file.read_text()
                if any(pattern in content for pattern in [
                    'IdempotentSeeder',
                    'upsert',
                    'get_or_create'
                ]):
                    idempotent_seeds += 1
            
            details['total_seed_scripts'] = len(seed_files)
            details['idempotent_seed_scripts'] = idempotent_seeds
            
            if len(seed_files) > 0:
                if idempotent_seeds == len(seed_files):
                    score += 3
                elif idempotent_seeds > 0:
                    score += 1
                    warnings.append(f"Only {idempotent_seeds}/{len(seed_files)} seed scripts use idempotent patterns")
        
        return {
            'passed': score >= (max_score * 0.7),
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def validate_enum_migration(self) -> Dict[str, Any]:
        """Validate enum to VARCHAR migration implementation"""
        logger.info("🔤 Validating enum migration...")
        
        score = 0
        max_score = 20
        errors = []
        warnings = []
        details = {}
        
        # Check for enum migration file
        alembic_versions_path = self.service_path / "alembic" / "versions"
        enum_migration_found = False
        
        if alembic_versions_path.exists():
            migration_files = list(alembic_versions_path.glob("*enum*varchar*.py"))
            if not migration_files:
                migration_files = list(alembic_versions_path.glob("*0999*.py"))
            
            if migration_files:
                enum_migration_found = True
                score += 5
                details['enum_migration_exists'] = True
                
                # Check migration content
                migration_content = migration_files[0].read_text()
                
                # Check for comprehensive enum conversion
                if all(pattern in migration_content for pattern in [
                    'difficulty',
                    'exercise_type', 
                    'condition_type',
                    'CHECK'
                ]):
                    score += 5
                    details['comprehensive_enum_conversion'] = True
                
                # Check for data migration
                if 'UPDATE' in migration_content and 'SET' in migration_content:
                    score += 3
                    details['data_migration_included'] = True
                
                # Check for constraint creation
                if 'CheckConstraint' in migration_content or 'check_' in migration_content:
                    score += 3
                    details['check_constraints_added'] = True
            else:
                errors.append("No enum-to-varchar migration file found")
        
        # Check for updated models.py with CaseInsensitiveEnum
        models_path = self.service_path / "app" / "models.py"
        models_updated_path = self.service_path / "app" / "models_updated.py"
        
        target_models = models_updated_path if models_updated_path.exists() else models_path
        
        if target_models.exists():
            models_content = target_models.read_text()
            
            # Check for CaseInsensitiveEnum TypeDecorator
            if "class CaseInsensitiveEnum" in models_content:
                score += 2
                details['case_insensitive_enum_exists'] = True
            
            # Check that SQLEnum is not used anymore (in updated models)
            if models_updated_path.exists() and "SQLEnum" not in models_content:
                score += 2
                details['sqlenum_removed'] = True
            elif "SQLEnum" in models_content:
                warnings.append("SQLEnum still found in models - migration may not be complete")
        
        return {
            'passed': score >= (max_score * 0.6),  # 60% threshold (this is complex)
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def validate_data_integrity_tools(self) -> Dict[str, Any]:
        """Validate data integrity validation tools"""
        logger.info("🔍 Validating data integrity tools...")
        
        score = 0
        max_score = 15
        errors = []
        warnings = []
        details = {}
        
        # Check for comprehensive validation script
        validation_script_path = self.service_path / "scripts" / "validate_data_integrity.py"
        if validation_script_path.exists():
            score += 5
            details['validation_script_exists'] = True
            
            content = validation_script_path.read_text()
            
            # Check for comprehensive validation methods
            validation_methods = [
                'check_referential_integrity',
                'check_constraint_violations',
                'check_orphaned_records',
                'check_data_consistency',
                'check_enum_values',
                'check_jsonb_structure'
            ]
            
            found_methods = []
            for method in validation_methods:
                if method in content:
                    found_methods.append(method)
                    score += 1
            
            details['validation_methods'] = found_methods
            details['validation_coverage'] = len(found_methods) / len(validation_methods)
            
            # Check for command-line interface
            if 'argparse' in content and '--check-' in content:
                score += 2
                details['cli_interface'] = True
            
            # Check for detailed reporting
            if 'ValidationResult' in content and 'print_summary' in content:
                score += 2
                details['detailed_reporting'] = True
        else:
            errors.append("Comprehensive validation script not found")
            details['validation_script_exists'] = False
        
        return {
            'passed': score >= (max_score * 0.7),
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def validate_ci_integration(self) -> Dict[str, Any]:
        """Validate CI integration for database safety"""
        logger.info("🔄 Validating CI integration...")
        
        score = 0
        max_score = 10
        errors = []
        warnings = []
        details = {}
        
        # Check for CI workflow file
        ci_workflow_path = self.service_path.parent.parent / ".github" / "workflows" / "ci.yml"
        if ci_workflow_path.exists():
            score += 2
            details['ci_workflow_exists'] = True
            
            content = ci_workflow_path.read_text()
            
            # Check for migration integration tests
            if 'migration-integration-tests' in content:
                score += 2
                details['migration_tests_in_ci'] = True
            
            # Check for data validation in CI
            if 'database-integrity-validation' in content or 'validate_data_integrity' in content:
                score += 3
                details['data_validation_in_ci'] = True
            
            # Check for proper database setup in CI
            if 'postgres:' in content and 'DATABASE_URL' in content:
                score += 2
                details['database_setup_in_ci'] = True
            
            # Check for comprehensive testing phases
            if all(phase in content for phase in [
                'Clean Database Migration',
                'Idempotency Test',
                'Rollback Test'
            ]):
                score += 1
                details['comprehensive_ci_testing'] = True
        else:
            errors.append("CI workflow file not found")
            details['ci_workflow_exists'] = False
        
        return {
            'passed': score >= (max_score * 0.7),
            'score': score,
            'max_score': max_score,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def print_comprehensive_report(self):
        """Print comprehensive FASE 6 validation report"""
        print("\n" + "="*100)
        print("🔍 FASE 6 DATABASE SAFETY COMPREHENSIVE VALIDATION REPORT")
        print("="*100)
        
        overall_percentage = (self.total_score / self.max_score * 100) if self.max_score > 0 else 0
        
        # Overall status
        if overall_percentage >= 85:
            status = "🎉 EXCELLENT"
            color = "GREEN"
        elif overall_percentage >= 70:
            status = "✅ GOOD"
            color = "YELLOW"
        elif overall_percentage >= 50:
            status = "⚠️  NEEDS IMPROVEMENT"
            color = "ORANGE"
        else:
            status = "❌ CRITICAL ISSUES"
            color = "RED"
        
        print(f"\n📊 OVERALL COMPLIANCE: {status}")
        print(f"📈 TOTAL SCORE: {self.total_score}/{self.max_score} ({overall_percentage:.1f}%)")
        
        # Print detailed results for each area
        print(f"\n{'='*100}")
        print("DETAILED VALIDATION RESULTS")
        print(f"{'='*100}")
        
        for check_name, result in self.results.items():
            status_icon = "✅" if result['passed'] else "❌"
            percentage = (result['score'] / result['max_score'] * 100) if result['max_score'] > 0 else 0
            
            print(f"\n{status_icon} {check_name.upper().replace('_', ' ')}")
            print(f"   Score: {result['score']}/{result['max_score']} ({percentage:.1f}%)")
            
            if result['errors']:
                print("   🚨 ERRORS:")
                for error in result['errors']:
                    print(f"      • {error}")
            
            if result['warnings']:
                print("   ⚠️  WARNINGS:")
                for warning in result['warnings']:
                    print(f"      • {warning}")
            
            if result['details']:
                print("   📋 DETAILS:")
                for key, value in result['details'].items():
                    if isinstance(value, bool):
                        print(f"      • {key}: {'✅' if value else '❌'}")
                    elif isinstance(value, (int, float)):
                        print(f"      • {key}: {value}")
                    elif isinstance(value, list) and len(value) < 10:
                        print(f"      • {key}: {', '.join(map(str, value))}")
        
        # Recommendations
        print(f"\n{'='*100}")
        print("🎯 FASE 6 COMPLIANCE RECOMMENDATIONS")
        print(f"{'='*100}")
        
        if overall_percentage < 85:
            print("\n🔧 PRIORITY IMPROVEMENTS:")
            
            for check_name, result in self.results.items():
                if not result['passed']:
                    print(f"\n• {check_name.replace('_', ' ').title()}:")
                    for error in result['errors']:
                        print(f"  - Fix: {error}")
        
        print(f"\n{'='*100}")
        print("📚 FASE 6 DATABASE SAFETY CHECKLIST")
        print(f"{'='*100}")
        
        checklist = [
            ("Migration Idempotency", self.results.get('migration_safety', {}).get('passed', False)),
            ("Seed Script Safety", self.results.get('seed_safety', {}).get('passed', False)),
            ("Enum Migration", self.results.get('enum_migration', {}).get('passed', False)),
            ("Data Integrity Tools", self.results.get('data_integrity', {}).get('passed', False)),
            ("CI Integration", self.results.get('ci_readiness', {}).get('passed', False))
        ]
        
        for item, status in checklist:
            icon = "✅" if status else "❌"
            print(f"{icon} {item}")
        
        print(f"\n{'='*100}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='FASE 6 Database Safety Comprehensive Validation')
    parser.add_argument('--all', action='store_true', help='Run all validation checks (default)')
    parser.add_argument('--migration-safety', action='store_true', help='Validate migration idempotency')
    parser.add_argument('--seed-safety', action='store_true', help='Validate seed script safety')
    parser.add_argument('--enum-migration', action='store_true', help='Validate enum migration')
    parser.add_argument('--data-integrity', action='store_true', help='Validate data integrity tools')
    parser.add_argument('--ci-readiness', action='store_true', help='Validate CI integration')
    parser.add_argument('--service-path', type=str, default='.', help='Path to service directory')
    
    args = parser.parse_args()
    
    # Default to all if no specific checks requested
    if not any([args.migration_safety, args.seed_safety, args.enum_migration, 
               args.data_integrity, args.ci_readiness]):
        args.all = True
    
    service_path = Path(args.service_path)
    validator = Fase6Validator(service_path)
    
    try:
        if args.all:
            results = validator.validate_all()
        else:
            # Run individual checks (not implemented for brevity)
            results = validator.validate_all()  # For now, run all
        
        # Exit with error code if compliance is below 70%
        overall_percentage = (validator.total_score / validator.max_score * 100) if validator.max_score > 0 else 0
        
        if overall_percentage < 70:
            print(f"\n❌ FASE 6 compliance below 70% threshold ({overall_percentage:.1f}%)")
            sys.exit(1)
        else:
            print(f"\n✅ FASE 6 compliance above 70% threshold ({overall_percentage:.1f}%)")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ FASE 6 validation failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()