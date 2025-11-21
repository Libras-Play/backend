"""force_fix_schema

Revision ID: c95390a6a4e8
Revises: d8b449c8cb72
Create Date: 2025-11-17 03:48:12.813864

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c95390a6a4e8'
down_revision = 'd8b449c8cb72'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fuerza el arreglo del schema usando SQL con manejo de errores"""
    
    # SQL que maneja TODOS los errores posibles
    op.execute("""
    DO $$
    BEGIN
        -- 1. Completar topic_id si existe level_id
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'exercises' AND column_name = 'level_id') THEN
            RAISE NOTICE '⚠️  level_id existe - Completando migración topic_id';
            
            -- Poblar topic_id faltante
            UPDATE exercises e SET topic_id = l.topic_id FROM levels l WHERE e.level_id = l.id AND e.topic_id IS NULL;
            
            -- Hacer topic_id NOT NULL
            ALTER TABLE exercises ALTER COLUMN topic_id SET NOT NULL;
            
            -- Crear índice topic_id (ignorar si existe)
            BEGIN
                CREATE INDEX ix_exercises_topic_id ON exercises(topic_id);
                RAISE NOTICE '✓ Índice ix_exercises_topic_id creado';
            EXCEPTION WHEN duplicate_table THEN
                RAISE NOTICE '✓ Índice ix_exercises_topic_id ya existe';
            END;
            
            -- Crear FK topic_id (ignorar si existe)
            BEGIN
                ALTER TABLE exercises ADD CONSTRAINT fk_exercises_topic_id FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE;
                RAISE NOTICE '✓ FK fk_exercises_topic_id creada';
            EXCEPTION WHEN duplicate_object THEN
                RAISE NOTICE '✓ FK fk_exercises_topic_id ya existe';
            END;
            
            -- Eliminar FK level_id (ignorar si no existe)
            BEGIN
                ALTER TABLE exercises DROP CONSTRAINT exercises_level_id_fkey;
                RAISE NOTICE '✓ FK exercises_level_id_fkey eliminada';
            EXCEPTION WHEN undefined_object THEN
                RAISE NOTICE '✓ FK exercises_level_id_fkey ya no existe';
            END;
            
            -- Eliminar índice level_id (ignorar si no existe)
            BEGIN
                DROP INDEX ix_exercises_level_id;
                RAISE NOTICE '✓ Índice ix_exercises_level_id eliminado';
            EXCEPTION WHEN undefined_object THEN
                RAISE NOTICE '✓ Índice ix_exercises_level_id ya no existe';
            END;
            
            -- Eliminar columna level_id
            ALTER TABLE exercises DROP COLUMN level_id;
            RAISE NOTICE '✅ level_id eliminado completamente';
        ELSE
            RAISE NOTICE '✅ level_id ya no existe - Migración topic_id completa';
        END IF;
        
        -- 2. Arreglar difficulty
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'exercises' AND column_name = 'difficulty') THEN
            RAISE NOTICE '⚠️  Agregando difficulty';
            
            -- DROP enum viejo (ignorar si no existe)
            BEGIN
                DROP TYPE IF EXISTS difficultylevel CASCADE;
                RAISE NOTICE '✓ Enum difficultylevel antiguo eliminado';
            EXCEPTION WHEN undefined_object THEN
                RAISE NOTICE '✓ Enum difficultylevel no existía';
            END;
            
            -- Crear nuevo enum
            CREATE TYPE difficultylevel AS ENUM ('easy', 'medium', 'hard');
            RAISE NOTICE '✓ Enum difficultylevel creado';
            
            -- Agregar columna
            ALTER TABLE exercises ADD COLUMN difficulty difficultylevel;
            RAISE NOTICE '✓ Columna difficulty agregada';
            
            -- Poblar
            UPDATE exercises SET difficulty = 'easy' WHERE difficulty IS NULL;
            
            -- NOT NULL
            ALTER TABLE exercises ALTER COLUMN difficulty SET NOT NULL;
            
            -- Índice
            CREATE INDEX ix_exercises_difficulty ON exercises(difficulty);
            RAISE NOTICE '✅ difficulty completado';
        ELSE
            RAISE NOTICE '✅ difficulty ya existe';
        END IF;
        
        RAISE NOTICE '🎉 MIGRACIÓN 0011 COMPLETADA EXITOSAMENTE';
    END $$;
    """)


def downgrade() -> None:
    pass
