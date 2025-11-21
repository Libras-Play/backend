#!/usr/bin/env python3
"""
Script para limpiar datos incorrectos y poblar con contenido en Portugués.
Para entrega del 15 de Noviembre.

Limpia:
- ASL, LSM, LSB de la tabla languages (son lenguajes de señas, no idiomas de interfaz)

Crea:
- Tópicos en Portugués (language_id=1: pt-BR)
- Niveles para cada tópico
- Ejercicios de ejemplo en Portugués
"""
import asyncio
from app.core.db import AsyncSessionLocal
from app.models import Language, Topic, Level, Exercise, DifficultyLevel, ExerciseType
from sqlalchemy import select, delete

async def cleanup_incorrect_data():
    """Elimina lenguajes de señas que están incorrectamente en la tabla languages"""
    print("\n🧹 Limpiando datos incorrectos...")
    
    async with AsyncSessionLocal() as db:
        # Eliminar ASL, LSM, LSB (son lenguajes de señas, no idiomas de interfaz)
        incorrect_codes = ["ASL", "LSM", "LSB"]
        
        for code in incorrect_codes:
            result = await db.execute(
                select(Language).where(Language.code == code)
            )
            lang = result.scalar_one_or_none()
            
            if lang:
                # Primero eliminar tópicos asociados
                await db.execute(
                    delete(Topic).where(Topic.language_id == lang.id)
                )
                
                # Luego eliminar el idioma
                await db.delete(lang)
                print(f"  ✓ Eliminado: {lang.name} ({code})")
        
        await db.commit()
        print(f"  ✓ Limpieza completada")


async def seed_portuguese_topics():
    """Crea tópicos en Portugués para Libras"""
    print("\n📖 Creando tópicos en Portugués...")
    
    async with AsyncSessionLocal() as db:
        # Obtener idioma Portugués
        result = await db.execute(
            select(Language).where(Language.code == "pt-BR")
        )
        pt_br = result.scalar_one_or_none()
        
        if not pt_br:
            print("  ❌ Error: No se encontró idioma pt-BR")
            return []
        
        print(f"  ✓ Idioma encontrado: {pt_br.name} (id={pt_br.id})")
        
        # Tópicos en Portugués para Libras
        topics_data = [
            {
                "language_id": pt_br.id,
                "name": "Alfabeto",
                "description": "Letras A-Z em Libras",
                "order_index": 1
            },
            {
                "language_id": pt_br.id,
                "name": "Números",
                "description": "Números de 0 a 100 em Libras",
                "order_index": 2
            },
            {
                "language_id": pt_br.id,
                "name": "Saudações",
                "description": "Cumprimentos e despedidas em Libras",
                "order_index": 3
            },
            {
                "language_id": pt_br.id,
                "name": "Família",
                "description": "Membros da família em Libras",
                "order_index": 4
            },
            {
                "language_id": pt_br.id,
                "name": "Cores",
                "description": "Cores básicas em Libras",
                "order_index": 5
            },
        ]
        
        created_topics = []
        for topic_data in topics_data:
            # Verificar si ya existe
            result = await db.execute(
                select(Topic).where(
                    Topic.language_id == topic_data["language_id"],
                    Topic.name == topic_data["name"]
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                topic = Topic(**topic_data)
                db.add(topic)
                await db.flush()
                created_topics.append(topic)
                print(f"  ✓ Criado: {topic.name}")
            else:
                created_topics.append(existing)
                print(f"  - Já existe: {existing.name}")
        
        await db.commit()
        return created_topics


async def seed_levels(topics):
    """Crea niveles para cada tópico"""
    print("\n🎯 Criando níveis...")
    
    async with AsyncSessionLocal() as db:
        created_levels = []
        
        for topic in topics:
            print(f"\n  Tópico: {topic.name}")
            
            # 3 niveles por tópico
            levels_data = [
                {
                    "topic_id": topic.id,
                    "title": f"Nível 1 - Iniciante - {topic.name}",
                    "difficulty": DifficultyLevel.BEGINNER,
                    "order_index": 1,
                    "xp_reward": 10
                },
                {
                    "topic_id": topic.id,
                    "title": f"Nível 2 - Básico - {topic.name}",
                    "difficulty": DifficultyLevel.INTERMEDIATE,
                    "order_index": 2,
                    "xp_reward": 20
                },
                {
                    "topic_id": topic.id,
                    "title": f"Nível 3 - Intermediário - {topic.name}",
                    "difficulty": DifficultyLevel.ADVANCED,
                    "order_index": 3,
                    "xp_reward": 30
                },
            ]
            
            for level_data in levels_data:
                # Verificar si ya existe
                result = await db.execute(
                    select(Level).where(
                        Level.topic_id == level_data["topic_id"],
                        Level.difficulty == level_data["difficulty"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    level = Level(**level_data)
                    db.add(level)
                    await db.flush()
                    created_levels.append(level)
                    print(f"    ✓ {level.title}")
                else:
                    created_levels.append(existing)
                    print(f"    - Já existe: {existing.title}")
        
        await db.commit()
        return created_levels


async def seed_exercises(levels):
    """Crea ejercicios en Portugués"""
    print("\n✏️  Criando exercícios...")
    
    async with AsyncSessionLocal() as db:
        exercises_created = 0
        
        # Encontrar nivel 1 de Alfabeto
        alphabet_level = None
        numbers_level = None
        
        for level in levels:
            result = await db.execute(
                select(Topic).where(Topic.id == level.topic_id)
            )
            topic = result.scalar_one_or_none()
            
            if topic and topic.name == "Alfabeto" and level.difficulty == DifficultyLevel.BEGINNER:
                alphabet_level = level
            elif topic and topic.name == "Números" and level.difficulty == DifficultyLevel.BEGINNER:
                numbers_level = level
        
        # Ejercicios para Alfabeto
        if alphabet_level:
            print(f"\n  Alfabeto - Nível 1:")
            letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
            
            for idx, letter in enumerate(letters):
                # Verificar si ya existe
                result = await db.execute(
                    select(Exercise).where(
                        Exercise.level_id == alphabet_level.id,
                        Exercise.gesture_label == f"letter_{letter}"
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    exercise = Exercise(
                        level_id=alphabet_level.id,
                        type=ExerciseType.TEST,
                        question_text=f"Qual letra é representada por este sinal?",
                        correct_answer=letter,
                        options=[letter, 
                                chr(ord(letter)+1) if ord(letter) < ord('Z') else 'A',
                                chr(ord(letter)+2) if ord(letter) < ord('Y') else 'B',
                                chr(ord(letter)+3) if ord(letter) < ord('X') else 'C'],
                        gesture_label=f"letter_{letter}",
                        image_url=f"https://example.com/libras/letters/{letter.lower()}.jpg",
                        order_index=idx+1
                    )
                    db.add(exercise)
                    exercises_created += 1
                    print(f"    ✓ Exercício: Letra {letter}")
        
        # Ejercicios para Números
        if numbers_level:
            print(f"\n  Números - Nível 1:")
            numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            
            for idx, num in enumerate(numbers):
                # Verificar si ya existe
                result = await db.execute(
                    select(Exercise).where(
                        Exercise.level_id == numbers_level.id,
                        Exercise.gesture_label == f"number_{num}"
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    exercise = Exercise(
                        level_id=numbers_level.id,
                        type=ExerciseType.TEST,
                        question_text=f"Qual número é representado por este sinal?",
                        correct_answer=str(num),
                        options=[str(num),
                                str(num+1) if num < 10 else "0",
                                str(num+2) if num < 9 else "1",
                                str(num+3) if num < 8 else "2"],
                        gesture_label=f"number_{num}",
                        image_url=f"https://example.com/libras/numbers/{num}.jpg",
                        order_index=idx+1
                    )
                    db.add(exercise)
                    exercises_created += 1
                    print(f"    ✓ Exercício: Número {num}")
        
        await db.commit()
        print(f"\n  Total de exercícios criados: {exercises_created}")


async def verify_data():
    """Verifica los datos finales"""
    print("\n🔍 Verificando dados finais...")
    
    async with AsyncSessionLocal() as db:
        # Languages
        result = await db.execute(select(Language))
        languages = result.scalars().all()
        print(f"\n  Idiomas de interfaz: {len(languages)}")
        for lang in languages:
            print(f"    • {lang.name} ({lang.code})")
        
        # Topics en Portugués
        result = await db.execute(
            select(Language).where(Language.code == "pt-BR")
        )
        pt_br = result.scalar_one_or_none()
        
        if pt_br:
            result = await db.execute(
                select(Topic).where(Topic.language_id == pt_br.id)
            )
            topics = result.scalars().all()
            print(f"\n  Tópicos em Português: {len(topics)}")
            for topic in topics:
                print(f"    • {topic.name}")
        
        # Levels
        result = await db.execute(select(Level))
        levels = result.scalars().all()
        print(f"\n  Níveis totais: {len(levels)}")
        
        # Exercises
        result = await db.execute(select(Exercise))
        exercises = result.scalars().all()
        print(f"\n  Exercícios totais: {len(exercises)}")


async def main():
    """Función principal"""
    print("=" * 70)
    print("🔧 CORRECCIÓN Y SEED DE CONTENIDO EN PORTUGUÉS")
    print("=" * 70)
    print("\nObjetivo: Preparar datos para entrega del 15/Nov/2025")
    print("Idioma de interfaz: Portugués (pt-BR)")
    print("Lenguaje de señas: Libras (LSB)")
    
    try:
        # Paso 1: Limpiar datos incorrectos
        await cleanup_incorrect_data()
        
        # Paso 2: Crear tópicos en Portugués
        topics = await seed_portuguese_topics()
        
        # Paso 3: Crear niveles
        levels = await seed_levels(topics)
        
        # Paso 4: Crear ejercicios
        await seed_exercises(levels)
        
        # Paso 5: Verificar
        await verify_data()
        
        print("\n" + "=" * 70)
        print("✅ ¡CORRECCIÓN Y SEED COMPLETADOS!")
        print("=" * 70)
        print("\n🎯 Ahora prueba en Postman:")
        print("  1. GET /content/api/v1/languages → Verás pt-BR y es-ES")
        print("  2. GET /content/api/v1/languages/1/topics → Verás tópicos en Portugués")
        print("  3. GET /content/api/v1/topics/1/levels → Verás 3 niveles")
        print("  4. GET /content/api/v1/levels/1/exercises → Verás ejercicios")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
