"""
Script para ejecutar migraciones de Alembic en RDS
Se debe ejecutar desde un entorno con acceso a RDS (ECS, Bastion, etc.)
"""
import asyncio
import sys
from alembic.config import Config
from alembic import command

def run_migrations():
    """Ejecuta todas las migraciones pendientes"""
    try:
        # Configurar Alembic
        alembic_cfg = Config("alembic.ini")
        
        print("🔄 Ejecutando migraciones...")
        print("=" * 60)
        
        # Mostrar migración actual
        print("\n📋 Estado actual:")
        command.current(alembic_cfg, verbose=True)
        
        # Mostrar historial
        print("\n📋 Historial de migraciones:")
        command.history(alembic_cfg)
        
        # Ejecutar upgrade
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

async def verify_schema():
    """Verifica que los cambios del schema se aplicaron correctamente"""
    from sqlalchemy import text
    from app.database import engine
    
    print("\n🔍 Verificando cambios del schema...")
    print("=" * 60)
    
    try:
        async with engine.begin() as conn:
            # 1. Verificar que tabla levels ya no existe
            result = await conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'levels'"
            ))
            levels_exists = result.scalar() > 0
            
            if levels_exists:
                print("❌ ADVERTENCIA: La tabla 'levels' aún existe!")
            else:
                print("✅ Tabla 'levels' eliminada correctamente")
            
            # 2. Verificar que topics tiene el campo levels (JSONB)
            result = await conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'topics' AND column_name = 'levels'"
            ))
            row = result.fetchone()
            if row:
                print(f"✅ Topics.levels existe (tipo: {row[1]})")
            else:
                print("❌ Topics.levels NO existe!")
            
            # 3. Verificar nuevos campos de Exercise
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'exercises' "
                "ORDER BY column_name"
            ))
            columns = [row[0] for row in result.fetchall()]
            
            print("\n📋 Columnas de 'exercises':")
            print(f"   {', '.join(columns)}")
            
            # Verificar campos nuevos
            new_fields = {
                'title': 'Título del ejercicio',
                'exercise_type': 'Tipo (test/camera)',
                'img_url': 'URL de imagen',
                'answers': 'Respuestas (JSONB)',
                'expected_sign': 'Seña esperada',
                'statement': 'Enunciado'
            }
            
            print("\n🔍 Verificando campos nuevos:")
            for field, desc in new_fields.items():
                if field in columns:
                    print(f"   ✅ {field} - {desc}")
                else:
                    print(f"   ❌ {field} - {desc} (FALTA!)")
            
            # Verificar campos eliminados
            old_fields = ['image_url', 'gesture_label', 'question_text', 'correct_answer', 'options', 'type']
            print("\n🔍 Verificando campos eliminados:")
            for field in old_fields:
                if field not in columns:
                    print(f"   ✅ {field} - eliminado correctamente")
                else:
                    print(f"   ❌ {field} - AÚN EXISTE!")
            
            # 4. Verificar constraints
            result = await conn.execute(text(
                "SELECT constraint_name, constraint_type "
                "FROM information_schema.table_constraints "
                "WHERE table_name = 'exercises'"
            ))
            constraints = result.fetchall()
            print(f"\n📋 Constraints en 'exercises': {len(constraints)}")
            for name, ctype in constraints:
                print(f"   - {name} ({ctype})")
            
            print("\n✅ Verificación del schema completada!")
            
    except Exception as e:
        print(f"\n❌ Error al verificar schema: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 EJECUTOR DE MIGRACIONES - Content Service")
    print("=" * 60)
    
    # Paso 1: Ejecutar migraciones
    success = run_migrations()
    
    if success:
        # Paso 2: Verificar cambios
        asyncio.run(verify_schema())
        print("\n🎉 ¡Proceso completado exitosamente!")
        sys.exit(0)
    else:
        print("\n❌ El proceso falló. Revisa los errores arriba.")
        sys.exit(1)
