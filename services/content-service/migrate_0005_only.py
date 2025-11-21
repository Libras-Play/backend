"""
Script para ejecutar SOLO la migración 0005 (dado que 0004 ya se ejecutó)
"""
import asyncio
import sys
from alembic.config import Config
from alembic import command

def run_single_migration():
    """Ejecuta solo la migración 0005"""
    try:
        # Configurar Alembic
        alembic_cfg = Config("alembic.ini")
        
        print("=" * 60)
        print("🔄 Ejecutando SOLO migración 0005...")
        print("=" * 60)
        
        # Mostrar migración actual
        print("\n📋 Estado actual:")
        command.current(alembic_cfg, verbose=True)
        
        # Ejecutar upgrade a head (solo ejecutará las pendientes)
        print("\n⬆️ Aplicando migraciones pendientes...")
        command.upgrade(alembic_cfg, "head")
        
        # Mostrar nuevo estado
        print("\n✅ Migraciones completadas!")
        print("📋 Nuevo estado:")
        command.current(alembic_cfg, verbose=True)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error al ejecutar migraciones: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_single_migration()
    sys.exit(0 if success else 1)
