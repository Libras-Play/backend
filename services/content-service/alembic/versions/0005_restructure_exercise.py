"""Restructure Exercise entity completely

Revision ID: 0005_restructure_exercise
Revises: 0004_remove_levels
Create Date: 2025-11-15 10:00:00.000000

Changes to Exercise table:
1. Rename 'type' column to 'exercise_type'
2. Change enum from ('test', 'gesture') to ('test', 'camera')
3. Add 'title' column (VARCHAR 200, NOT NULL)
4. Rename 'image_url' to 'img_url'
5. Add 'description' column (TEXT, nullable)
6. Add 'statement' column (TEXT, nullable) - enunciado personalizado
7. Make 'language' and 'learning_language' NOT NULL
8. Add 'answers' column (JSONB, nullable) - for type='test'
9. Rename 'gesture_label' to 'expected_sign' - for type='camera'
10. Remove 'question_text' and 'correct_answer' columns (ahora en 'answers')
11. Remove 'options' column (ahora en 'answers')
12. Add constraints for type-specific fields
13. Add indexes for language and learning_language
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0005_restructure_exercise'
down_revision = '0004_remove_levels'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Reestructuración completa de la tabla exercises siguiendo especificaciones:
    - exerciseType: 'test' | 'camera'
    - Campos obligatorios: title, img_url, language, learning_language
    - statement opcional (null usa default del frontend)
    - Estructura de respuestas según type
    """
    
    print("=" * 60)
    print("🚀 INICIANDO MIGRACIÓN 0005: Restructure Exercise")
    print("=" * 60)
    
    # ========================================================================
    # PASO 1: Agregar nuevas columnas con valores temporales
    # ========================================================================
    
    print("\n📦 PASO 1: Agregando nuevas columnas...")
    
    # Agregar 'title' (temporal nullable, luego se hará NOT NULL)
    print("   🔧 Agregando columna 'title'...")
    op.add_column('exercises', sa.Column('title', sa.String(200), nullable=True))
    
    # Agregar 'description' (opcional)
    print("   🔧 Agregando columna 'description'...")
    op.add_column('exercises', sa.Column('description', sa.Text(), nullable=True))
    
    # Agregar 'statement' (opcional - enunciado personalizado)
    print("   🔧 Agregando columna 'statement'...")
    op.add_column('exercises', sa.Column('statement', sa.Text(), nullable=True))
    
    # Agregar 'img_url' temporal (copiaremos de image_url)
    print("   🔧 Agregando columna 'img_url'...")
    op.add_column('exercises', sa.Column('img_url', sa.String(500), nullable=True))
    
    # Agregar 'answers' (JSONB para type='test')
    print("   🔧 Agregando columna 'answers' (JSONB)...")
    op.add_column('exercises', sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Agregar 'expected_sign' temporal (copiaremos de gesture_label)
    print("   🔧 Agregando columna 'expected_sign'...")
    op.add_column('exercises', sa.Column('expected_sign', sa.String(100), nullable=True))
    
    # Agregar 'exercise_type' temporal (copiaremos de 'type')
    print("   🔧 Agregando columna 'exercise_type'...")
    op.add_column('exercises', sa.Column('exercise_type', sa.String(20), nullable=True))
    
    # Agregar 'language' (código de idioma UI - ej: 'pt-BR', 'es-ES')
    print("   🔧 Agregando columna 'language'...")
    op.add_column('exercises', sa.Column('language', sa.String(10), nullable=True))
    
    # Agregar 'learning_language' (código de idioma de señas - ej: 'LSB', 'ASL')
    print("   🔧 Agregando columna 'learning_language'...")
    op.add_column('exercises', sa.Column('learning_language', sa.String(10), nullable=True))
    
    print("   ✅ Todas las columnas nuevas agregadas")
    
    # ========================================================================
    # PASO 2: Migrar datos de columnas antiguas a nuevas
    # ========================================================================
    
    print("\n📊 PASO 2: Migrando datos...")
    
    # Copiar image_url -> img_url
    print("   📋 Copiando image_url → img_url...")
    op.execute("UPDATE exercises SET img_url = image_url WHERE image_url IS NOT NULL")
    
    # Copiar gesture_label -> expected_sign
    print("   📋 Copiando gesture_label → expected_sign...")
    op.execute("""
        UPDATE exercises 
        SET expected_sign = COALESCE(gesture_label, 'default_sign')
        WHERE expected_sign IS NULL
    """)
    
    # Copiar type -> exercise_type y cambiar 'gesture' por 'camera'
    print("   📋 Copiando type → exercise_type (gesture → camera)...")
    op.execute("""
        UPDATE exercises 
        SET exercise_type = CASE 
            WHEN UPPER(type::text) = 'GESTURE' THEN 'camera'
            WHEN UPPER(type::text) = 'TEST' THEN 'test'
            ELSE LOWER(type::text)
        END
    """)
    
    # Migrar datos de question_text/correct_answer/options a estructura 'answers' para type='test'
    print("   📋 Construyendo estructura 'answers' para ejercicios tipo test...")
    op.execute("""
        UPDATE exercises 
        SET answers = jsonb_build_object(
            'correct', COALESCE(correct_answer, ''),
            'options', COALESCE(options::jsonb, '[]'::jsonb)
        )
        WHERE UPPER(type::text) = 'TEST'
    """)
    
    # Generar 'title' a partir de question_text (temporal, luego se debe completar manualmente)
    print("   📋 Generando 'title' a partir de question_text...")
    op.execute("""
        UPDATE exercises 
        SET title = COALESCE(
            CASE 
                WHEN question_text IS NOT NULL THEN SUBSTRING(question_text, 1, 200)
                WHEN type::text = 'test' THEN 'Ejercicio de Opción Múltiple'
                WHEN type::text = 'gesture' THEN 'Ejercicio de Cámara'
                ELSE 'Ejercicio'
            END,
            'Ejercicio Sin Título'
        )
    """)
    
    # Si statement es null, dejarlo null (el frontend usará defaults)
    # No hacemos nada, ya es nullable
    
    # Poblar language y learning_language con valores por defecto
    print("   📋 Poblando language y learning_language con valores por defecto...")
    op.execute("""
        UPDATE exercises 
        SET language = 'pt-BR',
            learning_language = 'LSB'
        WHERE language IS NULL OR learning_language IS NULL
    """)
    
    print("   ✅ Migración de datos completada")
    
    # ========================================================================
    # PASO 3: Drop constraints e índices de columnas antiguas
    # ========================================================================
    
    # Drop índice de 'type'
    try:
        op.drop_index('ix_exercises_type', table_name='exercises')
        print("   ✅ Índice ix_exercises_type eliminado")
    except Exception as e:
        print(f"   ⚠️  Índice ix_exercises_type no existe: {e}")
    
    # ========================================================================
    # PASO 4: Drop columnas antiguas Y eliminar enum viejo
    # ========================================================================
    
    print("   🗑️  Eliminando columnas antiguas...")
    op.drop_column('exercises', 'image_url')
    op.drop_column('exercises', 'gesture_label')
    op.drop_column('exercises', 'question_text')
    op.drop_column('exercises', 'correct_answer')
    op.drop_column('exercises', 'options')
    op.drop_column('exercises', 'type')
    
    # Eliminar el enum viejo ahora que no hay columnas usándolo
    print("   🗑️  Eliminando enum 'exercisetype' antiguo...")
    op.execute("DROP TYPE IF EXISTS exercisetype CASCADE")
    print("   ✅ Enum viejo eliminado")
    
    # ========================================================================
    # PASO 5: Crear enum nuevo y aplicar NOT NULL
    # ========================================================================
    
    print("   🔧 Creando enum 'exercisetype' nuevo...")
    # Crear nuevo enum para exercise_type con valores correctos (minúsculas)
    op.execute("CREATE TYPE exercisetype AS ENUM ('test', 'camera')")
    
    # Primero, mapear los valores de mayúsculas a minúsculas
    print("   🔄 Convirtiendo valores a minúsculas...")
    op.execute("""
        UPDATE exercises
        SET exercise_type = LOWER(exercise_type)
    """)
    
    # Cambiar exercise_type de VARCHAR a ENUM
    print("   🔧 Convirtiendo exercise_type a enum...")
    op.execute("ALTER TABLE exercises ALTER COLUMN exercise_type TYPE exercisetype USING exercise_type::exercisetype")
    
    # Hacer columnas NOT NULL
    print("   ✅ Aplicando NOT NULL a campos obligatorios...")
    op.alter_column('exercises', 'title', nullable=False)
    op.alter_column('exercises', 'img_url', nullable=False)
    op.alter_column('exercises', 'language', nullable=False)
    op.alter_column('exercises', 'learning_language', nullable=False)
    op.alter_column('exercises', 'exercise_type', nullable=False)
    
    # ========================================================================
    # PASO 6: Crear nuevos índices
    # ========================================================================
    
    op.create_index('ix_exercises_type', 'exercises', ['exercise_type'])
    op.create_index('ix_exercises_language', 'exercises', ['language'])
    op.create_index('ix_exercises_learning_language', 'exercises', ['learning_language'])
    
    # ========================================================================
    # PASO 7: Agregar constraints de validación
    # ========================================================================
    
    # Constraint: si exercise_type='test', answers debe estar presente
    op.create_check_constraint(
        'check_test_has_answers',
        'exercises',
        "(exercise_type != 'test'::exercisetype) OR (answers IS NOT NULL)"
    )
    
    # Constraint: si exercise_type='camera', expected_sign debe estar presente
    op.create_check_constraint(
        'check_camera_has_expected_sign',
        'exercises',
        "(exercise_type != 'camera'::exercisetype) OR (expected_sign IS NOT NULL)"
    )
    
    print("✅ Migración 0005 completada: Exercise restructurado exitosamente")


def downgrade() -> None:
    """
    No implementado - esta es una migración destructiva.
    Se pierden datos de la estructura antigua.
    """
    raise NotImplementedError("No se puede revertir esta migración - es destructiva")
