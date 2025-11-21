"""
Script para ejecutar la migración 0005 COMPLETA desde 0004
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from alembic.config import Config
from alembic import command
import sys

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL, echo=False)

async def reset_to_0004():
    """Asegurar que alembic_version está en 0004"""
    async with engine.begin() as conn:
        # Verificar versión actual
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        current = result.scalar()
        print(f"📋 Versión actual: {current}")
        
        if current != '0004_remove_levels':
            print("🔧 Actualizando a 0004_remove_levels...")
            await conn.execute(text(
                "UPDATE alembic_version SET version_num = '0004_remove_levels'"
            ))
            print("✅ Actualizado a 0004_remove_levels")
        else:
            print("✅ Ya está en 0004_remove_levels")

def run_migration():
    """Ejecutar migración a head"""
    try:
        alembic_cfg = Config("alembic.ini")
        
        print("\n⬆️ Ejecutando upgrade a head...")
        print("=" * 60)
        command.upgrade(alembic_cfg, "head")
        print("=" * 60)
        
        print("\n✅ Migración completada!")
        command.current(alembic_cfg, verbose=True)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def verify_result():
    """Verificar resultado final"""
    async with engine.begin() as conn:
        print("\n🔍 Verificando resultado...")
        
        # Verificar columnas de exercises
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'exercises' ORDER BY column_name"
        ))
        columns = [row[0] for row in result.fetchall()]
        
        required = ['title', 'exercise_type', 'img_url', 'answers', 'expected_sign', 'language', 'learning_language']
        print("\n📋 Columnas requeridas:")
        for col in required:
            status = "✅" if col in columns else "❌"
            print(f"   {status} {col}")
        
        removed = ['type', 'image_url', 'gesture_label', 'question_text', 'correct_answer', 'options', 'level_id']
        print("\n📋 Columnas que deben estar eliminadas:")
        for col in removed:
            status = "✅" if col not in columns else "❌"
            print(f"   {status} {col}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MIGRACIÓN 0005 COMPLETA")
    print("=" * 60)
    
    # Paso 1: Reset a 0004
    asyncio.run(reset_to_0004())
    
    # Paso 2: Ejecutar upgrade
    success = run_migration()
    
    if success:
        # Paso 3: Verificar
        asyncio.run(verify_result())
        print("\n✅ TODO COMPLETADO")
        sys.exit(0)
    else:
        print("\n❌ FALLÓ")
        sys.exit(1)
