#!/bin/bash
# =============================================================================
# Script de Migraciones para CI/CD - Content Service
# =============================================================================
# 
# Ejecuta migraciones de Alembic en PostgreSQL
# Uso: ./run_migrations.sh [environment]
#
# Environments:
#   local      - LocalStack/Docker local
#   dev        - Development en AWS
#   staging    - Staging en AWS
#   production - Production en AWS
#
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Environment
ENV=${1:-local}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Content Service - Database Migrations${NC}"
echo -e "${BLUE}  Environment: ${ENV}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# =============================================================================
# 1. Set Environment Variables
# =============================================================================

echo -e "${YELLOW}[1/5]${NC} Setting environment variables..."

case $ENV in
  local)
    export POSTGRES_USER=${POSTGRES_USER:-postgres}
    export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
    export POSTGRES_DB=${POSTGRES_DB:-content_db}
    export POSTGRES_HOST=${POSTGRES_HOST:-localhost}
    export POSTGRES_PORT=${POSTGRES_PORT:-5432}
    export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
    ;;
  dev|staging|production)
    # Load from .env file or AWS Parameter Store
    if [ -f ".env.${ENV}" ]; then
      source ".env.${ENV}"
    else
      echo -e "${RED}Error: .env.${ENV} file not found${NC}"
      exit 1
    fi
    ;;
  *)
    echo -e "${RED}Error: Unknown environment: ${ENV}${NC}"
    echo "Valid environments: local, dev, staging, production"
    exit 1
    ;;
esac

echo -e "${GREEN}✓${NC} Environment variables set"
echo "  Database: ${POSTGRES_DB}"
echo "  Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo ""

# =============================================================================
# 2. Wait for PostgreSQL to be ready
# =============================================================================

echo -e "${YELLOW}[2/5]${NC} Waiting for PostgreSQL..."

max_retries=30
retry_count=0

while ! pg_isready -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} > /dev/null 2>&1; do
  retry_count=$((retry_count + 1))
  if [ $retry_count -ge $max_retries ]; then
    echo -e "${RED}Error: PostgreSQL not ready after ${max_retries} attempts${NC}"
    exit 1
  fi
  echo "  Waiting for PostgreSQL... (attempt $retry_count/$max_retries)"
  sleep 2
done

echo -e "${GREEN}✓${NC} PostgreSQL is ready"
echo ""

# =============================================================================
# 3. Check database exists
# =============================================================================

echo -e "${YELLOW}[3/5]${NC} Checking database..."

# Try to connect
if psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -lqt | cut -d \| -f 1 | grep -qw ${POSTGRES_DB}; then
  echo -e "${GREEN}✓${NC} Database '${POSTGRES_DB}' exists"
else
  echo -e "${YELLOW}⚠${NC}  Database '${POSTGRES_DB}' does not exist, creating..."
  createdb -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} ${POSTGRES_DB}
  echo -e "${GREEN}✓${NC} Database '${POSTGRES_DB}' created"
fi
echo ""

# =============================================================================
# 4. Run Alembic migrations
# =============================================================================

echo -e "${YELLOW}[4/5]${NC} Running Alembic migrations..."

# Check current revision
echo "  Checking current database revision..."
current_revision=$(alembic current 2>&1 | grep -oP '(?<=\(head\)|^)[a-z0-9]+' || echo "none")
echo "  Current revision: ${current_revision}"

# Check target revision
target_revision=$(alembic heads 2>&1 | grep -oP '^[a-z0-9]+' || echo "unknown")
echo "  Target revision: ${target_revision}"

if [ "$current_revision" = "$target_revision" ] && [ "$current_revision" != "none" ]; then
  echo -e "${GREEN}✓${NC} Database is already up to date"
else
  # Run migrations
  echo "  Applying migrations..."
  alembic upgrade head
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Migrations applied successfully"
  else
    echo -e "${RED}Error: Failed to apply migrations${NC}"
    exit 1
  fi
fi
echo ""

# =============================================================================
# 5. Verify migrations
# =============================================================================

echo -e "${YELLOW}[5/5]${NC} Verifying migrations..."

# Check if all tables exist
tables_to_check=("languages" "topics" "levels" "exercises" "signs" "translations" "achievements")
missing_tables=()

for table in "${tables_to_check[@]}"; do
  if psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "\dt ${table}" | grep -q ${table}; then
    echo -e "  ${GREEN}✓${NC} Table '${table}' exists"
  else
    echo -e "  ${RED}✗${NC} Table '${table}' missing"
    missing_tables+=("$table")
  fi
done

if [ ${#missing_tables[@]} -eq 0 ]; then
  echo -e "${GREEN}✓${NC} All tables verified successfully"
else
  echo -e "${RED}Error: ${#missing_tables[@]} tables missing${NC}"
  exit 1
fi
echo ""

# =============================================================================
# Summary
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Migrations completed successfully${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Database: ${POSTGRES_DB}"
echo "Revision: ${target_revision}"
echo "Tables: ${#tables_to_check[@]} verified"
echo ""
echo "Next steps:"
echo "  1. Run seed script: ./scripts/seed_all.sh ${ENV}"
echo "  2. Start service: uvicorn app.main:app --reload"
echo ""
