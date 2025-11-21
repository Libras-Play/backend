# =============================================================================
# Terraform Variables - Global Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------

variable "project_name" {
  description = "Nombre del proyecto (usado en tags y nombres de recursos)"
  type        = string
  default     = "aplicacion-senas"
}

variable "environment" {
  description = "Ambiente de deployment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment debe ser: dev, staging, o prod."
  }
}

variable "owner" {
  description = "Owner del proyecto (para tags)"
  type        = string
  default     = "ERIKO"
}

variable "cost_center" {
  description = "Cost center para billing (para tags)"
  type        = string
  default     = "UNASP"
}

# -----------------------------------------------------------------------------
# AWS Configuration
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region para deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile (solo para desarrollo local)"
  type        = string
  default     = "default"
}

# -----------------------------------------------------------------------------
# VPC Configuration
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block para VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Lista de availability zones para usar"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "enable_nat_gateway" {
  description = "Crear NAT gateway para subnets privadas"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Usar solo 1 NAT gateway (cost saving, no HA)"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# ECS Configuration
# -----------------------------------------------------------------------------

variable "ecs_task_cpu" {
  description = "CPU units para ECS task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 256
}

variable "ecs_task_memory" {
  description = "Memoria para ECS task en MB (512, 1024, 2048, 4096, 8192)"
  type        = number
  default     = 512
}

variable "ecs_desired_count" {
  description = "Número de tasks ECS a ejecutar"
  type        = number
  default     = 1
}

variable "ecs_autoscaling_min" {
  description = "Mínimo número de tasks para autoscaling"
  type        = number
  default     = 1
}

variable "ecs_autoscaling_max" {
  description = "Máximo número de tasks para autoscaling"
  type        = number
  default     = 4
}

variable "container_images" {
  description = "Map de imágenes Docker para cada servicio"
  type        = map(string)
  default = {
    content_service = "aplicacion-senas-content-service:latest"
    user_service    = "aplicacion-senas-user-service:latest"
    ml_service      = "aplicacion-senas-ml-service:latest"
  }
}

# -----------------------------------------------------------------------------
# RDS Aurora Configuration
# -----------------------------------------------------------------------------

variable "rds_instance_class" {
  description = "Instance class para RDS Aurora (db.serverless, db.t4g.medium, etc)"
  type        = string
  default     = "db.serverless"
}

variable "rds_engine_version" {
  description = "Versión de PostgreSQL para Aurora"
  type        = string
  default     = "15.4"
}

variable "rds_database_name" {
  description = "Nombre de la base de datos PostgreSQL"
  type        = string
  default     = "content_db"
}

variable "rds_master_username" {
  description = "Master username para RDS"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "rds_master_password" {
  description = "Master password para RDS (debe estar en Secrets Manager)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "rds_backup_retention_days" {
  description = "Días de retención de backups automáticos"
  type        = number
  default     = 7
}

variable "rds_skip_final_snapshot" {
  description = "Skip final snapshot al eliminar RDS (solo para dev)"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# DynamoDB Configuration
# -----------------------------------------------------------------------------

variable "dynamodb_tables" {
  description = "Map de tablas DynamoDB a crear"
  type = map(object({
    hash_key       = string
    range_key      = string
    billing_mode   = string
    read_capacity  = number
    write_capacity = number
  }))
  default = {
    UserData = {
      hash_key       = "user_id"
      range_key      = ""
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
    UserProgress = {
      hash_key       = "user_id"
      range_key      = "exercise_id"
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
    AiSessions = {
      hash_key       = "session_id"
      range_key      = ""
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
  }
}

# -----------------------------------------------------------------------------
# S3 Configuration
# -----------------------------------------------------------------------------

variable "s3_buckets" {
  description = "Lista de S3 buckets a crear"
  type        = list(string)
  default = [
    "content-assets",
    "user-uploads",
    "ml-models",
    "video-processing"
  ]
}

variable "s3_enable_versioning" {
  description = "Habilitar versioning en buckets S3"
  type        = bool
  default     = true
}

variable "s3_lifecycle_expiration_days" {
  description = "Días antes de expirar objetos antiguos (0 = disabled)"
  type        = number
  default     = 0
}

# -----------------------------------------------------------------------------
# Cognito Configuration
# -----------------------------------------------------------------------------

variable "cognito_user_pool_name" {
  description = "Nombre del Cognito User Pool"
  type        = string
  default     = "aplicacion-senas-users"
}

variable "cognito_password_minimum_length" {
  description = "Longitud mínima de password"
  type        = number
  default     = 8
}

variable "cognito_mfa_configuration" {
  description = "MFA configuration (OFF, ON, OPTIONAL)"
  type        = string
  default     = "OPTIONAL"
}

# -----------------------------------------------------------------------------
# SQS Configuration
# -----------------------------------------------------------------------------

variable "sqs_queues" {
  description = "Map de SQS queues a crear"
  type = map(object({
    visibility_timeout_seconds = number
    message_retention_seconds  = number
    max_message_size           = number
    receive_wait_time_seconds  = number
  }))
  default = {
    video-processing = {
      visibility_timeout_seconds = 300
      message_retention_seconds  = 345600 # 4 days
      max_message_size           = 262144 # 256 KB
      receive_wait_time_seconds  = 20
    }
    ml-inference = {
      visibility_timeout_seconds = 600
      message_retention_seconds  = 345600
      max_message_size           = 262144
      receive_wait_time_seconds  = 20
    }
  }
}

# -----------------------------------------------------------------------------
# SNS Configuration
# -----------------------------------------------------------------------------

variable "sns_topics" {
  description = "Lista de SNS topics a crear"
  type        = list(string)
  default = [
    "achievement-notifications",
    "level-completion",
    "system-alerts"
  ]
}

# -----------------------------------------------------------------------------
# Monitoring & Logging
# -----------------------------------------------------------------------------

variable "enable_cloudwatch_logs" {
  description = "Habilitar CloudWatch Logs para ECS"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Días de retención de logs en CloudWatch"
  type        = number
  default     = 7
}

variable "enable_container_insights" {
  description = "Habilitar Container Insights para ECS"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

variable "allowed_cidr_blocks" {
  description = "CIDR blocks permitidos para acceso a ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"] # CAMBIAR en producción
}

variable "enable_deletion_protection" {
  description = "Habilitar deletion protection en RDS y ALB"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# RDS Configuration
# -----------------------------------------------------------------------------

variable "db_name" {
  description = "Nombre de la base de datos PostgreSQL"
  type        = string
  default     = "content_db"
}

variable "db_master_username" {
  description = "Usuario master de PostgreSQL"
  type        = string
  default     = "postgres"
}

variable "db_min_capacity" {
  description = "Capacidad mínima de Aurora Serverless v2 (ACUs)"
  type        = number
  default     = 0.5
}

variable "db_max_capacity" {
  description = "Capacidad máxima de Aurora Serverless v2 (ACUs)"
  type        = number
  default     = 1.0
}

# -----------------------------------------------------------------------------
# Cost Optimization
# -----------------------------------------------------------------------------

variable "enable_autoscaling" {
  description = "Habilitar autoscaling para ECS"
  type        = bool
  default     = true
}

variable "enable_spot_instances" {
  description = "Usar Fargate Spot para cost saving (no recomendado para prod)"
  type        = bool
  default     = false
}
