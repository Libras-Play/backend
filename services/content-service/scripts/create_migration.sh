#!/bin/bash
# =============================================================================
# Create New Migration - Content Service
# =============================================================================
#
# Crea una nueva migración con Alembic autogenerate
# Uso: ./create_migration.sh "descripcion de la migracion"
#
# Ejemplo: ./create_migration.sh "add user preferences table"
#
# =============================================================================

set -e

if [ -z "$1" ]; then
  echo "❌ Error: Migration message required"
  echo ""
  echo "Usage: ./create_migration.sh \"migration message\""
  echo "Example: ./create_migration.sh \"add user preferences table\""
  exit 1
fi

MESSAGE="$1"

echo "🔧 Creating new migration: ${MESSAGE}"
echo ""

# Configuración
export POSTGRES_USER=${POSTGRES_USER:-postgres}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
export POSTGRES_DB=${POSTGRES_DB:-content_db}
export POSTGRES_HOST=${POSTGRES_HOST:-localhost}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# Create migration
alembic revision --autogenerate -m "${MESSAGE}"

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Migration created successfully"
  echo ""
  echo "Next steps:"
  echo "  1. Review the generated migration file in alembic/versions/"
  echo "  2. Edit if needed (autogenerate may not catch everything)"
  echo "  3. Run: alembic upgrade head"
else
  echo "❌ Failed to create migration"
  exit 1
fi
