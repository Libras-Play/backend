#!/usr/bin/env python3
"""
Script para resetear completamente la database de RDS.
CUIDADO: Esto ELIMINA todos los datos.
"""
import asyncio
import os
from sqlalchemy import create_engine, text

async def reset_database():
    # Obtener DATABASE_URL del ambiente
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL no encontrado en variables de entorno")
        return
    
    # Convertir asyncpg URL a psycopg2 para comandos admin
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Extraer componentes
    # postgresql://user:pass@host:port/dbname
    parts = sync_url.split("@")
    credentials = parts[0].replace("postgresql://", "")
    host_db = parts[1]
    host_port = host_db.split("/")[0]
    db_name = host_db.split("/")[1]
    
    # URL a postgres (database por defecto)
    postgres_url = f"postgresql://{credentials}@{host_port}/postgres"
    
    print(f"🗑️  DROP database: {db_name}")
    print(f"📍 Host: {host_port}")
    
    # Conectar a postgres para poder DROP la database
    engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
    
    with engine.connect() as conn:
        # Terminar todas las conexiones a la database
        print("⏹️  Terminando conexiones activas...")
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
              AND pid <> pg_backend_pid()
        """))
        
        # DROP database
        print(f"🗑️  Eliminando database {db_name}...")
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        
        # CREATE database
        print(f"✨ Creando database {db_name} nueva...")
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        
    engine.dispose()
    print("✅ Database reseteada - lista para migraciones Alembic")
    print("")
    print("🔄 Ahora ejecuta: alembic upgrade head")

if __name__ == "__main__":
    asyncio.run(reset_database())
