#!/bin/bash
# =============================================================================
# Quick Migration Script - Content Service
# =============================================================================
#
# Script rápido para desarrollo local
# Uso: ./quick_migrate.sh
#
# =============================================================================

set -e

echo "🚀 Quick Migration - Content Service"
echo ""

# Configuración local por defecto
export POSTGRES_USER=${POSTGRES_USER:-postgres}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
export POSTGRES_DB=${POSTGRES_DB:-content_db}
export POSTGRES_HOST=${POSTGRES_HOST:-localhost}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

echo "📊 Database: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
echo ""

# Upgrade migrations
echo "⬆️  Running migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
  echo "✅ Migrations completed"
  echo ""
  echo "Current revision:"
  alembic current
else
  echo "❌ Migration failed"
  exit 1
fi
