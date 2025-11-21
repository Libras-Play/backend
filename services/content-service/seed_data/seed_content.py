"""
Script para poblar la base de datos con datos iniciales
Lee el archivo content_seed.json y crea los registros usando CRUD functions
"""
import asyncio
import json
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import AsyncSessionLocal
from app import crud, schemas


async def load_seed_data():
    """Cargar datos desde el archivo JSON"""
    seed_file = Path(__file__).parent / "content_seed.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_database():
    """Poblar la base de datos con datos de ejemplo"""
    print("🌱 Starting database seeding...")
    
    # Cargar datos
    data = await load_seed_data()
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. Crear Languages
            print("\n📚 Creating languages...")
            language_map = {}
            for lang_data in data["languages"]:
                existing = await crud.get_language_by_code(db, lang_data["code"])
                if existing:
                    print(f"  ⚠️  Language {lang_data['code']} already exists, skipping...")
                    language_map[lang_data["code"]] = existing
                else:
                    language = await crud.create_language(
                        db,
                        schemas.LanguageCreate(**lang_data)
                    )
                    language_map[lang_data["code"]] = language
                    print(f"  ✅ Created language: {language.name} ({language.code})")
            
            # 2. Crear Topics
            print("\n🗂️  Creating topics...")
            topic_map = {}
            for topic_data in data["topics"]:
                lang_code = topic_data.pop("language_code")
                language = language_map[lang_code]
                
                topic = await crud.create_topic(
                    db,
                    schemas.TopicCreate(
                        language_id=language.id,
                        **topic_data
                    )
                )
                topic_key = f"{lang_code}_{topic_data['name']}"
                topic_map[topic_key] = topic
                print(f"  ✅ Created topic: {topic.name} (Language: {lang_code})")
            
            # 3. Crear Levels
            print("\n📊 Creating levels...")
            level_map = {}
            for level_data in data["levels"]:
                topic_name = level_data.pop("topic_name")
                lang_code = level_data.pop("language_code")
                topic_key = f"{lang_code}_{topic_name}"
                topic = topic_map[topic_key]
                
                level = await crud.create_level(
                    db,
                    schemas.LevelCreate(
                        topic_id=topic.id,
                        **level_data
                    )
                )
                level_key = f"{topic_key}_{level_data['title']}"
                level_map[level_key] = level
                print(f"  ✅ Created level: {level.title} (Topic: {topic_name})")
            
            # 4. Crear Exercises
            print("\n✏️  Creating exercises...")
            for exercise_data in data["exercises"]:
                level_title = exercise_data.pop("level_title")
                topic_name = exercise_data.pop("topic_name")
                lang_code = exercise_data.pop("language_code")
                topic_key = f"{lang_code}_{topic_name}"
                level_key = f"{topic_key}_{level_title}"
                level = level_map[level_key]
                
                exercise = await crud.create_exercise(
                    db,
                    schemas.ExerciseCreate(
                        level_id=level.id,
                        **exercise_data
                    )
                )
                print(f"  ✅ Created exercise: {exercise.type} - {exercise.question_text[:50]}...")
            
            # 5. Crear Translations
            print("\n🌐 Creating translations...")
            for trans_data in data["translations"]:
                lang_code = trans_data.pop("language_code")
                language = language_map[lang_code]
                
                translation = await crud.create_translation(
                    db,
                    schemas.TranslationCreate(
                        language_id=language.id,
                        **trans_data
                    )
                )
                print(f"  ✅ Created translation: {translation.key} ({lang_code})")
            
            # 6. Crear Achievements
            print("\n🏆 Creating achievements...")
            for achievement_data in data["achievements"]:
                from app import models
                # Convertir string a enum
                condition_type = achievement_data["condition_type"].upper()
                achievement_data["condition_type"] = models.ConditionType[condition_type]
                
                achievement = await crud.create_achievement(
                    db,
                    schemas.AchievementCreate(**achievement_data)
                )
                print(f"  ✅ Created achievement: {achievement.title} ({achievement.code})")
            
            print("\n✨ Database seeding completed successfully!")
            print(f"\n📊 Summary:")
            print(f"  - Languages: {len(data['languages'])}")
            print(f"  - Topics: {len(data['topics'])}")
            print(f"  - Levels: {len(data['levels'])}")
            print(f"  - Exercises: {len(data['exercises'])}")
            print(f"  - Translations: {len(data['translations'])}")
            print(f"  - Achievements: {len(data['achievements'])}")
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {str(e)}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
