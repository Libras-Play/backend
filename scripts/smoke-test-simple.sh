#!/bin/bash

# 🧪 Production Smoke Test - LibrasPlay AWS
# Version simplificada sin jq para Git Bash

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
ALB="http://libras-play-dev-alb-1450968088.us-east-1.elb.amazonaws.com"
TIMEOUT=10

echo "============================================================================"
echo "🧪 SMOKE TEST - LibrasPlay Production (AWS)"
echo "============================================================================"
echo ""
echo "ALB: $ALB"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Contador de tests
PASSED=0
FAILED=0
TOTAL=0

# Función para test HTTP
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=${4:-}
    local expected_status=${5:-200}
    
    TOTAL=$((TOTAL + 1))
    echo -n "TEST $TOTAL: $name ... "
    
    if [ -z "$data" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url")
    else
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -X $method -H "Content-Type: application/json" -d "$data" "$url")
    fi
    
    if [ "$HTTP_CODE" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $HTTP_CODE)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $HTTP_CODE, expected $expected_status)"
        FAILED=$((FAILED + 1))
    fi
}

# Función para mostrar respuesta
show_response() {
    local name=$1
    local url=$2
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    curl -s --max-time $TIMEOUT "$url" | python -m json.tool 2>/dev/null || curl -s --max-time $TIMEOUT "$url"
    echo ""
    echo ""
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏥 HEALTH CHECKS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "Content Service Health" "$ALB/content/health"
test_endpoint "User Service Health" "$ALB/users/health"
test_endpoint "ML Service Health" "$ALB/ml/health"

show_response "Content Service Response" "$ALB/content/health"
show_response "User Service Response" "$ALB/users/health"
show_response "ML Service Response" "$ALB/ml/health"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 API DOCUMENTATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "Content API Docs" "$ALB/content/api/docs"
test_endpoint "User API Docs" "$ALB/users/api/docs"
test_endpoint "ML API Docs" "$ALB/ml/api/docs"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 ML SERVICE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

test_endpoint "ML Model Info" "$ALB/ml/api/v1/model/info"
show_response "ML Model Info Response" "$ALB/ml/api/v1/model/info"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👤 USER SERVICE - CRUD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Generate unique user ID
USER_ID="smoke-test-$(date +%s)"
USER_EMAIL="smoketest-$(date +%s)@example.com"
USER_DATA="{\"userId\":\"$USER_ID\",\"email\":\"$USER_EMAIL\",\"username\":\"smoketest\",\"preferredLanguage\":\"LSB\"}"

echo "Creating test user: $USER_ID"
test_endpoint "Create User" "$ALB/users/api/v1/users" "POST" "$USER_DATA" "201"

# Si el create fue exitoso, intentar get
if [ $? -eq 0 ]; then
    echo ""
    echo "Getting created user..."
    test_endpoint "Get User" "$ALB/users/api/v1/users/$USER_ID"
    show_response "User Data" "$ALB/users/api/v1/users/$USER_ID"
    
    echo "Updating user progress..."
    PROGRESS_DATA="{\"lessonId\":\"lesson-1\",\"progress\":50,\"completed\":false}"
    test_endpoint "Update Progress" "$ALB/users/api/v1/users/$USER_ID/progress" "POST" "$PROGRESS_DATA"
    
    echo "Adding experience points..."
    XP_DATA="{\"points\":100,\"reason\":\"Completed lesson\"}"
    test_endpoint "Add Experience" "$ALB/users/api/v1/users/$USER_ID/experience" "POST" "$XP_DATA"
    
    echo "Reducing lives..."
    LIVES_DATA="{\"amount\":1,\"reason\":\"Wrong answer\"}"
    test_endpoint "Reduce Lives" "$ALB/users/api/v1/users/$USER_ID/lives/reduce" "POST" "$LIVES_DATA"
    
    echo "Getting user stats..."
    test_endpoint "Get User Stats" "$ALB/users/api/v1/users/$USER_ID/stats"
    show_response "User Stats" "$ALB/users/api/v1/users/$USER_ID/stats"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    exit 1
fi
