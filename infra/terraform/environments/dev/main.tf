# Development Environment Configuration
terraform {
  backend "s3" {
    bucket         = "libras-play-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "libras-play-terraform-locks"
  }
}

provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Project     = "libras-play"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

locals {
  project_name = "libras-play"
  environment  = "dev"
  common_tags = {
    Project     = local.project_name
    Environment = local.environment
  }
}

# VPC
module "vpc" {
  source = "../../modules/vpc"

  project_name       = local.project_name
  environment        = local.environment
  vpc_cidr           = "10.0.0.0/16"
  az_count           = 2
  single_nat_gateway = true
  enable_flow_logs   = false
  tags               = local.common_tags
}

# ECR Repositories
module "ecr" {
  source = "../../modules/ecr"

  project_name     = local.project_name
  environment      = local.environment
  repository_names = ["content-service", "user-service", "ml-service"]
  tags             = local.common_tags
}

# IAM Roles
module "iam" {
  source = "../../modules/iam"

  project_name        = local.project_name
  environment         = local.environment
  s3_bucket_arns      = values(module.s3.bucket_arns)
  dynamodb_table_arns = values(module.dynamodb.table_arns)
  secrets_arns        = []  # Sin RDS, no hay secrets por ahora
  sqs_queue_arns      = concat(values(module.sqs.queue_arns), values(module.sqs.dlq_arns))
  sns_topic_arns      = values(module.sns.topic_arns)
  enable_ecs_exec     = true
  tags                = local.common_tags
}

# RDS Aurora Serverless v2
# NOTA: Aurora Serverless v2 NO está disponible en AWS Free Tier
# Opciones:
# 1. Comentar este módulo y usar PostgreSQL local para desarrollo
# 2. Usar RDS PostgreSQL estándar (t3.micro es free tier por 12 meses)
# 3. Actualizar a cuenta de pago de AWS
#
# Para habilitar RDS PostgreSQL estándar (free tier), crear módulo rds_postgres
# module "rds" {
#   source = "../../modules/rds_postgres"
#   ...
# }

# module "rds" {
#   source = "../../modules/rds_aurora"
#
#   project_name               = local.project_name
#   environment                = local.environment
#   vpc_id                     = module.vpc.vpc_id
#   database_subnet_ids        = module.vpc.database_subnets
#   allowed_security_group_ids = []
#
#   database_name              = "content_db"
#   master_username            = "postgres"
#   serverless_min_capacity    = 0.5
#   serverless_max_capacity    = 1
#   backup_retention_days      = 1  # Free tier: máximo 1 día
#   skip_final_snapshot        = true
#   enable_deletion_protection = false
#
#   tags = local.common_tags
# }

# TEMPORALMENTE: Sin RDS en la nube, usar PostgreSQL local
# Para conectar los servicios a DB local, configurar DATABASE_URL en .env
locals {
  # Dummy RDS outputs para que no falle el resto de la config
  rds_cluster_endpoint = "localhost:5432"
  rds_secret_arn       = "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:your-db-secret"
  rds_security_group_id = ""
}

# DynamoDB Tables
module "dynamodb" {
  source = "../../modules/dynamodb"

  project_name = local.project_name
  environment  = local.environment
  tables = {
    user-data = {
      hash_key       = "user_id"
      range_key      = ""
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
    user-progress = {
      hash_key       = "user_id"
      range_key      = "exercise_id"
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
    user-path-progress = {
      hash_key       = "PK"
      range_key      = "SK"
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
    user-streaks = {
      hash_key       = "PK"
      range_key      = "SK"
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
    ai-sessions = {
      hash_key       = "session_id"
      range_key      = ""
      billing_mode   = "PAY_PER_REQUEST"
      read_capacity  = 0
      write_capacity = 0
    }
  }
  enable_point_in_time_recovery = false
  tags                          = local.common_tags
}

# S3 Buckets
module "s3" {
  source = "../../modules/s3"

  project_name              = local.project_name
  environment               = local.environment
  bucket_names              = ["content-assets", "user-uploads", "ml-models", "video-processing"]
  enable_versioning         = true
  lifecycle_expiration_days = 0
  tags                      = local.common_tags
}

# SQS Queues
module "sqs" {
  source = "../../modules/sqs"

  project_name = local.project_name
  environment  = local.environment
  queues = {
    video-processing = {
      visibility_timeout_seconds = 300
      message_retention_seconds  = 345600
      max_message_size           = 262144
      receive_wait_time_seconds  = 10
    }
    ml-inference = {
      visibility_timeout_seconds = 600
      message_retention_seconds  = 345600
      max_message_size           = 262144
      receive_wait_time_seconds  = 10
    }
  }
  enable_dlq = true
  tags       = local.common_tags
}

# SNS Topics
module "sns" {
  source = "../../modules/sns"

  project_name        = local.project_name
  environment         = local.environment
  topic_names         = ["achievement-notifications", "level-completion", "system-alerts"]
  email_subscriptions = {}
  tags                = local.common_tags
}

# Cognito User Pool
module "cognito" {
  source = "../../modules/cognito"

  project_name            = local.project_name
  environment             = local.environment
  password_minimum_length = 8
  mfa_configuration       = "OPTIONAL"
  tags                    = local.common_tags
}

# ECS Fargate
module "ecs" {
  source = "../../modules/ecs_fargate"

  project_name       = local.project_name
  environment        = local.environment
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnets
  private_subnet_ids = module.vpc.private_subnets

  execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn      = module.iam.ecs_task_role_arn

  services = {
    content-service = {
      image                = "${module.ecr.repository_urls["content-service"]}:latest"
      cpu                  = 256
      memory               = 512
      desired_count        = 1
      container_port       = 8000
      health_check_path    = "/health"
      health_check_command = ""
      path_pattern         = "/content*"
      priority             = 1
      autoscaling_min      = 1
      autoscaling_max      = 2
      environment = {
        DATABASE_URL = "postgresql://postgres@${local.rds_cluster_endpoint}/content_db"
        AWS_REGION   = "us-east-1"
      }
      secrets = {}  # Sin RDS en la nube, configurar DB local
    }
    user-service = {
      image                = "${module.ecr.repository_urls["user-service"]}:latest"
      cpu                  = 256
      memory               = 512
      desired_count        = 1
      container_port       = 8001
      health_check_path    = "/health"
      health_check_command = ""
      path_pattern         = "/users*"
      priority             = 2
      autoscaling_min      = 1
      autoscaling_max      = 2
      environment = {
        DYNAMODB_TABLE = module.dynamodb.table_names["user-data"]
        AWS_REGION     = "us-east-1"
      }
      secrets = {}
    }
    ml-service = {
      image                = "${module.ecr.repository_urls["ml-service"]}:latest"
      cpu                  = 512
      memory               = 1024
      desired_count        = 1
      container_port       = 8002
      health_check_path    = "/health"
      health_check_command = ""
      path_pattern         = "/ml*"
      priority             = 3
      autoscaling_min      = 1
      autoscaling_max      = 3
      environment = {
        SQS_QUEUE_URL = module.sqs.queue_urls["ml-inference"]
        AWS_REGION    = "us-east-1"
      }
      secrets = {}
    }
  }

  allowed_cidr_blocks       = ["0.0.0.0/0"]
  enable_container_insights = false

  tags = local.common_tags
}

# Security Group Rule: Allow ECS tasks to access RDS
# COMENTADO: No hay RDS en este deployment (free tier limitation)
# resource "aws_security_group_rule" "ecs_to_rds" {
#   type                     = "ingress"
#   from_port                = 5432
#   to_port                  = 5432
#   protocol                 = "tcp"
#   security_group_id        = local.rds_security_group_id
#   source_security_group_id = module.ecs.security_group_ids["content-service"]
#   description              = "Allow ECS content-service to access RDS"
# }
