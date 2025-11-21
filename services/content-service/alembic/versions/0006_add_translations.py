"""Add multilanguage translations to Topics and Exercises

Revision ID: 0006_add_translations
Revises: 0005_restructure_exercise
Create Date: 2025-11-16 22:00:00.000000

CAMBIOS:
- Topics: name (String) → title (JSONB multilenguaje)
- Topics: description (String) → description (JSONB multilenguaje)
- Exercises: title (String) → title (JSONB multilenguaje)
- Exercises: statement (String/nullable) → statement (JSONB multilenguaje obligatorio)
- Eliminar: exercises.language, exercises.learning_language, exercises.description
- Mantener: Todo lo demás igual que migración 0005

ESTRUCTURA FINAL:
Topic.title = {"es": "...", "en": "...", "pt": "..."}
Topic.description = {"es": "...", "en": "...", "pt": "..."}
Exercise.title = {"es": "...", "en": "...", "pt": "..."}
Exercise.statement = {"es": "...", "en": "...", "pt": "..."}
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0006_add_translations'
down_revision = '0005_restructure_exercise'
branch_labels = None
depends_on = None


def upgrade() -> None:
    print("\n" + "=" * 70)
    print("🌍 INICIANDO MIGRACIÓN 0006: Translations Multilenguaje")
    print("=" * 70 + "\n")
    
    # ========================================================================
    # PASO 1: MIGRAR TOPICS (name → title, description → description JSONB)
    # ========================================================================
    print("📋 PASO 1: Migrando Topics a sistema multilenguaje...\n")
    
    # 1.1: Verificar columnas existentes
    print("   📍 Estado inicial de Topics:")
    print("      - name (String) → se convertirá en title (JSONB)")
    print("      - description (String/nullable) → se convertirá en description (JSONB)\n")
    
    # 1.2: Crear columnas temporales JSONB
    print("   🔧 Creando columnas JSONB temporales...")
    op.add_column('topics', sa.Column('title_temp', postgresql.JSONB(), nullable=True))
    op.add_column('topics', sa.Column('description_temp', postgresql.JSONB(), nullable=True))
    print("      ✅ Columnas temporales creadas\n")
    
    # 1.3: Migrar datos de name → title_temp (3 idiomas con placeholders)
    print("   📊 Migrando datos de 'name' a 'title_temp' (formato JSONB)...")
    op.execute("""
        UPDATE topics 
        SET title_temp = jsonb_build_object(
            'es', name,
            'en', name,
            'pt', name
        )
    """)
    print("      ✅ Datos de 'name' migrados a 'title_temp'\n")
    
    # 1.4: Migrar datos de description → description_temp
    print("   📊 Migrando datos de 'description' a 'description_temp'...")
    op.execute("""
        UPDATE topics 
        SET description_temp = jsonb_build_object(
            'es', COALESCE(description, ''),
            'en', COALESCE(description, ''),
            'pt', COALESCE(description, '')
        )
    """)
    print("      ✅ Datos de 'description' migrados a 'description_temp'\n")
    
    # 1.5: Eliminar columnas antiguas
    print("   🗑️  Eliminando columnas 'name' y 'description' antiguas...")
    op.drop_column('topics', 'name')
    op.drop_column('topics', 'description')
    print("      ✅ Columnas antiguas eliminadas\n")
    
    # 1.6: Renombrar _temp → finales
    print("   🔄 Renombrando columnas temporales...")
    op.alter_column('topics', 'title_temp', new_column_name='title')
    op.alter_column('topics', 'description_temp', new_column_name='description')
    print("      ✅ Renombrado completado\n")
    
    # 1.7: Aplicar NOT NULL
    print("   ✅ Aplicando constraint NOT NULL...")
    op.alter_column('topics', 'title', nullable=False)
    op.alter_column('topics', 'description', nullable=False)
    print("      ✅ Constraints aplicados\n")
    
    print("   ✅ PASO 1 COMPLETADO: Topics ahora son multilenguaje\n")
    
    # ========================================================================
    # PASO 2: MIGRAR EXERCISES
    # ========================================================================
    print("📋 PASO 2: Migrando Exercises a sistema multilenguaje...\n")
    
    # 2.1: Verificar estado actual (después de migración 0005)
    print("   📍 Estado inicial de Exercises (post-0005):")
    print("      - title (String, NOT NULL) → se convertirá en JSONB")
    print("      - statement (String, nullable) → se convertirá en JSONB NOT NULL")
    print("      - description (String, nullable) → SE ELIMINARÁ")
    print("      - language (String) → SE ELIMINARÁ")
    print("      - learning_language (String) → SE ELIMINARÁ\n")
    
    # 2.2: Crear columnas temporales
    print("   🔧 Creando columnas JSONB temporales...")
    op.add_column('exercises', sa.Column('title_temp', postgresql.JSONB(), nullable=True))
    op.add_column('exercises', sa.Column('statement_temp', postgresql.JSONB(), nullable=True))
    print("      ✅ Columnas temporales creadas\n")
    
    # 2.3: Migrar title (String) → title_temp (JSONB)
    print("   📊 Migrando 'title' (String) a 'title_temp' (JSONB)...")
    op.execute("""
        UPDATE exercises 
        SET title_temp = jsonb_build_object(
            'es', title,
            'en', title,
            'pt', title
        )
    """)
    print("      ✅ 'title' migrado a JSONB\n")
    
    # 2.4: Migrar statement con defaults si es null
    print("   📊 Migrando 'statement' (String nullable) a 'statement_temp' (JSONB NOT NULL)...")
    op.execute("""
        UPDATE exercises 
        SET statement_temp = CASE 
            WHEN statement IS NOT NULL AND statement != '' THEN jsonb_build_object(
                'es', statement,
                'en', statement,
                'pt', statement
            )
            ELSE jsonb_build_object(
                'es', CASE 
                    WHEN exercise_type::text = 'test' THEN 'Selecciona la respuesta correcta'
                    WHEN exercise_type::text = 'camera' THEN 'Realiza la seña frente a la cámara'
                    ELSE 'Completa el ejercicio'
                END,
                'en', CASE 
                    WHEN exercise_type::text = 'test' THEN 'Select the correct answer'
                    WHEN exercise_type::text = 'camera' THEN 'Perform the sign in front of the camera'
                    ELSE 'Complete the exercise'
                END,
                'pt', CASE 
                    WHEN exercise_type::text = 'test' THEN 'Selecione a resposta correta'
                    WHEN exercise_type::text = 'camera' THEN 'Realize o sinal em frente à câmera'
                    ELSE 'Complete o exercício'
                END
            )
        END
    """)
    print("      ✅ 'statement' migrado a JSONB con defaults\n")
    
    # 2.5: Eliminar índices primero
    print("   🗑️  Eliminando índices de columnas a eliminar...")
    try:
        op.drop_index('ix_exercises_language', table_name='exercises')
        print("      ✅ Índice ix_exercises_language eliminado")
    except Exception as e:
        print(f"      ⚠️  Índice ix_exercises_language no existe o ya fue eliminado")
    
    try:
        op.drop_index('ix_exercises_learning_language', table_name='exercises')
        print("      ✅ Índice ix_exercises_learning_language eliminado")
    except Exception as e:
        print(f"      ⚠️  Índice ix_exercises_learning_language no existe o ya fue eliminado")
    print()
    
    # 2.6: Eliminar columnas antiguas
    print("   🗑️  Eliminando columnas antiguas...")
    op.drop_column('exercises', 'title')
    print("      ✅ Columna 'title' (String) eliminada")
    
    op.drop_column('exercises', 'statement')
    print("      ✅ Columna 'statement' (String) eliminada")
    
    op.drop_column('exercises', 'language')
    print("      ✅ Columna 'language' eliminada (ya no necesaria)")
    
    op.drop_column('exercises', 'learning_language')
    print("      ✅ Columna 'learning_language' eliminada (ya no necesaria)")
    
    try:
        op.drop_column('exercises', 'description')
        print("      ✅ Columna 'description' eliminada (ya no necesaria)")
    except Exception as e:
        print(f"      ⚠️  Columna 'description' no existe o ya fue eliminada\n")
    
    print()
    
    # 2.7: Renombrar columnas temporales
    print("   🔄 Renombrando columnas temporales...")
    op.alter_column('exercises', 'title_temp', new_column_name='title')
    op.alter_column('exercises', 'statement_temp', new_column_name='statement')
    print("      ✅ Renombrado completado\n")
    
    # 2.8: Aplicar NOT NULL
    print("   ✅ Aplicando constraints NOT NULL...")
    op.alter_column('exercises', 'title', nullable=False)
    op.alter_column('exercises', 'statement', nullable=False)
    print("      ✅ Constraints aplicados\n")
    
    print("   ✅ PASO 2 COMPLETADO: Exercises ahora son multilenguaje\n")
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print("=" * 70)
    print("✅ MIGRACIÓN 0006 COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    print("\n📊 RESUMEN DE CAMBIOS:\n")
    print("   Topics:")
    print("      - name (String) → title (JSONB: {es, en, pt})")
    print("      - description (String) → description (JSONB: {es, en, pt})")
    print()
    print("   Exercises:")
    print("      - title (String) → title (JSONB: {es, en, pt})")
    print("      - statement (String nullable) → statement (JSONB NOT NULL: {es, en, pt})")
    print("      - ❌ language (eliminado - ya no necesario)")
    print("      - ❌ learning_language (eliminado - ya no necesario)")
    print("      - ❌ description (eliminado - ya no necesario)")
    print()
    print("⚠️  NOTA IMPORTANTE:")
    print("   Las traducciones actuales son PLACEHOLDERS (mismo texto en 3 idiomas).")
    print("   Debes actualizar manualmente con traducciones correctas via API o SQL.\n")


def downgrade() -> None:
    """Revertir migración 0006 - restaurar estructura de migración 0005"""
    print("\n" + "=" * 70)
    print("⏪ REVIRTIENDO MIGRACIÓN 0006: Translations")
    print("=" * 70 + "\n")
    
    # ========================================================================
    # REVERTIR EXERCISES
    # ========================================================================
    print("📋 Revirtiendo Exercises...\n")
    
    # Crear columnas String temporales
    print("   � Creando columnas String temporales...")
    op.add_column('exercises', sa.Column('title_old', sa.String(200), nullable=True))
    op.add_column('exercises', sa.Column('statement_old', sa.Text(), nullable=True))
    op.add_column('exercises', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('exercises', sa.Column('language', sa.String(10), nullable=True))
    op.add_column('exercises', sa.Column('learning_language', sa.String(10), nullable=True))
    
    # Extraer español (es) como idioma default
    print("   📊 Extrayendo idioma español como default...")
    op.execute("UPDATE exercises SET title_old = title->>'es'")
    op.execute("UPDATE exercises SET statement_old = statement->>'es'")
    op.execute("UPDATE exercises SET language = 'pt-BR', learning_language = 'LSB'")
    
    # Eliminar columnas JSONB
    print("   🗑️  Eliminando columnas JSONB...")
    op.drop_column('exercises', 'title')
    op.drop_column('exercises', 'statement')
    
    # Renombrar columnas temporales
    print("   🔄 Renombrando columnas...")
    op.alter_column('exercises', 'title_old', new_column_name='title')
    op.alter_column('exercises', 'statement_old', new_column_name='statement')
    
    # Aplicar NOT NULL y recrear índices
    print("   ✅ Aplicando constraints y recreando índices...")
    op.alter_column('exercises', 'title', nullable=False)
    op.alter_column('exercises', 'language', nullable=False)
    op.alter_column('exercises', 'learning_language', nullable=False)
    op.create_index('ix_exercises_language', 'exercises', ['language'])
    op.create_index('ix_exercises_learning_language', 'exercises', ['learning_language'])
    print("      ✅ Exercises revertido\n")
    
    # ========================================================================
    # REVERTIR TOPICS
    # ========================================================================
    print("📋 Revirtiendo Topics...\n")
    
    # Crear columnas String temporales
    print("   🔧 Creando columnas String temporales...")
    op.add_column('topics', sa.Column('name', sa.String(200), nullable=True))
    op.add_column('topics', sa.Column('description_old', sa.Text(), nullable=True))
    
    # Extraer español como default
    print("   📊 Extrayendo idioma español como default...")
    op.execute("UPDATE topics SET name = title->>'es'")
    op.execute("UPDATE topics SET description_old = description->>'es'")
    
    # Eliminar columnas JSONB
    print("   🗑️  Eliminando columnas JSONB...")
    op.drop_column('topics', 'title')
    op.drop_column('topics', 'description')
    
    # Renombrar
    print("   🔄 Renombrando columnas...")
    op.alter_column('topics', 'description_old', new_column_name='description')
    
    # Aplicar NOT NULL
    print("   ✅ Aplicando constraints...")
    op.alter_column('topics', 'name', nullable=False)
    print("      ✅ Topics revertido\n")
    
    print("=" * 70)
    print("✅ MIGRACIÓN 0006 REVERTIDA - Estructura restaurada a post-0005")
    print("=" * 70 + "\n")
