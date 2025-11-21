#!/usr/bin/env python3
"""
Script simple para completar el seeding de niveles y ejercicios.
Se ejecuta desde el contenedor ECS.
"""
import asyncio
from app.core.db import AsyncSessionLocal
from app.models import Language, Topic, Level, Exercise
from sqlalchemy import select

async def seed_levels_and_exercises():
    """Crea niveles y ejercicios para los tópicos existentes"""
    print("🌱 Completando seed: Niveles y Ejercicios")
    
    async with AsyncSessionLocal() as db:
        # Obtener tópicos existentes
        result = await db.execute(select(Topic))
        topics = result.scalars().all()
        
        print(f"\n📖 Encontrados {len(topics)} tópicos")
        
        levels_created = 0
        exercises_created = 0
        
        # Crear niveles para cada tópico
        for topic in topics[:2]:  # Solo primeros 2 tópicos
            print(f"\n  Procesando: {topic.name}")
            
            # Crear 3 niveles por tópico
            for i in range(1, 4):
                # Verificar si ya existe
                result = await db.execute(
                    select(Level).where(
                        Level.topic_id == topic.id,
                        Level.difficulty == i
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    level = Level(
                        topic_id=topic.id,
                        name=f"Level {i}",
                        description=f"{topic.name} - Level {i}",
                        difficulty=i,
                        order_index=i
                    )
                    db.add(level)
                    await db.flush()
                    levels_created += 1
                    print(f"    ✓ Nivel {i} creado (id={level.id})")
                    
                    # Crear ejercicios para nivel 1
                    if i == 1:
                        if topic.name == "Alphabet":
                            letters = ["A", "B", "C", "D", "E"]
                            for idx, letter in enumerate(letters):
                                exercise = Exercise(
                                    level_id=level.id,
                                    type="multiple_choice",
                                    question_text=f"What letter is this sign?",
                                    correct_answer=letter,
                                    options=[letter, chr(ord(letter)+1), chr(ord(letter)+2), chr(ord(letter)+3)],
                                    gesture_label=f"letter_{letter}",
                                    image_url=f"https://example.com/asl/{letter.lower()}.jpg",
                                    order_index=idx+1
                                )
                                db.add(exercise)
                                exercises_created += 1
                        
                        elif topic.name == "Numbers":
                            numbers = ["1", "2", "3", "4", "5"]
                            for idx, num in enumerate(numbers):
                                exercise = Exercise(
                                    level_id=level.id,
                                    type="video_practice",
                                    question_text=f"Practice signing the number {num}",
                                    correct_answer=num,
                                    gesture_label=f"number_{num}",
                                    image_url=f"https://example.com/asl/num_{num}.jpg",
                                    order_index=idx+1
                                )
                                db.add(exercise)
                                exercises_created += 1
        
        await db.commit()
        
        print(f"\n✅ Completado:")
        print(f"   Niveles creados: {levels_created}")
        print(f"   Ejercicios creados: {exercises_created}")

if __name__ == "__main__":
    asyncio.run(seed_levels_and_exercises())
