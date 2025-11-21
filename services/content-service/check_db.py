"""
Script para verificar el estado actual de la base de datos antes de las migraciones
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Crear engine directamente desde DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("❌ DATABASE_URL no está configurada")
    exit(1)

engine = create_async_engine(DATABASE_URL, echo=False)

async def check_database_state():
    """Verifica el estado actual de la base de datos"""
    print("=" * 60)
    print("🔍 VERIFICANDO ESTADO DE LA BASE DE DATOS")
    print("=" * 60)
    
    async with engine.begin() as conn:
        # 1. Verificar si existe tabla levels
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'levels'"
        ))
        levels_exists = result.scalar() > 0
        print(f"\n📋 Tabla 'levels' existe: {levels_exists}")
        
        if levels_exists:
            result = await conn.execute(text("SELECT COUNT(*) FROM levels"))
            count = result.scalar()
            print(f"   - Registros en levels: {count}")
            
            result = await conn.execute(text(
                "SELECT DISTINCT difficulty FROM levels ORDER BY difficulty"
            ))
            difficulties = [row[0] for row in result.fetchall()]
            print(f"   - Valores de difficulty: {difficulties}")
        
        # 2. Verificar enum types
        result = await conn.execute(text(
            "SELECT t.typname, e.enumlabel "
            "FROM pg_type t "
            "JOIN pg_enum e ON t.oid = e.enumtypid "
            "WHERE t.typname IN ('difficultylevel', 'exercisetype') "
            "ORDER BY t.typname, e.enumsortorder"
        ))
        enums = {}
        for typename, enumlabel in result.fetchall():
            if typename not in enums:
                enums[typename] = []
            enums[typename].append(enumlabel)
        
        print(f"\n📋 Enums existentes:")
        for typename, labels in enums.items():
            print(f"   - {typename}: {labels}")
        
        # 3. Verificar columnas de exercises
        result = await conn.execute(text(
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_name = 'exercises' "
            "ORDER BY column_name"
        ))
        print(f"\n📋 Columnas de 'exercises':")
        for col_name, data_type, is_nullable in result.fetchall():
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            print(f"   - {col_name}: {data_type} ({nullable})")
        
        # 4. Verificar migración actual
        result = await conn.execute(text(
            "SELECT version_num FROM alembic_version"
        ))
        version = result.scalar()
        print(f"\n📋 Versión de migración actual: {version}")
        
        # 5. Verificar si exercises tiene level_id
        result = await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'exercises' AND column_name = 'level_id'"
        ))
        has_level_id = result.scalar() > 0
        print(f"\n📋 exercises tiene level_id: {has_level_id}")
        
        if has_level_id:
            result = await conn.execute(text("SELECT COUNT(*) FROM exercises"))
            count = result.scalar()
            print(f"   - Registros en exercises: {count}")

if __name__ == "__main__":
    asyncio.run(check_database_state())
