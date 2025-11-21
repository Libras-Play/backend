#!/usr/bin/env python3
"""
Seed script for mission templates in Content Service

Creates initial mission templates with multilanguage support.
Run after alembic migration: alembic upgrade head
"""

import sys
import asyncio
import asyncpg
from typing import List, Dict, Any

# Database connection settings
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "librasplay",
    "password": "devpassword123",
    "database": "content_service"
}

# Mission templates to seed
MISSION_TEMPLATES: List[Dict[str, Any]] = [
    # ============= EASY EXERCISES =============
    {
        "code": "daily_easy_ex_3",
        "title": {
            "es": "Completa 3 ejercicios fáciles",
            "en": "Complete 3 easy exercises",
            "pt": "Complete 3 exercícios fáceis"
        },
        "description": {
            "es": "Practica lo básico completando 3 ejercicios fáciles hoy",
            "en": "Practice the basics by completing 3 easy exercises today",
            "pt": "Pratique o básico completando 3 exercícios fáceis hoje"
        },
        "learning_languages": [],  # All languages
        "metric_type": "exercises_completed",
        "metric_value": 3,
        "difficulty": "easy",
        "reward_coins": 10,
        "reward_xp": 20,
        "reward_gems": 0,
        "image_url": "missions/easy_exercises.png",
        "priority": 10,
        "active": True
    },
    {
        "code": "daily_easy_ex_5",
        "title": {
            "es": "Completa 5 ejercicios fáciles",
            "en": "Complete 5 easy exercises",
            "pt": "Complete 5 exercícios fáceis"
        },
        "description": {
            "es": "¡Desafíate! Completa 5 ejercicios fáciles para ganar más recompensas",
            "en": "Challenge yourself! Complete 5 easy exercises for more rewards",
            "pt": "Desafie-se! Complete 5 exercícios fáceis para mais recompensas"
        },
        "learning_languages": [],
        "metric_type": "exercises_completed",
        "metric_value": 5,
        "difficulty": "easy",
        "reward_coins": 15,
        "reward_xp": 30,
        "reward_gems": 0,
        "image_url": "missions/easy_exercises.png",
        "priority": 8,
        "active": True
    },
    
    # ============= MEDIUM EXERCISES =============
    {
        "code": "daily_medium_ex_3",
        "title": {
            "es": "Completa 3 ejercicios medianos",
            "en": "Complete 3 medium exercises",
            "pt": "Complete 3 exercícios médios"
        },
        "description": {
            "es": "Sube de nivel con 3 ejercicios de dificultad media",
            "en": "Level up with 3 medium difficulty exercises",
            "pt": "Suba de nível com 3 exercícios de dificuldade média"
        },
        "learning_languages": [],
        "metric_type": "exercises_completed",
        "metric_value": 3,
        "difficulty": "medium",
        "reward_coins": 15,
        "reward_xp": 35,
        "reward_gems": 0,
        "image_url": "missions/medium_exercises.png",
        "priority": 9,
        "active": True
    },
    {
        "code": "daily_medium_ex_5",
        "title": {
            "es": "Completa 5 ejercicios medianos",
            "en": "Complete 5 medium exercises",
            "pt": "Complete 5 exercícios médios"
        },
        "description": {
            "es": "Domina el nivel intermedio con 5 ejercicios",
            "en": "Master the intermediate level with 5 exercises",
            "pt": "Domine o nível intermediário com 5 exercícios"
        },
        "learning_languages": [],
        "metric_type": "exercises_completed",
        "metric_value": 5,
        "difficulty": "medium",
        "reward_coins": 20,
        "reward_xp": 50,
        "reward_gems": 1,
        "image_url": "missions/medium_exercises.png",
        "priority": 7,
        "active": True
    },
    
    # ============= HARD EXERCISES =============
    {
        "code": "daily_hard_ex_3",
        "title": {
            "es": "Completa 3 ejercicios difíciles",
            "en": "Complete 3 hard exercises",
            "pt": "Complete 3 exercícios difíceis"
        },
        "description": {
            "es": "¡Acepta el desafío! Completa 3 ejercicios difíciles",
            "en": "Accept the challenge! Complete 3 hard exercises",
            "pt": "Aceite o desafio! Complete 3 exercícios difíceis"
        },
        "learning_languages": [],
        "metric_type": "exercises_completed",
        "metric_value": 3,
        "difficulty": "hard",
        "reward_coins": 25,
        "reward_xp": 60,
        "reward_gems": 1,
        "image_url": "missions/hard_exercises.png",
        "priority": 10,
        "active": True
    },
    
    # ============= PRACTICE (CAMERA MINUTES) =============
    {
        "code": "daily_practice_3min",
        "title": {
            "es": "Practica 3 minutos con cámara",
            "en": "Practice 3 minutes with camera",
            "pt": "Pratique 3 minutos com câmera"
        },
        "description": {
            "es": "Usa la cámara para practicar señas durante 3 minutos",
            "en": "Use the camera to practice signs for 3 minutes",
            "pt": "Use a câmera para praticar sinais por 3 minutos"
        },
        "learning_languages": [],
        "metric_type": "camera_minutes",
        "metric_value": 3,
        "difficulty": None,
        "reward_coins": 15,
        "reward_xp": 25,
        "reward_gems": 0,
        "image_url": "missions/camera_practice.png",
        "priority": 9,
        "active": True
    },
    {
        "code": "daily_practice_5min",
        "title": {
            "es": "Practica 5 minutos con cámara",
            "en": "Practice 5 minutes with camera",
            "pt": "Pratique 5 minutos com câmera"
        },
        "description": {
            "es": "Mejora tu técnica practicando 5 minutos con la cámara",
            "en": "Improve your technique by practicing 5 minutes with camera",
            "pt": "Melhore sua técnica praticando 5 minutos com a câmera"
        },
        "learning_languages": [],
        "metric_type": "camera_minutes",
        "metric_value": 5,
        "difficulty": None,
        "reward_coins": 20,
        "reward_xp": 40,
        "reward_gems": 1,
        "image_url": "missions/camera_practice.png",
        "priority": 8,
        "active": True
    },
    
    # ============= PRACTICE (PRACTICE SECONDS) =============
    {
        "code": "daily_practice_120sec",
        "title": {
            "es": "Practica durante 2 minutos",
            "en": "Practice for 2 minutes",
            "pt": "Pratique por 2 minutos"
        },
        "description": {
            "es": "Dedica 2 minutos a practicar señas hoy",
            "en": "Dedicate 2 minutes to practicing signs today",
            "pt": "Dedique 2 minutos para praticar sinais hoje"
        },
        "learning_languages": [],
        "metric_type": "practice_seconds",
        "metric_value": 120,
        "difficulty": None,
        "reward_coins": 10,
        "reward_xp": 20,
        "reward_gems": 0,
        "image_url": "missions/practice_time.png",
        "priority": 7,
        "active": True
    },
    
    # ============= GOALS (XP EARNED) =============
    {
        "code": "daily_xp_30",
        "title": {
            "es": "Gana 30 XP hoy",
            "en": "Earn 30 XP today",
            "pt": "Ganhe 30 XP hoje"
        },
        "description": {
            "es": "Alcanza 30 puntos de experiencia completando actividades",
            "en": "Reach 30 experience points by completing activities",
            "pt": "Alcance 30 pontos de experiência completando atividades"
        },
        "learning_languages": [],
        "metric_type": "xp_earned",
        "metric_value": 30,
        "difficulty": None,
        "reward_coins": 10,
        "reward_xp": 0,  # No XP reward to avoid recursive loop
        "reward_gems": 1,
        "image_url": "missions/xp_goal.png",
        "priority": 8,
        "active": True
    },
    {
        "code": "daily_xp_50",
        "title": {
            "es": "Gana 50 XP hoy",
            "en": "Earn 50 XP today",
            "pt": "Ganhe 50 XP hoje"
        },
        "description": {
            "es": "¡Gran desafío! Alcanza 50 puntos de experiencia",
            "en": "Big challenge! Reach 50 experience points",
            "pt": "Grande desafio! Alcance 50 pontos de experiência"
        },
        "learning_languages": [],
        "metric_type": "xp_earned",
        "metric_value": 50,
        "difficulty": None,
        "reward_coins": 15,
        "reward_xp": 0,
        "reward_gems": 2,
        "image_url": "missions/xp_goal.png",
        "priority": 7,
        "active": True
    },
    
    # ============= GOALS (TOPIC COMPLETED) =============
    {
        "code": "daily_topic_complete",
        "title": {
            "es": "Completa 1 tema",
            "en": "Complete 1 topic",
            "pt": "Complete 1 tópico"
        },
        "description": {
            "es": "Domina un tema completándolo al 100%",
            "en": "Master a topic by completing it 100%",
            "pt": "Domine um tópico completando-o 100%"
        },
        "learning_languages": [],
        "metric_type": "topic_completed",
        "metric_value": 1,
        "difficulty": None,
        "reward_coins": 30,
        "reward_xp": 75,
        "reward_gems": 2,
        "image_url": "missions/topic_complete.png",
        "priority": 10,
        "active": True
    },
    
    # ============= LANGUAGE-SPECIFIC MISSIONS (LSB - Portuguese) =============
    {
        "code": "daily_lsb_practice",
        "title": {
            "es": "Practica LIBRAS hoy",
            "en": "Practice LIBRAS today",
            "pt": "Pratique LIBRAS hoje"
        },
        "description": {
            "es": "Completa 3 ejercicios de Lengua de Señas Brasileña",
            "en": "Complete 3 Brazilian Sign Language exercises",
            "pt": "Complete 3 exercícios de Língua Brasileira de Sinais"
        },
        "learning_languages": ["LIBRAS"],
        "metric_type": "exercises_completed",
        "metric_value": 3,
        "difficulty": None,
        "reward_coins": 15,
        "reward_xp": 30,
        "reward_gems": 0,
        "image_url": "missions/lsb_practice.png",
        "priority": 9,
        "active": True
    },
]


async def seed_mission_templates():
    """Seed mission templates into PostgreSQL"""
    
    print("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(**DB_CONFIG)
    
    try:
        print(f"\nSeeding {len(MISSION_TEMPLATES)} mission templates...")
        
        for i, template in enumerate(MISSION_TEMPLATES, 1):
            # Check if template already exists
            existing = await conn.fetchval(
                "SELECT id FROM mission_templates WHERE code = $1",
                template["code"]
            )
            
            if existing:
                print(f"  [{i}/{len(MISSION_TEMPLATES)}] SKIP: {template['code']} (already exists)")
                continue
            
            # Insert template
            await conn.execute(
                """
                INSERT INTO mission_templates (
                    code, title, description, learning_languages,
                    metric_type, metric_value, difficulty,
                    reward_coins, reward_xp, reward_gems,
                    image_url, priority, active
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                )
                """,
                template["code"],
                template["title"],  # JSONB
                template["description"],  # JSONB
                template["learning_languages"],  # Array
                template["metric_type"],
                template["metric_value"],
                template["difficulty"],  # Nullable
                template["reward_coins"],
                template["reward_xp"],
                template["reward_gems"],
                template["image_url"],
                template["priority"],
                template["active"]
            )
            
            print(f"  [{i}/{len(MISSION_TEMPLATES)}] ✓ Created: {template['code']}")
        
        # Display summary
        total = await conn.fetchval("SELECT COUNT(*) FROM mission_templates")
        active = await conn.fetchval("SELECT COUNT(*) FROM mission_templates WHERE active = true")
        
        print(f"\n✓ Seed completed!")
        print(f"  Total templates in DB: {total}")
        print(f"  Active templates: {active}")
        
        # Display breakdown by metric_type
        print(f"\nBreakdown by metric type:")
        breakdown = await conn.fetch(
            """
            SELECT metric_type, COUNT(*) as count, AVG(priority) as avg_priority
            FROM mission_templates
            WHERE active = true
            GROUP BY metric_type
            ORDER BY count DESC
            """
        )
        
        for row in breakdown:
            print(f"  - {row['metric_type']}: {row['count']} templates (avg priority: {row['avg_priority']:.1f})")
        
    finally:
        await conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    try:
        asyncio.run(seed_mission_templates())
        print("\n✓ Mission templates seeded successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
