#!/bin/bash
# Script para ejecutar migración 0006 en RDS

echo "🔧 EJECUTANDO MIGRACIÓN 0006 EN RDS..."
echo "======================================"
echo ""

cd /app

# Ejecutar migración
alembic upgrade head

echo ""
echo "✅ MIGRACIÓN COMPLETADA"
