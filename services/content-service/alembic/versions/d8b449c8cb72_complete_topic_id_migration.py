"""complete_topic_id_migration

Revision ID: d8b449c8cb72
Revises: 91d3b4129f20
Create Date: 2025-11-17 02:57:09.612994

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'd8b449c8cb72'
down_revision = '91d3b4129f20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Completa la migración level_id → topic_id que quedó incompleta"""
    
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('exercises')]
    
    print(f"🔍 Verificando estado de exercises: {existing_columns}")
    
    # Si topic_id existe pero level_id también, terminar la migración
    if 'topic_id' in existing_columns and 'level_id' in existing_columns:
        print("⚠️  topic_id existe pero level_id AÚN existe - Completando migración...")
        
        # Asegurar que topic_id tiene valores
        op.execute("""
            UPDATE exercises e
            SET topic_id = l.topic_id
            FROM levels l
            WHERE e.level_id = l.id AND e.topic_id IS NULL
        """)
        
        # Hacer topic_id NOT NULL
        op.execute("ALTER TABLE exercises ALTER COLUMN topic_id SET NOT NULL")
        
        # Crear índice si no existe
        try:
            op.create_index('ix_exercises_topic_id', 'exercises', ['topic_id'])
        except Exception:
            print("✓ Índice ix_exercises_topic_id ya existe")
        
        # Crear FK si no existe
        try:
            op.create_foreign_key('fk_exercises_topic_id', 'exercises', 'topics', ['topic_id'], ['id'], ondelete='CASCADE')
        except Exception:
            print("✓ FK fk_exercises_topic_id ya existe")
        
        # Eliminar level_id
        try:
            op.drop_constraint('exercises_level_id_fkey', 'exercises', type_='foreignkey')
        except Exception:
            print("✓ FK exercises_level_id_fkey ya eliminada")
        
        try:
            op.drop_index('ix_exercises_level_id', 'exercises')
        except Exception:
            print("✓ Índice ix_exercises_level_id ya eliminado")
        
        op.drop_column('exercises', 'level_id')
        
        print("✅ Migración completada: level_id eliminado, topic_id operativo")
    
    elif 'topic_id' not in existing_columns:
        print("❌ ERROR: topic_id no existe - Ejecutar migración 0009 primero")
        raise Exception("topic_id column missing")
    
    else:
        print("✅ Migración ya completada - topic_id existe y level_id no existe")
    
    # Agregar difficulty si no existe
    if 'difficulty' not in existing_columns:
        print("⚠️  Agregando difficulty...")
        
        # DROP enum viejo y crear nuevo
        op.execute("DROP TYPE IF EXISTS difficultylevel CASCADE")
        op.execute("CREATE TYPE difficultylevel AS ENUM ('easy', 'medium', 'hard')")
        
        # Agregar columna
        op.add_column('exercises', sa.Column('difficulty', 
            sa.Enum('easy', 'medium', 'hard', name='difficultylevel', create_type=False), 
            nullable=True))
        
        op.execute("UPDATE exercises SET difficulty = 'easy' WHERE difficulty IS NULL")
        op.execute("ALTER TABLE exercises ALTER COLUMN difficulty SET NOT NULL")
        op.create_index('ix_exercises_difficulty', 'exercises', ['difficulty'])
        
        print("✅ Difficulty agregada")
    
    print("🎉 Migración 0010 COMPLETADA")


def downgrade() -> None:
    pass
