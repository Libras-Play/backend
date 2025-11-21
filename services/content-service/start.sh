#!/bin/bash
set -e

echo "================================"
echo "FASE 4: Initializing database..."
echo "================================"
python init_db.py || echo "Warning: init_db.py failed (might be OK if already initialized)"

echo ""
echo "================================"
echo "Running database migrations..."
echo "================================"
alembic upgrade head

echo ""
echo "================================"
echo "Starting application..."
echo "================================"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

