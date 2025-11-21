#!/bin/bash
# =============================================================================
# Script de Seeding Completo - Multi-Service
# =============================================================================
#
# Ejecuta seeds para content-service y user-service
# Uso: ./seed_all.sh [environment]
#
# Environments:
#   local      - LocalStack/Docker local
#   dev        - Development en AWS
#   staging    - Staging en AWS
#   production - Production en AWS (¡CUIDADO!)
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
echo -e "${BLUE}  Multi-Service Database Seeding${NC}"
echo -e "${BLUE}  Environment: ${ENV}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Confirm production seeding
if [ "$ENV" = "production" ]; then
  echo -e "${RED}⚠ WARNING: You are about to seed PRODUCTION database!${NC}"
  echo ""
  read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Seeding cancelled."
    exit 0
  fi
  echo ""
fi

# =============================================================================
# 1. Run Migrations First
# =============================================================================

echo -e "${YELLOW}[1/4]${NC} Running migrations..."
echo ""

# Run content-service migrations
echo "  Running content-service migrations..."
cd "$(dirname "$0")/.." || exit 1
./scripts/run_migrations.sh ${ENV}

echo -e "${GREEN}✓${NC} Migrations completed"
echo ""

# =============================================================================
# 2. Seed Content Service (PostgreSQL)
# =============================================================================

echo -e "${YELLOW}[2/4]${NC} Seeding content-service..."
echo ""

# Set PostgreSQL environment variables
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
    if [ -f ".env.${ENV}" ]; then
      source ".env.${ENV}"
    else
      echo -e "${RED}Error: .env.${ENV} file not found${NC}"
      exit 1
    fi
    ;;
esac

# Run content seed script
echo "  Executing content seed script..."
python seed_data/seed_content.py

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓${NC} Content-service seeded successfully"
else
  echo -e "${RED}Error: Failed to seed content-service${NC}"
  exit 1
fi
echo ""

# =============================================================================
# 3. Seed User Service (DynamoDB) - Optional
# =============================================================================

echo -e "${YELLOW}[3/4]${NC} Seeding user-service (optional)..."
echo ""

# Check if user-service exists
USER_SERVICE_PATH="../user-service"
if [ -d "$USER_SERVICE_PATH" ]; then
  echo "  Found user-service, seeding demo users..."
  
  # Set AWS/DynamoDB environment variables
  case $ENV in
    local)
      export AWS_REGION=${AWS_REGION:-us-east-1}
      export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-test}
      export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-test}
      export AWS_ENDPOINT_URL=${AWS_ENDPOINT_URL:-http://localhost:4566}
      export DYNAMODB_TABLE_USER_DATA=${DYNAMODB_TABLE_USER_DATA:-UserData}
      ;;
    dev|staging|production)
      if [ -f "$USER_SERVICE_PATH/.env.${ENV}" ]; then
        source "$USER_SERVICE_PATH/.env.${ENV}"
      fi
      ;;
  esac
  
  # Run user seed script
  cd $USER_SERVICE_PATH
  
  if [ -f "scripts/seed_demo_users.py" ]; then
    python scripts/seed_demo_users.py
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}✓${NC} User-service seeded successfully"
    else
      echo -e "${YELLOW}⚠${NC}  Warning: Failed to seed user-service (non-critical)"
    fi
  else
    echo -e "${YELLOW}⚠${NC}  User seed script not found, skipping..."
  fi
  
  cd - > /dev/null
else
  echo -e "${YELLOW}⚠${NC}  User-service not found, skipping..."
fi
echo ""

# =============================================================================
# 4. Verification
# =============================================================================

echo -e "${YELLOW}[4/4]${NC} Verifying seeded data..."
echo ""

# Verify content-service
cd "$(dirname "$0")/.." || exit 1

echo "  Checking content-service data..."

# Count records in each table
languages_count=$(psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM languages;" 2>/dev/null | xargs || echo "0")
topics_count=$(psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM topics;" 2>/dev/null | xargs || echo "0")
levels_count=$(psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM levels;" 2>/dev/null | xargs || echo "0")
exercises_count=$(psql -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t -c "SELECT COUNT(*) FROM exercises;" 2>/dev/null | xargs || echo "0")

echo ""
echo "  Content-service records:"
echo "    Languages:  ${languages_count}"
echo "    Topics:     ${topics_count}"
echo "    Levels:     ${levels_count}"
echo "    Exercises:  ${exercises_count}"
echo ""

if [ "$languages_count" -gt 0 ] && [ "$exercises_count" -gt 0 ]; then
  echo -e "${GREEN}✓${NC} Content-service data verified"
else
  echo -e "${RED}✗${NC} Warning: Content-service has insufficient data"
fi
echo ""

# =============================================================================
# Summary
# =============================================================================

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Seeding completed successfully${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Environment: ${ENV}"
echo ""
echo "Content Service (PostgreSQL):"
echo "  Languages:  ${languages_count}"
echo "  Topics:     ${topics_count}"
echo "  Levels:     ${levels_count}"
echo "  Exercises:  ${exercises_count}"
echo ""
echo "Next steps:"
echo "  1. Start content-service: uvicorn app.main:app --reload --port 8001"
if [ -d "$USER_SERVICE_PATH" ]; then
  echo "  2. Start user-service: uvicorn app.main:app --reload --port 8002"
fi
echo "  3. Verify API: curl http://localhost:8001/health"
echo ""
