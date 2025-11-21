"""
Script para actualizar alembic_version a 0004_remove_levels y luego ejecutar 0005
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from alembic.config import Config
from alembic import command

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL, echo=False)

async def fix_alembic_version():
    """Actualizar alembic_version a 0004_remove_levels"""
    async with engine.begin() as conn:
        print("🔧 Actualizando alembic_version a '0004_remove_levels'...")
        await conn.execute(text(
            "UPDATE alembic_version SET version_num = '0004_remove_levels'"
        ))
        print("✅ alembic_version actualizado")

def run_migration_0005():
    """Ejecutar solo migración 0005"""
    try:
        alembic_cfg = Config("alembic.ini")
        
        print("\n🔄 Ejecutando migración 0005...")
        print("=" * 60)
        
        # Mostrar estado actual
        print("\n📋 Estado actual:")
        command.current(alembic_cfg, verbose=True)
        
        # Ejecutar upgrade
        print("\n⬆️ Aplicando 0005...")
        command.upgrade(alembic_cfg, "head")
        
        # Mostrar nuevo estado
        print("\n✅ Migración completada!")
        command.current(alembic_cfg, verbose=True)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 EJECUTOR DE MIGRACIÓN 0005")
    print("=" * 60)
    
    # Paso 1: Actualizar alembic_version
    asyncio.run(fix_alembic_version())
    
    # Paso 2: Ejecutar migración 0005
    success = run_migration_0005()
    
    exit(0 if success else 1)
