#!/bin/bash

##############################################################################
# SIMPLIFIED PRODUCTION ACCEPTANCE TEST
##############################################################################

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

ALB_DNS="libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com"
BASE_URL="http://${ALB_DNS}"
TEST_USER_ID="acceptance-$(date +%s)"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE} PRODUCTION ACCEPTANCE TEST - LibrasPlay AWS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# 1. Crear Usuario
echo -e "${BLUE}✅ 1. Crear Usuario${NC}"
create_response=$(curl -s -X POST "${BASE_URL}/users/api/v1/users" \
  -H 'Content-Type: application/json' \
  -d "{\"userId\":\"${TEST_USER_ID}\",\"username\":\"testuser\",\"email\":\"test@example.com\"}")
echo "Response: $create_response"
echo ""

# 2. Get User
echo -e "${BLUE}✅ 2. Get User (Exportar Progreso)${NC}"
get_response=$(curl -s "${BASE_URL}/users/api/v1/users/${TEST_USER_ID}")
echo "Response: $get_response"
echo ""

# 3. Ganar Experiencia
echo -e "${BLUE}✅ 3. Ganar Experiencia${NC}"
xp_response=$(curl -s -X POST "${BASE_URL}/users/api/v1/users/${TEST_USER_ID}/experience" \
  -H 'Content-Type: application/json' \
  -d '{"amount":150}')
echo "Response: $xp_response"
echo ""

# 4. Reducir Vidas
echo -e "${BLUE}✅ 4. Reducir Vidas${NC}"
lives_response=$(curl -s -X POST "${BASE_URL}/users/api/v1/users/${TEST_USER_ID}/lives/reduce" \
  -H 'Content-Type: application/json' \
  -d '{"amount":1}')
echo "Response: $lives_response"
echo ""

# 5. Get Stats (Exportar Progreso Final)
echo -e "${BLUE}✅ 5. Get Stats (Exportar Progreso Final)${NC}"
stats_response=$(curl -s "${BASE_URL}/users/api/v1/users/${TEST_USER_ID}/stats")
echo "Response: $stats_response"
echo ""

# 6. Llamar a /levels
echo -e "${BLUE}✅ 6. Llamar a /levels (Content Service)${NC}"
levels_response=$(curl -s "${BASE_URL}/content/api/v1/topics/1/levels" -w "\nHTTP_CODE:%{http_code}")
echo "Response: $levels_response"
echo ""

# 7. Llamar a /exercises
echo -e "${BLUE}✅ 7. Llamar a /exercises (Content Service)${NC}"
exercises_response=$(curl -s "${BASE_URL}/content/api/v1/levels/1/exercises" -w "\nHTTP_CODE:%{http_code}")
echo "Response: $exercises_response"
echo ""

# 8. CloudWatch Logs
echo -e "${BLUE}✅ 8. Verificar CloudWatch Logs${NC}"
if command -v aws &> /dev/null; then
    export AWS_PROFILE=libras-play
    echo "Content Service logs:"
    aws logs filter-log-events \
        --log-group-name "/ecs/libras-play-dev/content-service" \
        --start-time $(($(date +%s)-60))000 \
        --region us-east-1 \
        --max-items 2 \
        --query 'events[*].message' \
        --output text 2>&1 | head -3
    echo ""
    echo "User Service logs:"
    aws logs filter-log-events \
        --log-group-name "/ecs/libras-play-dev/user-service" \
        --start-time $(($(date +%s)-60))000 \
        --region us-east-1 \
        --max-items 2 \
        --query 'events[*].message' \
        --output text 2>&1 | head -3
else
    echo "AWS CLI not available"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN} ✅ ACCEPTANCE TEST COMPLETED${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
