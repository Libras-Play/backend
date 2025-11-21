"""
Script para poblar la base de datos con contenido inicial.
Ejecutar: python scripts/seed_content.py
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.db import AsyncSessionLocal, init_db
from app import crud, schemas, models


async def seed_languages():
    """Crea idiomas de señas"""
    languages_data = [
        {
            "code": "ASL",
            "name": "American Sign Language",
            "description": "Sign language used primarily in the United States and Canada"
        },
        {
            "code": "LSB",
            "name": "Língua Brasileira de Sinais",
            "description": "Brazilian Sign Language"
        },
        {
            "code": "LSM",
            "name": "Lengua de Señas Mexicana",
            "description": "Mexican Sign Language"
        },
    ]
    
    async with AsyncSessionLocal() as db:
        created_languages = []
        for lang_data in languages_data:
            existing = await crud.get_language_by_code(db, lang_data["code"])
            if not existing:
                language = await crud.create_language(db, schemas.LanguageCreate(**lang_data))
                created_languages.append(language)
                print(f"✓ Created language: {language.name}")
            else:
                created_languages.append(existing)
                print(f"- Language already exists: {existing.name}")
        
        await db.commit()
        return created_languages


async def seed_topics(languages):
    """Crea temas/categorías"""
    async with AsyncSessionLocal() as db:
        # Temas para ASL
        asl = next((l for l in languages if l.code == "ASL"), None)
        if asl:
            topics_data = [
                {"name": "Alphabet", "description": "Letters A-Z", "order": 1},
                {"name": "Numbers", "description": "Numbers 0-100", "order": 2},
                {"name": "Greetings", "description": "Common greetings and farewells", "order": 3},
                {"name": "Family", "description": "Family members", "order": 4},
                {"name": "Colors", "description": "Basic colors", "order": 5},
            ]
            
            for topic_data in topics_data:
                topic_data["language_id"] = asl.id
                topic = await crud.create_topic(db, schemas.TopicCreate(**topic_data))
                print(f"✓ Created topic: {topic.name}")
        
        await db.commit()


async def seed_exercises():
    """Crea ejercicios de ejemplo"""
    async with AsyncSessionLocal() as db:
        # Obtener el tema "Alphabet"
        from sqlalchemy import select
        result = await db.execute(
            select(models.Topic).where(models.Topic.name == "Alphabet")
        )
        alphabet_topic = result.scalar_one_or_none()
        
        if alphabet_topic:
            # Crear ejercicios para las letras A-E
            letters = ["A", "B", "C", "D", "E"]
            for i, letter in enumerate(letters):
                exercise_data = {
                    "topic_id": alphabet_topic.id,
                    "title": f"Sign the letter {letter}",
                    "description": f"Learn how to sign the letter {letter} in ASL",
                    "type": models.ExerciseType.VIDEO,
                    "difficulty": models.DifficultyLevel.BEGINNER,
                    "order": i + 1,
                    "content_url": f"https://example.com/videos/asl_letter_{letter.lower()}.mp4",
                    "thumbnail_url": f"https://example.com/thumbs/asl_letter_{letter.lower()}.jpg",
                    "duration_seconds": 30,
                }
                
                exercise = await crud.create_exercise(db, schemas.ExerciseCreate(**exercise_data))
                
                # Agregar traducciones
                translations = [
                    {"locale": "en", "title": f"Sign the letter {letter}", "description": f"Learn how to sign the letter {letter}"},
                    {"locale": "es", "title": f"Señar la letra {letter}", "description": f"Aprende a señar la letra {letter}"},
                    {"locale": "pt", "title": f"Fazer o sinal da letra {letter}", "description": f"Aprenda a fazer o sinal da letra {letter}"},
                ]
                
                for trans_data in translations:
                    trans_data["exercise_id"] = exercise.id
                    await crud.create_translation(db, schemas.TranslationCreate(**trans_data))
                
                print(f"✓ Created exercise: Sign letter {letter}")
        
        await db.commit()


async def main():
    """Función principal"""
    print("=" * 50)
    print("SEEDING CONTENT DATABASE")
    print("=" * 50)
    
    # Inicializar base de datos
    print("\n1. Initializing database...")
    await init_db()
    print("✓ Database initialized")
    
    # Seed languages
    print("\n2. Creating languages...")
    languages = await seed_languages()
    
    # Seed topics
    print("\n3. Creating topics...")
    await seed_topics(languages)
    
    # Seed exercises
    print("\n4. Creating exercises...")
    await seed_exercises()
    
    print("\n" + "=" * 50)
    print("✅ SEEDING COMPLETED SUCCESSFULLY!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
