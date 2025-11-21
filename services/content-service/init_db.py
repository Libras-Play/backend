#!/usr/bin/env python3
"""
FASE 4: Initialize mission_templates table before Alembic runs.
This bypasses Alembic migration chain conflicts.
"""
import asyncio
import asyncpg
import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import get_settings


async def init_mission_templates():
    """Create mission_templates table and update alembic_version"""
    settings = get_settings()
    database_url = settings.DATABASE_URL
    
    if not database_url:
        print("ERROR: DATABASE_URL not configured", file=sys.stderr)
        sys.exit(1)
    
    # Convert SQLAlchemy URL to asyncpg format
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Step 1: Create enum
        await conn.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'metric_type_enum') THEN
                    CREATE TYPE metric_type_enum AS ENUM (
                        'exercises_completed',
                        'camera_minutes',
                        'xp_earned',
                        'topic_completed',
                        'practice_seconds'
                    );
                END IF;
            END$$;
        """)
        print("✓ metric_type_enum created/verified")
        
        # Step 2: Create table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mission_templates (
                id SERIAL PRIMARY KEY,
                code VARCHAR(100) UNIQUE NOT NULL,
                title JSONB NOT NULL,
                description JSONB NOT NULL,
                learning_languages TEXT[] NOT NULL DEFAULT '{}',
                metric_type metric_type_enum NOT NULL,
                metric_value INTEGER NOT NULL,
                difficulty VARCHAR(20),
                reward_coins INTEGER NOT NULL DEFAULT 0,
                reward_xp INTEGER NOT NULL DEFAULT 0,
                reward_gems INTEGER NOT NULL DEFAULT 0,
                image_url VARCHAR(500),
                active BOOLEAN NOT NULL DEFAULT true,
                priority INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                
                CONSTRAINT positive_metric_value CHECK (metric_value > 0),
                CONSTRAINT positive_reward_coins CHECK (reward_coins >= 0),
                CONSTRAINT positive_reward_xp CHECK (reward_xp >= 0),
                CONSTRAINT positive_reward_gems CHECK (reward_gems >= 0),
                CONSTRAINT positive_priority CHECK (priority >= 0)
            )
        """)
        print("✓ mission_templates table created/verified")
        
        # Step 3: Create indexes
        indexes = [
            ("idx_mission_templates_code", "CREATE INDEX IF NOT EXISTS idx_mission_templates_code ON mission_templates(code)"),
            ("idx_mission_templates_active", "CREATE INDEX IF NOT EXISTS idx_mission_templates_active ON mission_templates(active)"),
            ("idx_mission_templates_active_priority", "CREATE INDEX IF NOT EXISTS idx_mission_templates_active_priority ON mission_templates(active, priority) WHERE active = true"),
            ("idx_mission_templates_languages", "CREATE INDEX IF NOT EXISTS idx_mission_templates_languages ON mission_templates USING GIN (learning_languages)"),
        ]
        
        for idx_name, sql in indexes:
            await conn.execute(sql)
            print(f"✓ {idx_name} created/verified")
        
        # Step 4: Update alembic_version - clean up all old entries
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
        )
        
        if table_exists:
            # Get current version
            current_version = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
            print(f"Current alembic_version: {current_version}")
            
            # Clean up - delete ALL old versions
            deleted_count = await conn.execute("DELETE FROM alembic_version")
            print(f"Deleted {deleted_count} old alembic_version entries")
            
            # Insert only 9f8e7d6c5b4a
            await conn.execute(
                "INSERT INTO alembic_version (version_num) VALUES ('9f8e7d6c5b4a')"
            )
            print("✓ alembic_version set to 9f8e7d6c5b4a (mission_templates)")
        
        print("✅ FASE 4 database initialization complete")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}", file=sys.stderr)
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_mission_templates())
