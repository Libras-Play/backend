#!/bin/bash
# ============================================================================
# SMOKE TEST - PRODUCCIÓN
# ============================================================================
# Tests end-to-end de la aplicación Libras Play en AWS
#
# USO: ./smoke-test-production.sh
# ============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ALB_URL="http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com"

echo "============================================================================"
echo "SMOKE TEST - LIBRAS PLAY PRODUCTION"
echo "============================================================================"
echo "ALB: $ALB_URL"
echo ""

# ============================================================================
# TEST 1: HEALTH CHECKS
# ============================================================================
echo -e "${YELLOW}TEST 1: Health Checks${NC}"
echo "-------------------------------------------"

echo -n "Content Service health... "
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/content_health.json $ALB_URL/content/health)
if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/content_health.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/content_health.json
fi
echo ""

echo -n "User Service health... "
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/user_health.json $ALB_URL/users/health)
if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/user_health.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/user_health.json
fi
echo ""

echo -n "ML Service health... "
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/ml_health.json $ALB_URL/ml/health)
if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/ml_health.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/ml_health.json
fi
echo ""

# ============================================================================
# TEST 2: USER SERVICE - CREATE USER
# ============================================================================
echo -e "${YELLOW}TEST 2: Create User${NC}"
echo "-------------------------------------------"

USER_ID="test-user-$(date +%s)"
USER_DATA='{
  "user_id": "'$USER_ID'",
  "email": "test@example.com",
  "full_name": "Test User",
  "preferred_language": "pt-BR"
}'

echo "Creating user: $USER_ID"
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/create_user.json \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$USER_DATA" \
  $ALB_URL/users/api/v1/users)

if [ "$RESPONSE" = "201" ] || [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/create_user.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/create_user.json
fi
echo ""

# ============================================================================
# TEST 3: USER SERVICE - GET USER
# ============================================================================
echo -e "${YELLOW}TEST 3: Get User${NC}"
echo "-------------------------------------------"

echo "Getting user: $USER_ID"
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/get_user.json \
  $ALB_URL/users/api/v1/users/$USER_ID)

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/get_user.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/get_user.json
fi
echo ""

# ============================================================================
# TEST 4: USER SERVICE - UPDATE PROGRESS
# ============================================================================
echo -e "${YELLOW}TEST 4: Update User Progress${NC}"
echo "-------------------------------------------"

PROGRESS_DATA='{
  "exercise_id": "ex_001",
  "level_id": "lv_001",
  "score": 85,
  "time_spent": 120,
  "completed": true
}'

echo "Updating progress for user: $USER_ID"
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/update_progress.json \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$PROGRESS_DATA" \
  $ALB_URL/users/api/v1/users/$USER_ID/progress)

if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "201" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/update_progress.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/update_progress.json
fi
echo ""

# ============================================================================
# TEST 5: USER SERVICE - ADD EXPERIENCE
# ============================================================================
echo -e "${YELLOW}TEST 5: Add Experience Points${NC}"
echo "-------------------------------------------"

echo "Adding 100 XP to user: $USER_ID"
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/add_xp.json \
  -X POST \
  $ALB_URL/users/api/v1/users/$USER_ID/experience?points=100)

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/add_xp.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/add_xp.json
fi
echo ""

# ============================================================================
# TEST 6: USER SERVICE - REDUCE LIVES
# ============================================================================
echo -e "${YELLOW}TEST 6: Reduce Lives${NC}"
echo "-------------------------------------------"

echo "Reducing 1 life from user: $USER_ID"
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/reduce_lives.json \
  -X POST \
  $ALB_URL/users/api/v1/users/$USER_ID/lives/reduce)

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/reduce_lives.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/reduce_lives.json
fi
echo ""

# ============================================================================
# TEST 7: USER SERVICE - GET STATS
# ============================================================================
echo -e "${YELLOW}TEST 7: Get User Stats${NC}"
echo "-------------------------------------------"

echo "Getting stats for user: $USER_ID"
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/get_stats.json \
  $ALB_URL/users/api/v1/users/$USER_ID/stats)

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/get_stats.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/get_stats.json
fi
echo ""

# ============================================================================
# TEST 8: ML SERVICE - MODEL INFO
# ============================================================================
echo -e "${YELLOW}TEST 8: ML Model Info${NC}"
echo "-------------------------------------------"

echo "Getting ML model information..."
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/model_info.json \
  $ALB_URL/ml/api/v1/model/info)

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    cat /tmp/model_info.json | jq .
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
    cat /tmp/model_info.json
fi
echo ""

# ============================================================================
# TEST 9: CONTENT SERVICE - API DOCS
# ============================================================================
echo -e "${YELLOW}TEST 9: API Documentation${NC}"
echo "-------------------------------------------"

echo -n "Content Service OpenAPI... "
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/openapi.json \
  $ALB_URL/content/api/openapi.json)

if [ "$RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $RESPONSE)"
    TITLE=$(cat /tmp/openapi.json | jq -r '.info.title')
    VERSION=$(cat /tmp/openapi.json | jq -r '.info.version')
    echo "API: $TITLE v$VERSION"
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $RESPONSE)"
fi
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "============================================================================"
echo -e "${GREEN}SMOKE TEST COMPLETED${NC}"
echo "============================================================================"
echo "Check CloudWatch Logs for detailed application logs:"
echo "  - /ecs/libras-play-dev/content-service"
echo "  - /ecs/libras-play-dev/user-service"
echo "  - /ecs/libras-play-dev/ml-service"
echo ""
echo "ALB DNS: $ALB_URL"
echo "Swagger UI: $ALB_URL/content/api/docs"
echo "============================================================================"
