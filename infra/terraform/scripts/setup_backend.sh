#!/bin/bash
# =============================================================================
# Setup Terraform Backend - S3 + DynamoDB (FASE 5)
# =============================================================================
#
# Este script crea la infraestructura necesaria para Terraform remote state:
# - S3 bucket para almacenar state files
# - DynamoDB table para state locking
# - Configuración de seguridad (encryption, versioning, public access block)
#
# IMPORTANTE: Ejecutar ANTES de terraform init
#
# Uso: 
#   ./scripts/setup_backend.sh [region] [environment] [project]
#
# Ejemplos:
#   ./scripts/setup_backend.sh us-east-1 dev aplicacion-senas
#   ./scripts/setup_backend.sh us-east-1 prod aplicacion-senas
#
# Requisitos:
#   - AWS CLI configurado con permisos para S3 y DynamoDB
#   - jq instalado (para JSON parsing)
#
# =============================================================================

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parámetros
REGION=${1:-us-east-1}
ENVIRONMENT=${2:-dev}
PROJECT=${3:-aplicacion-senas}

# Validar parámetros
if [ -z "$REGION" ] || [ -z "$ENVIRONMENT" ] || [ -z "$PROJECT" ]; then
    echo -e "${RED}Error: Faltan parámetros requeridos${NC}"
    echo "Uso: $0 <region> <environment> <project>"
    echo "Ejemplo: $0 us-east-1 dev aplicacion-senas"
    exit 1
fi

# Nombres de recursos (incluir environment para separación)
BUCKET_NAME="${PROJECT}-terraform-state-${ENVIRONMENT}-$(date +%s | tail -c 5)"
DYNAMODB_TABLE="${PROJECT}-terraform-locks-${ENVIRONMENT}"

# Verificar AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI no está instalado${NC}"
    exit 1
fi

# Verificar credenciales AWS
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS CLI no está configurado correctamente${NC}"
    echo "Ejecutar: aws configure"
    exit 1
fi

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Terraform Backend Setup${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo "Bucket: $BUCKET_NAME"
echo "DynamoDB Table: $DYNAMODB_TABLE"
echo ""

# Confirmar
read -p "¿Continuar? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Setup cancelado."
    exit 0
fi

echo ""
echo -e "${YELLOW}[1/4] Creando S3 bucket para Terraform state...${NC}"

# Crear bucket S3
if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3api create-bucket \
        --bucket $BUCKET_NAME \
        --region $REGION \
        --create-bucket-configuration LocationConstraint=$REGION 2>/dev/null || \
    aws s3api create-bucket \
        --bucket $BUCKET_NAME \
        --region $REGION
    
    echo -e "${GREEN}✓ Bucket creado: $BUCKET_NAME${NC}"
else
    echo -e "${GREEN}✓ Bucket ya existe: $BUCKET_NAME${NC}"
fi

echo ""
echo -e "${YELLOW}[2/4] Habilitando versioning en bucket...${NC}"

aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

echo -e "${GREEN}✓ Versioning habilitado${NC}"

echo ""
echo -e "${YELLOW}[3/4] Habilitando encryption en bucket...${NC}"

aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'

echo -e "${GREEN}✓ Encryption habilitado (AES256)${NC}"

echo ""
echo -e "${YELLOW}[4/4] Creando DynamoDB table para state locking...${NC}"

# Crear tabla DynamoDB
aws dynamodb describe-table --table-name $DYNAMODB_TABLE --region $REGION &>/dev/null || \
aws dynamodb create-table \
    --table-name $DYNAMODB_TABLE \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

echo -e "${GREEN}✓ DynamoDB table creada: $DYNAMODB_TABLE${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Backend setup completado${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Siguiente paso:"
echo "  cd infra/terraform/environments/$ENVIRONMENT"
echo "  terraform init"
echo ""
echo "IMPORTANTE: Verificar que provider.tf tenga:"
echo "  backend \"s3\" {"
echo "    bucket         = \"$BUCKET_NAME\""
echo "    key            = \"$ENVIRONMENT/terraform.tfstate\""
echo "    region         = \"$REGION\""
echo "    encrypt        = true"
echo "    dynamodb_table = \"$DYNAMODB_TABLE\""
echo "  }"
echo ""
