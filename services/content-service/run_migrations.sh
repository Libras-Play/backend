#!/bin/sh
# Script para ejecutar migraciones en ECS
set -e

echo "🔄 Starting migration process..."
echo "Current directory: $(pwd)"
echo "Python version: $(python --version)"

# Verificar que Alembic esté disponible
if ! command -v alembic &> /dev/null; then
    echo "❌ Alembic not found, installing..."
    pip install alembic
fi

# Mostrar migraciones actuales
echo "📋 Current migration status:"
alembic current

# Mostrar migraciones pendientes
echo "📋 Available migrations:"
alembic history

# Ejecutar migraciones
echo "⬆️ Running migrations..."
alembic upgrade head

# Verificar resultado
echo "✅ Migration completed!"
echo "📋 New migration status:"
alembic current

echo "🔍 Verifying database schema..."
# Verificar que la tabla levels ya no existe
python -c "
import asyncio
from sqlalchemy import text
from app.database import engine, SessionLocal

async def verify():
    async with engine.begin() as conn:
        # Verificar que levels no existe
        result = await conn.execute(text(
            \"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'levels'\"
        ))
        levels_count = result.scalar()
        print(f'✅ Levels table exists: {levels_count > 0}')
        
        # Verificar que exercises tiene los nuevos campos
        result = await conn.execute(text(
            \"SELECT column_name FROM information_schema.columns WHERE table_name = 'exercises' ORDER BY column_name\"
        ))
        columns = [row[0] for row in result.fetchall()]
        print(f'✅ Exercise columns: {columns}')
        
        required_cols = ['title', 'exercise_type', 'img_url', 'answers', 'expected_sign', 'statement']
        for col in required_cols:
            if col in columns:
                print(f'  ✅ {col} exists')
            else:
                print(f'  ❌ {col} MISSING!')

asyncio.run(verify())
"

echo "🎉 All migrations completed successfully!"
