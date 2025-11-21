"""Remove Level entity and refactor to simple architecture

Revision ID: 0004_remove_levels
Revises: 0001_initial
Create Date: 2025-11-15 00:00:00.000000

This migration eliminates the Level entity completely from the database,
moving level information to Topic (as embedded JSONB array) and Exercise
(as difficulty string field).

Changes:
- Add 'levels' JSONB column to 'topics' with 3 default levels
- Update 'exercises' to reference 'topic_id' instead of 'level_id'
- Add 'difficulty' column to 'exercises' with values: easy, medium, hard
- Remove 'levels' table completely
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004_remove_levels'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

# Niveles por defecto que se aplicarán a todos los topics
DEFAULT_LEVELS = [
    {"level": "easy", "description": "Nivel básico"},
    {"level": "medium", "description": "Nivel intermedio"},
    {"level": "hard", "description": "Nivel avanzado"}
]

def upgrade():
    """Ejecuta la migración para eliminar la entidad Level"""
    
    print("=" * 60)
    print("🚀 INICIANDO MIGRACIÓN: Eliminar entidad Level")
    print("=" * 60)
    
    # ===========================================================================
    # PASO 1: Migrar datos de levels a exercises
    # ===========================================================================
    
    print("\n📦 PASO 1: Migrando datos de levels a exercises...")
    
    # 1.1 Añadir columnas temporales a exercises
    print("   🔧 Añadiendo columnas temporales...")
    op.add_column('exercises', sa.Column('topic_id_temp', sa.Integer(), nullable=True))
    op.add_column('exercises', sa.Column('difficulty_temp', sa.String(20), nullable=True))
    
    # 1.2 Migrar datos: copiar topic_id desde levels y mapear difficulty
    print("   📊 Copiando datos de levels a exercises...")
    op.execute("""
        UPDATE exercises e
        SET topic_id_temp = l.topic_id,
            difficulty_temp = CASE 
                WHEN l.difficulty::text = 'BEGINNER' THEN 'easy'
                WHEN l.difficulty::text = 'INTERMEDIATE' THEN 'medium'
                WHEN l.difficulty::text = 'ADVANCED' THEN 'hard'
                ELSE 'easy'
            END
        FROM levels l
        WHERE e.level_id = l.id
    """)
    
    print("   ✅ Datos migrados exitosamente")
    
    # ===========================================================================
    # PASO 2: Eliminar foreign keys y constraints de level_id
    # ===========================================================================
    
    print("\n🗑️  PASO 2: Eliminando constraints de level_id...")
    
    try:
        op.drop_constraint('exercises_level_id_fkey', 'exercises', type_='foreignkey')
        print("   ✅ FK exercises_level_id_fkey eliminada")
    except Exception as e:
        print(f"   ⚠️  FK exercises_level_id_fkey no existe: {e}")
    
    try:
        op.drop_index('ix_exercises_level_order', table_name='exercises')
        print("   ✅ Index ix_exercises_level_order eliminado")
    except Exception as e:
        print(f"   ⚠️  Index ix_exercises_level_order no existe: {e}")
    
    # ===========================================================================
    # PASO 3: Eliminar columna level_id de exercises
    # ===========================================================================
    
    print("\n🗑️  PASO 3: Eliminando columna level_id...")
    op.drop_column('exercises', 'level_id')
    print("   ✅ Columna level_id eliminada")
    
    # ===========================================================================
    # PASO 4: Renombrar columnas temporales a definitivas
    # ===========================================================================
    
    print("\n🔄 PASO 4: Renombrando columnas temporales...")
    op.alter_column('exercises', 'topic_id_temp', new_column_name='topic_id')
    op.alter_column('exercises', 'difficulty_temp', new_column_name='difficulty')
    print("   ✅ Columnas renombradas")
    
    # ===========================================================================
    # PASO 5: Aplicar NOT NULL y foreign keys a nuevas columnas
    # ===========================================================================
    
    print("\n✅ PASO 5: Aplicando constraints...")
    
    # Hacer topic_id y difficulty NOT NULL
    op.alter_column('exercises', 'topic_id', nullable=False)
    op.alter_column('exercises', 'difficulty', nullable=False)
    
    # Añadir foreign key a topics
    op.create_foreign_key(
        'exercises_topic_id_fkey', 
        'exercises', 
        'topics', 
        ['topic_id'], 
        ['id']
    )
    print("   ✅ Constraints aplicados")
    
    # ===========================================================================
    # PASO 6: Añadir levels JSONB a topics
    # ===========================================================================
    
    print("\n📝 PASO 6: Añadiendo campo 'levels' a topics...")
    op.add_column('topics', sa.Column('levels', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Insertar los niveles por defecto en todos los topics
    print("   📊 Insertando niveles por defecto...")
    import json
    op.execute(f"""
        UPDATE topics
        SET levels = '{json.dumps(DEFAULT_LEVELS)}'::jsonb
    """)
    
    # Hacer el campo NOT NULL
    op.alter_column('topics', 'levels', nullable=False)
    print("   ✅ Campo 'levels' añadido con datos por defecto")
    
    # ===========================================================================
    # PASO 7: Eliminar tabla levels
    # ===========================================================================
    
    print("\n🗑️  PASO 7: Eliminando tabla 'levels'...")
    op.drop_table('levels')
    print("   ✅ Tabla 'levels' eliminada")
    
    print("\n" + "=" * 60)
    print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    print("\nResumen de cambios:")
    print("  ✅ Tabla 'levels' eliminada")
    print("  ✅ 'exercises.level_id' → 'exercises.topic_id'")
    print("  ✅ 'exercises.difficulty' añadido (easy/medium/hard)")
    print("  ✅ 'topics.levels' añadido con 3 niveles por defecto")
    print("=" * 60)


def downgrade():
    """No se soporta downgrade de esta migración"""
    raise NotImplementedError(
        "No se puede revertir esta migración ya que implica pérdida de datos. "
        "Si necesitas revertir, debes restaurar desde un backup de la base de datos."
    )
