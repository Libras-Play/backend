#!/usr/bin/env python3
"""
Script para ejecutar la migración 0006 (sistema de traducciones multilenguaje)
Este script debe ejecutarse desde un entorno con acceso a la base de datos RDS.
"""
import sys
from alembic.config import Config
from alembic import command
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_migration():
    """Ejecuta la migración 0006 usando alembic"""
    try:
        logger.info("=" * 80)
        logger.info("Iniciando migración 0006: Sistema de Traducciones Multilenguaje")
        logger.info("=" * 80)
        
        # Configurar Alembic
        alembic_cfg = Config("alembic.ini")
        
        logger.info("\n🚀 Ejecutando migración 0006...")
        logger.info("-" * 80)
        logger.info("PASO 1: Migración de Topics")
        logger.info("  - name (String) → title (JSONB)")
        logger.info("  - description (String) → description (JSONB)")
        logger.info("  - Actualizar levels array con traducciones multilenguaje")
        logger.info("")
        logger.info("PASO 2: Migración de Exercises")
        logger.info("  - title (String) → title (JSONB)")
        logger.info("  - statement (String) → statement (JSONB)")
        logger.info("  - Eliminar: language, learning_language, description")
        logger.info("-" * 80)
        
        # Ejecutar upgrade a head (incluye migración 0006)
        command.upgrade(alembic_cfg, "head")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ MIGRACIÓN 0006 COMPLETADA EXITOSAMENTE")
        logger.info("=" * 80)
        logger.info("\n📋 Cambios aplicados:")
        logger.info("  ✓ Topics: title y description ahora son JSONB multilenguaje")
        logger.info("  ✓ Exercises: title y statement ahora son JSONB multilenguaje")
        logger.info("  ✓ Eliminadas columnas: language, learning_language, description")
        logger.info("  ✓ Niveles actualizados con descripciones en es/en/pt")
        logger.info("")
        logger.info("⚠️  IMPORTANTE: Los datos migrados tienen el mismo texto en los 3 idiomas")
        logger.info("   Será necesario actualizar manualmente las traducciones reales.")
        logger.info("")
        
        return 0
        
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("❌ ERROR DURANTE LA MIGRACIÓN 0006")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.exception(e)
        logger.error("")
        logger.error("Para revertir la migración, ejecutar:")
        logger.error("  alembic downgrade -1")
        logger.error("")
        return 1

def main():
    """Punto de entrada principal"""
    try:
        exit_code = run_migration()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Migración interrumpida por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
