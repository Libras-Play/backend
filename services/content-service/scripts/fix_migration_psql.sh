#!/bin/bash

# Script para reparar migración 0009 usando psql
# Se conecta a RDS y ejecuta SQL directamente

set -e

echo "================================================================================"
echo "🔧 REPARANDO MIGRACIÓN 0009 CON PSQL"
echo "================================================================================"

# Extraer credenciales del DATABASE_URL
DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
DB_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

export PGPASSWORD="$DB_PASS"

echo "1️⃣ Verificando estado actual..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT column_name FROM information_schema.columns WHERE table_name='exercises' ORDER BY ordinal_position;"

echo ""
echo "2️⃣ Completando migración level_id → topic_id..."

# Poblar topic_id
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "UPDATE exercises e SET topic_id = l.topic_id FROM levels l WHERE e.level_id = l.id AND e.topic_id IS NULL;"

# Hacer NOT NULL
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ALTER TABLE exercises ALTER COLUMN topic_id SET NOT NULL;"

# Crear índice
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE INDEX IF NOT EXISTS ix_exercises_topic_id ON exercises(topic_id);"

# Crear FK
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ALTER TABLE exercises ADD CONSTRAINT IF NOT EXISTS fk_exercises_topic_id FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE;" 2>/dev/null || echo "FK ya existe"

# Eliminar level_id constraints
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ALTER TABLE exercises DROP CONSTRAINT IF EXISTS exercises_level_id_fkey;"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DROP INDEX IF EXISTS ix_exercises_level_id;"

# Eliminar columna level_id
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ALTER TABLE exercises DROP COLUMN IF EXISTS level_id;"

echo "✅ Migración topic_id completada"

echo ""
echo "3️⃣ Arreglando difficulty enum..."

# DROP enum viejo
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "DROP TYPE IF EXISTS difficultylevel CASCADE;"

# Crear nuevo enum
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE TYPE difficultylevel AS ENUM ('easy', 'medium', 'hard');"

# Agregar columna
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ALTER TABLE exercises ADD COLUMN IF NOT EXISTS difficulty difficultylevel;"

# Poblar
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "UPDATE exercises SET difficulty = 'easy' WHERE difficulty IS NULL;"

# Hacer NOT NULL
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ALTER TABLE exercises ALTER COLUMN difficulty SET NOT NULL;"

# Crear índice
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE INDEX IF NOT EXISTS ix_exercises_difficulty ON exercises(difficulty);"

echo "✅ difficulty completado"

echo ""
echo "4️⃣ Verificando estado final..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='exercises' ORDER BY ordinal_position;"

echo ""
echo "================================================================================"
echo "✅ REPARACIÓN COMPLETADA EXITOSAMENTE"
echo "================================================================================"
