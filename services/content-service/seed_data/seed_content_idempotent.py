"""
Idempotent Content Seeding Script

This script safely populates the content database with initial data.
It can be run multiple times without creating duplicates.

Usage: python seed_data/seed_content_idempotent.py
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import AsyncSessionLocal, init_db
from app import models, schemas
from seed_utils import (
    IdempotentSeeder,
    with_seeding_context,
    seed_lookup_table,
    seed_with_dependencies,
    SeedDataValidator
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_seed_data() -> Dict[str, Any]:
    """Load seed data from JSON file"""
    seed_file = Path(__file__).parent / "content_seed.json"
    
    if not seed_file.exists():
        # Create minimal seed data if file doesn't exist
        logger.warning(f"Seed file {seed_file} not found, using minimal data")
        return {
            "languages": [
                {"code": "LSB", "name": "Língua Brasileira de Sinais", "flag_url": None},
                {"code": "ASL", "name": "American Sign Language", "flag_url": None},
            ],
            "topics": [
                {"language_code": "LSB", "name": "Alfabeto", "description": "Letras A-Z", "order_index": 1},
                {"language_code": "LSB", "name": "Números", "description": "Números 0-100", "order_index": 2},
            ],
            "levels": [],
            "exercises": [],
            "translations": [],
            "achievements": []
        }
    
    with open(seed_file, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_languages(session: AsyncSession, languages_data: List[Dict[str, Any]]) -> Dict[str, models.Language]:
    """Seed languages table with idempotency"""
    
    # Use the lookup table seeder for simple reference data
    languages = await seed_lookup_table(
        session=session,
        model_class=models.Language,
        data=languages_data,
        unique_field='code',
        description="Seeding sign languages"
    )
    
    # Create lookup map for use in other seeders
    return {lang.code: lang for lang in languages}


async def seed_topics(
    session: AsyncSession, 
    topics_data: List[Dict[str, Any]], 
    language_map: Dict[str, models.Language]
) -> Dict[str, models.Topic]:
    """Seed topics table with language references"""
    
    async with with_seeding_context(session, "Seeding topics") as ctx:
        seeder = IdempotentSeeder(
            session=session,
            model_class=models.Topic,
            unique_fields=['language_id', 'name'],
            update_fields=['description', 'order_index', 'icon_url']
        )
        
        topic_map = {}
        
        for topic_data in topics_data:
            # Resolve language reference
            lang_code = topic_data.pop('language_code')
            language = language_map.get(lang_code)
            
            if not language:
                ctx.log_error(f"Language {lang_code} not found for topic {topic_data.get('name')}")
                continue
            
            # Prepare topic data with language_id
            final_data = {
                **topic_data,
                'language_id': language.id,
                'created_at': models.utcnow(),
                'updated_at': models.utcnow()
            }
            
            topic, action = await seeder.upsert(final_data)
            topic_key = f"{lang_code}_{topic.name}"
            topic_map[topic_key] = topic
            
            ctx.log_operation(f"{action.title()} topic: {topic.name} ({lang_code})")
    
    return topic_map


async def seed_levels(
    session: AsyncSession,
    levels_data: List[Dict[str, Any]],
    topic_map: Dict[str, models.Topic]
) -> Dict[str, models.Level]:
    """Seed levels table with topic references"""
    
    async with with_seeding_context(session, "Seeding levels") as ctx:
        seeder = IdempotentSeeder(
            session=session,
            model_class=models.Level,
            unique_fields=['topic_id', 'title'],
            update_fields=['difficulty', 'order_index', 'xp_reward', 'unlocks_next']
        )
        
        level_map = {}
        
        for level_data in levels_data:
            # Resolve topic reference
            topic_name = level_data.pop('topic_name')
            lang_code = level_data.pop('language_code')
            topic_key = f"{lang_code}_{topic_name}"
            topic = topic_map.get(topic_key)
            
            if not topic:
                ctx.log_error(f"Topic {topic_key} not found for level {level_data.get('title')}")
                continue
            
            # Prepare level data
            final_data = {
                **level_data,
                'topic_id': topic.id,
                'created_at': models.utcnow(),
                'updated_at': models.utcnow()
            }
            
            level, action = await seeder.upsert(final_data)
            level_key = f"{topic_key}_{level.title}"
            level_map[level_key] = level
            
            ctx.log_operation(f"{action.title()} level: {level.title}")
    
    return level_map


async def seed_exercises(
    session: AsyncSession,
    exercises_data: List[Dict[str, Any]],
    level_map: Dict[str, models.Level]
) -> List[models.Exercise]:
    """Seed exercises table with level references"""
    
    async with with_seeding_context(session, "Seeding exercises") as ctx:
        seeder = IdempotentSeeder(
            session=session,
            model_class=models.Exercise,
            unique_fields=['level_id', 'order_index'],  # Assuming unique per level
            update_fields=[
                'type', 'question_text', 'correct_answer', 'image_url',
                'options', 'gesture_label', 'updated_at'
            ]
        )
        
        exercises = []
        
        for exercise_data in exercises_data:
            # Resolve level reference
            level_title = exercise_data.pop('level_title')
            topic_name = exercise_data.pop('topic_name')
            lang_code = exercise_data.pop('language_code')
            level_key = f"{lang_code}_{topic_name}_{level_title}"
            level = level_map.get(level_key)
            
            if not level:
                ctx.log_error(f"Level {level_key} not found for exercise")
                continue
            
            # Prepare exercise data
            final_data = {
                **exercise_data,
                'level_id': level.id,
                'created_at': models.utcnow(),
                'updated_at': models.utcnow()
            }
            
            exercise, action = await seeder.upsert(final_data)
            exercises.append(exercise)
            
            # Truncate question for logging
            question_preview = (final_data.get('question_text', 'No question')[:50] + '...') \
                if len(final_data.get('question_text', '')) > 50 else final_data.get('question_text', 'No question')
            
            ctx.log_operation(f"{action.title()} exercise: {exercise.type} - {question_preview}")
    
    return exercises


async def seed_translations(
    session: AsyncSession,
    translations_data: List[Dict[str, Any]],
    language_map: Dict[str, models.Language]
) -> List[models.Translation]:
    """Seed translations table"""
    
    async with with_seeding_context(session, "Seeding translations") as ctx:
        seeder = IdempotentSeeder(
            session=session,
            model_class=models.Translation,
            unique_fields=['key', 'language_id'],
            update_fields=['value', 'updated_at']
        )
        
        translations = []
        
        for trans_data in translations_data:
            # Resolve language reference
            lang_code = trans_data.pop('language_code')
            language = language_map.get(lang_code)
            
            if not language:
                ctx.log_error(f"Language {lang_code} not found for translation {trans_data.get('key')}")
                continue
            
            # Prepare translation data
            final_data = {
                **trans_data,
                'language_id': language.id,
                'created_at': models.utcnow(),
                'updated_at': models.utcnow()
            }
            
            translation, action = await seeder.upsert(final_data)
            translations.append(translation)
            
            ctx.log_operation(f"{action.title()} translation: {translation.key} ({lang_code})")
    
    return translations


async def seed_achievements(
    session: AsyncSession,
    achievements_data: List[Dict[str, Any]]
) -> List[models.Achievement]:
    """Seed achievements table"""
    
    async with with_seeding_context(session, "Seeding achievements") as ctx:
        seeder = IdempotentSeeder(
            session=session,
            model_class=models.Achievement,
            unique_fields=['code'],
            update_fields=['title', 'description', 'condition_type', 'condition_value', 'reward', 'icon_url', 'updated_at']
        )
        
        achievements = []
        
        for achievement_data in achievements_data:
            # Convert condition_type string to enum if needed
            if 'condition_type' in achievement_data and isinstance(achievement_data['condition_type'], str):
                try:
                    achievement_data['condition_type'] = models.ConditionType[achievement_data['condition_type'].upper()]
                except KeyError:
                    ctx.log_error(f"Unknown condition type: {achievement_data['condition_type']}")
                    continue
            
            # Prepare achievement data
            final_data = {
                **achievement_data,
                'created_at': models.utcnow(),
                'updated_at': models.utcnow()
            }
            
            achievement, action = await seeder.upsert(final_data)
            achievements.append(achievement)
            
            ctx.log_operation(f"{action.title()} achievement: {achievement.title} ({achievement.code})")
    
    return achievements


async def validate_seeded_data(session: AsyncSession) -> Dict[str, Any]:
    """Validate the integrity of seeded data"""
    
    logger.info("🔍 Validating seeded data integrity...")
    
    validator = SeedDataValidator(session)
    
    validation_results = {
        'unique_constraints': [],
        'foreign_keys': [],
        'summary': {}
    }
    
    # Check unique constraints for key tables
    key_models = [
        (models.Language, ['code']),
        (models.Topic, ['language_id', 'name']),
        (models.Level, ['topic_id', 'title']),
        (models.Translation, ['key', 'language_id']),
        (models.Achievement, ['code'])
    ]
    
    for model_class, unique_fields in key_models:
        result = await validator.validate_unique_constraints(model_class, unique_fields)
        validation_results['unique_constraints'].append(result)
        
        if result['duplicates_found'] > 0:
            logger.warning(f"⚠️ Found {result['duplicates_found']} duplicates in {result['table']}")
    
    # Check foreign key constraints
    foreign_key_models = [models.Topic, models.Level, models.Exercise, models.Translation]
    
    for model_class in foreign_key_models:
        fk_results = await validator.validate_foreign_keys(model_class)
        validation_results['foreign_keys'].extend(fk_results)
        
        for fk_result in fk_results:
            if fk_result['status'] == 'FAIL':
                logger.warning(
                    f"⚠️ Found {fk_result['orphaned_records']} orphaned records "
                    f"in {fk_result['constraint']}"
                )
    
    # Generate summary
    total_duplicates = sum(r['duplicates_found'] for r in validation_results['unique_constraints'])
    total_orphans = sum(r['orphaned_records'] for r in validation_results['foreign_keys'])
    
    validation_results['summary'] = {
        'total_duplicate_violations': total_duplicates,
        'total_orphaned_records': total_orphans,
        'validation_status': 'PASS' if total_duplicates == 0 and total_orphans == 0 else 'FAIL'
    }
    
    if validation_results['summary']['validation_status'] == 'PASS':
        logger.info("✅ Data validation passed - no integrity issues found")
    else:
        logger.warning("⚠️ Data validation found issues - check logs for details")
    
    return validation_results


async def main():
    """Main seeding function"""
    logger.info("=" * 70)
    logger.info("🌱 STARTING IDEMPOTENT CONTENT DATABASE SEEDING")
    logger.info("=" * 70)
    
    try:
        # Initialize database
        logger.info("📊 Initializing database connection...")
        await init_db()
        
        # Load seed data
        logger.info("📖 Loading seed data...")
        data = await load_seed_data()
        
        async with AsyncSessionLocal() as session:
            # Seed in dependency order
            language_map = await seed_languages(session, data["languages"])
            topic_map = await seed_topics(session, data["topics"], language_map)
            level_map = await seed_levels(session, data["levels"], topic_map)
            
            exercises = await seed_exercises(session, data["exercises"], level_map)
            translations = await seed_translations(session, data["translations"], language_map)
            achievements = await seed_achievements(session, data["achievements"])
            
            # Validate seeded data
            validation_results = await validate_seeded_data(session)
            
            # Generate summary
            logger.info("\n" + "=" * 70)
            logger.info("✅ IDEMPOTENT SEEDING COMPLETED SUCCESSFULLY!")
            logger.info("=" * 70)
            logger.info(f"📊 Summary:")
            logger.info(f"   Languages: {len(language_map)} items")
            logger.info(f"   Topics: {len(topic_map)} items")
            logger.info(f"   Levels: {len(level_map)} items")
            logger.info(f"   Exercises: {len(exercises)} items")
            logger.info(f"   Translations: {len(translations)} items")
            logger.info(f"   Achievements: {len(achievements)} items")
            logger.info(f"   Validation Status: {validation_results['summary']['validation_status']}")
            logger.info("\n🔄 This script can be run multiple times safely - it's fully idempotent!")
            
    except Exception as e:
        logger.error(f"❌ Seeding failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())