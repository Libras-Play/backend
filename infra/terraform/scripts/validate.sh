#!/bin/bash
# Terraform Validation Script
# Validates all Terraform configurations before applying

set -e

echo "🔍 Terraform Configuration Validator"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Terraform installation
echo "1️⃣  Checking Terraform installation..."
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform not found. Install from https://www.terraform.io/downloads${NC}"
    exit 1
fi
TERRAFORM_VERSION=$(terraform version -json | grep -o '"terraform_version":"[^"]*' | cut -d'"' -f4)
echo -e "${GREEN}✅ Terraform ${TERRAFORM_VERSION} found${NC}"
echo ""

# Check AWS CLI
echo "2️⃣  Checking AWS CLI..."
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Install from https://aws.amazon.com/cli/${NC}"
    exit 1
fi
AWS_VERSION=$(aws --version | awk '{print $1}')
echo -e "${GREEN}✅ ${AWS_VERSION} found${NC}"
echo ""

# Check AWS credentials
echo "3️⃣  Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run 'aws configure'${NC}"
    exit 1
fi
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account: ${AWS_ACCOUNT}${NC}"
echo ""

# Validate module structure
echo "4️⃣  Validating module structure..."
MODULES=("vpc" "ecr" "ecs_fargate" "rds_aurora" "dynamodb" "s3" "cognito" "iam" "sqs" "sns")
MISSING_MODULES=()

for module in "${MODULES[@]}"; do
    if [ ! -d "modules/$module" ]; then
        MISSING_MODULES+=("$module")
    fi
done

if [ ${#MISSING_MODULES[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing modules: ${MISSING_MODULES[*]}${NC}"
    exit 1
fi
echo -e "${GREEN}✅ All 10 modules found${NC}"
echo ""

# Validate module files
echo "5️⃣  Validating module files..."
ERRORS=0

for module in "${MODULES[@]}"; do
    echo "   Checking modules/$module..."
    
    if [ ! -f "modules/$module/main.tf" ]; then
        echo -e "   ${RED}❌ Missing main.tf${NC}"
        ((ERRORS++))
    fi
    
    if [ ! -f "modules/$module/variables.tf" ]; then
        echo -e "   ${RED}❌ Missing variables.tf${NC}"
        ((ERRORS++))
    fi
    
    if [ ! -f "modules/$module/outputs.tf" ]; then
        echo -e "   ${RED}❌ Missing outputs.tf${NC}"
        ((ERRORS++))
    fi
done

if [ $ERRORS -ne 0 ]; then
    echo -e "${RED}❌ Found $ERRORS errors in module files${NC}"
    exit 1
fi
echo -e "${GREEN}✅ All module files present${NC}"
echo ""

# Validate environment configurations
echo "6️⃣  Validating environment configurations..."
ENVS=("dev" "prod")

for env in "${ENVS[@]}"; do
    echo "   Checking environments/$env..."
    
    if [ ! -f "environments/$env/main.tf" ]; then
        echo -e "   ${RED}❌ Missing main.tf${NC}"
        exit 1
    fi
    
    if [ ! -f "environments/$env/outputs.tf" ]; then
        echo -e "   ${RED}❌ Missing outputs.tf${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Environment configurations valid${NC}"
echo ""

# Validate Terraform syntax (dev environment)
echo "7️⃣  Validating Terraform syntax (dev environment)..."
cd environments/dev
if terraform fmt -check -recursive ../../modules > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Code formatting is correct${NC}"
else
    echo -e "${YELLOW}⚠️  Code needs formatting. Run: terraform fmt -recursive${NC}"
fi

if terraform init -backend=false > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Terraform init successful${NC}"
else
    echo -e "${RED}❌ Terraform init failed${NC}"
    exit 1
fi

if terraform validate > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Terraform configuration is valid${NC}"
else
    echo -e "${RED}❌ Terraform validation failed${NC}"
    terraform validate
    exit 1
fi

cd ../..
echo ""

# Check backend configuration
echo "8️⃣  Checking backend configuration..."
if grep -q "aplicacion-senas-terraform-state" environments/dev/main.tf; then
    echo -e "${GREEN}✅ Backend S3 bucket configured${NC}"
else
    echo -e "${RED}❌ Backend S3 bucket not configured${NC}"
    exit 1
fi
echo ""

# Check for sensitive data
echo "9️⃣  Checking for sensitive data..."
if grep -r "aws_access_key_id.*=.*\"[^$]\|aws_secret_access_key.*=.*\"[^$]\|password.*=.*\"[^$]" modules/ environments/ --include="*.tf" | grep -v "variable\|output\|description\|var\.\|local\.\|random_password" > /dev/null; then
    echo -e "${RED}❌ Potential hardcoded credentials found!${NC}"
    grep -r "aws_access_key_id.*=.*\"[^$]\|aws_secret_access_key.*=.*\"[^$]\|password.*=.*\"[^$]" modules/ environments/ --include="*.tf" | grep -v "variable\|output\|description\|var\.\|local\.\|random_password"
    exit 1
fi
echo -e "${GREEN}✅ No hardcoded credentials detected${NC}"
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ ALL VALIDATIONS PASSED${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  1. Setup backend:    ./scripts/setup_backend.sh"
echo "  2. Deploy dev:       cd environments/dev && terraform apply"
echo "  3. Deploy prod:      cd environments/prod && terraform apply"
echo ""
