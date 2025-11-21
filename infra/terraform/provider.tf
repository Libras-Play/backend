# =============================================================================
# Terraform Provider Configuration - AWS
# =============================================================================
#
# Configura el provider de AWS con la versión requerida
# Incluye configuración de región, profile, y tags por defecto
#
# =============================================================================

terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70.0"  # Pin to specific minor version for security
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7.2"  # Pin to specific minor version
    }
  }

  # Backend S3 para state remoto
  # IMPORTANTE: No usar credenciales hardcoded aquí
  # Configurar via terraform init -backend-config o environment variables
  # Ver: scripts/setup_backend.sh para configuración completa
  backend "s3" {
    # Valores configurados via backend-config o variables de entorno:
    # - bucket: TF_VAR_backend_bucket o -backend-config="bucket=..."
    # - key: environment-specific (dev/staging/prod)
    # - region: TF_VAR_aws_region
    # - encrypt: true (siempre)
    # - dynamodb_table: para state locking
    # - role_arn: para OIDC authentication en CI/CD
  }
}

# AWS Provider
provider "aws" {
  region = var.aws_region

  # NO usar credenciales hardcoded aquí
  # Prioridad de autenticación:
  # 1. OIDC (CI/CD) - role_arn via assume_role
  # 2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
  # 3. AWS Profile (desarrollo local solamente)
  # 4. IAM instance role (EC2)
  
  # Para CI/CD con OIDC (recomendado):
  # assume_role {
  #   role_arn = var.aws_assume_role_arn
  #   session_name = "terraform-${var.environment}"
  # }
  
  # Para desarrollo local (opcional):
  # profile = var.aws_profile  # Solo si TF_VAR_aws_profile está definido

  # Tags por defecto para todos los recursos
  default_tags {
    tags = {
      Project       = var.project_name
      Environment   = var.environment
      ManagedBy     = "Terraform"
      Repository    = "libras-play"
      Owner         = var.owner
      CostCenter    = var.cost_center
      DeployedBy    = "GitHub-Actions"
      SecurityScan  = "Required"
      BackupPolicy  = var.environment == "production" ? "Required" : "Optional"
    }
  }
}

# Data sources útiles
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}
