#!/bin/bash
# =============================================================================
# Rollback Migration - Content Service
# =============================================================================
#
# Hace rollback de migraciones
# Uso: ./rollback.sh [steps]
#
# Ejemplos:
#   ./rollback.sh         # Rollback 1 step
#   ./rollback.sh 2       # Rollback 2 steps
#   ./rollback.sh base    # Rollback to base (WARNING: drops all tables)
#
# =============================================================================

set -e

STEPS=${1:-1}

echo "⚠️  Rollback Migration - Content Service"
echo ""

if [ "$STEPS" = "base" ]; then
  echo "🚨 WARNING: This will rollback ALL migrations and drop all tables!"
  echo ""
  read -p "Are you sure? Type 'yes' to confirm: " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled."
    exit 0
  fi
  TARGET="base"
else
  TARGET="-${STEPS}"
fi

# Configuración
export POSTGRES_USER=${POSTGRES_USER:-postgres}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
export POSTGRES_DB=${POSTGRES_DB:-content_db}
export POSTGRES_HOST=${POSTGRES_HOST:-localhost}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

echo "Current revision:"
alembic current
echo ""

echo "Rolling back to: ${TARGET}"
alembic downgrade ${TARGET}

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Rollback completed"
  echo ""
  echo "New revision:"
  alembic current
else
  echo "❌ Rollback failed"
  exit 1
fi
