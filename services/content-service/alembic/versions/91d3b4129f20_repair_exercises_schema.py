"""repair_exercises_schema

Revision ID: 91d3b4129f20
Revises: fc5e0716f0cc
Create Date: 2025-11-17 02:13:40.996456

MIGRACIÓN DE REPARACIÓN:
Verifica y corrige el schema de exercises si tiene estructura antigua.
Si la tabla tiene level_id en lugar de topic_id, la migra al nuevo schema.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '91d3b4129f20'
down_revision = 'fc5e0716f0cc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Repara el schema de exercises si tiene estructura antigua.
    Verifica si topic_id existe, si no, migra desde level_id.
    """
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Verificar columnas existentes en exercises
    existing_columns = [col['name'] for col in inspector.get_columns('exercises')]
    
    print(f"🔍 Columnas existentes en exercises: {existing_columns}")
    
    # CASO 1: Si tiene level_id pero NO topic_id (schema antiguo)
    if 'level_id' in existing_columns and 'topic_id' not in existing_columns:
        print("⚠️  SCHEMA ANTIGUO DETECTADO - Migrando level_id a topic_id")
        
        # 1. Agregar topic_id temporal
        op.add_column('exercises', sa.Column('topic_id', sa.Integer(), nullable=True))
        
        # 2. Poblar topic_id desde levels.topic_id
        op.execute("""
            UPDATE exercises e
            SET topic_id = l.topic_id
            FROM levels l
            WHERE e.level_id = l.id
        """)
        
        # 3. Hacer topic_id NOT NULL
        op.alter_column('exercises', 'topic_id', nullable=False)
        
        # 4. Crear índice y FK
        op.create_index('ix_exercises_topic_id', 'exercises', ['topic_id'])
        op.create_foreign_key('fk_exercises_topic_id', 'exercises', 'topics', ['topic_id'], ['id'], ondelete='CASCADE')
        
        # 5. Eliminar level_id
        op.drop_constraint('exercises_level_id_fkey', 'exercises', type_='foreignkey')
        op.drop_index('ix_exercises_level_id', 'exercises')
        op.drop_column('exercises', 'level_id')
        
        print("✅ Migración level_id → topic_id completada")
    
    # CASO 2: Si NO tiene topic_id (pero tampoco level_id - caso raro)
    elif 'topic_id' not in existing_columns:
        print("⚠️  FALTA topic_id - Agregando columna")
        
        op.add_column('exercises', sa.Column('topic_id', sa.Integer(), nullable=True))
        
        # Asignar topic por defecto (si existe topic ID 1)
        op.execute("UPDATE exercises SET topic_id = 1 WHERE topic_id IS NULL")
        
        op.alter_column('exercises', 'topic_id', nullable=False)
        op.create_index('ix_exercises_topic_id', 'exercises', ['topic_id'])
        op.create_foreign_key('fk_exercises_topic_id', 'exercises', 'topics', ['topic_id'], ['id'], ondelete='CASCADE')
        
        print("✅ Columna topic_id agregada")
    
    else:
        print("✅ Schema correcto - topic_id ya existe")
    
    # Verificar otros campos críticos
    if 'title' not in existing_columns:
        print("⚠️  Agregando campos faltantes (title, exercise_type, etc.)")
        
        op.add_column('exercises', sa.Column('title', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.add_column('exercises', sa.Column('statement', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        
        # Poblar con valores temporales
        op.execute("""
            UPDATE exercises 
            SET title = '{"es": "Ejercicio", "en": "Exercise", "pt": "Exercício"}'::jsonb,
                statement = '{"es": "Pregunta", "en": "Question", "pt": "Pergunta"}'::jsonb
            WHERE title IS NULL
        """)
        
        op.alter_column('exercises', 'title', nullable=False)
        op.alter_column('exercises', 'statement', nullable=False)
        
        print("✅ Campos multilenguaje agregados")
    
    # Verificar difficulty
    if 'difficulty' not in existing_columns:
        print("⚠️  Agregando difficulty")
        
        # Primero eliminar el enum viejo si existe (BEGINNER/INTERMEDIATE/ADVANCED)
        op.execute("DROP TYPE IF EXISTS difficultylevel CASCADE")
        
        # Crear nuevo enum con valores correctos
        op.execute("CREATE TYPE difficultylevel AS ENUM ('easy', 'medium', 'hard')")
        
        # Agregar columna con el nuevo enum
        op.add_column('exercises', sa.Column('difficulty', 
            sa.Enum('easy', 'medium', 'hard', name='difficultylevel', create_type=False), 
            nullable=True))
        
        op.execute("UPDATE exercises SET difficulty = 'easy' WHERE difficulty IS NULL")
        op.alter_column('exercises', 'difficulty', nullable=False)
        op.create_index('ix_exercises_difficulty', 'exercises', ['difficulty'])
        
        print("✅ Difficulty agregada")
    
    print("🎉 REPARACIÓN COMPLETADA")


def downgrade() -> None:
    """No hay downgrade para esta reparación"""
    pass
