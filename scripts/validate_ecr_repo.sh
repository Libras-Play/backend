#!/bin/bash
#
# FASE 5: ECR Repository Validation Script
#
# ANTI-ERROR: Prevent pushing to wrong ECR repository
#
# Usage:
#   ./validate_ecr_repo.sh libras-play-dev-user-service
#   Exit code 0 if valid, 1 if invalid
#

set -e

REPO_NAME="$1"

if [ -z "$REPO_NAME" ]; then
    echo "❌ ERROR: Repository name required"
    echo "Usage: $0 <repository-name>"
    exit 1
fi

# Expected pattern for dev environment
DEV_PATTERN="libras-play-dev-.*-service"

if [[ ! "$REPO_NAME" =~ ^$DEV_PATTERN$ ]]; then
    echo "❌ ERROR: Repository name does not match dev pattern"
    echo "   Expected: libras-play-dev-*-service"
    echo "   Got: $REPO_NAME"
    echo ""
    echo "Valid examples:"
    echo "  - libras-play-dev-user-service"
    echo "  - libras-play-dev-content-service"
    echo "  - libras-play-dev-ml-service"
    exit 1
fi

# Check if service name is recognized
SERVICE=$(echo "$REPO_NAME" | sed 's/libras-play-dev-\(.*\)-service/\1/')
VALID_SERVICES=("user" "content" "ml")

if [[ ! " ${VALID_SERVICES[@]} " =~ " ${SERVICE} " ]]; then
    echo "⚠️  WARNING: Service '$SERVICE' not in known list: ${VALID_SERVICES[*]}"
    echo "   Proceeding anyway..."
fi

echo "✅ Repository name valid: $REPO_NAME"
echo "   Service: $SERVICE"
exit 0
