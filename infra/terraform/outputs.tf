# =============================================================================
# Terraform Outputs - Global Infrastructure
# =============================================================================

# -----------------------------------------------------------------------------
# General Information
# -----------------------------------------------------------------------------

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# -----------------------------------------------------------------------------
# VPC Outputs
# -----------------------------------------------------------------------------

output "vpc_id" {
  description = "ID de la VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "CIDR block de la VPC"
  value       = module.vpc.vpc_cidr
}

output "public_subnets" {
  description = "IDs de subnets públicas"
  value       = module.vpc.public_subnets
}

output "private_subnets" {
  description = "IDs de subnets privadas"
  value       = module.vpc.private_subnets
}

output "nat_gateway_ips" {
  description = "IPs públicas de NAT gateways"
  value       = module.vpc.nat_gateway_ips
}

# -----------------------------------------------------------------------------
# ECR Outputs
# -----------------------------------------------------------------------------

output "ecr_repository_urls" {
  description = "URLs de repositorios ECR"
  value = {
    content_service = module.ecr.repository_urls["content-service"]
    user_service    = module.ecr.repository_urls["user-service"]
    ml_service      = module.ecr.repository_urls["ml-service"]
  }
}

output "ecr_repository_arns" {
  description = "ARNs de repositorios ECR"
  value       = module.ecr.repository_arns
}

# -----------------------------------------------------------------------------
# ECS Outputs
# -----------------------------------------------------------------------------

output "ecs_cluster_id" {
  description = "ID del cluster ECS"
  value       = module.ecs_fargate.cluster_id
}

output "ecs_cluster_name" {
  description = "Nombre del cluster ECS"
  value       = module.ecs_fargate.cluster_name
}

output "ecs_service_names" {
  description = "Nombres de los servicios ECS"
  value       = module.ecs_fargate.service_names
}

output "ecs_task_definition_arns" {
  description = "ARNs de task definitions ECS"
  value       = module.ecs_fargate.task_definition_arns
}

# -----------------------------------------------------------------------------
# ALB Outputs
# -----------------------------------------------------------------------------

output "alb_url" {
  description = "URL del Application Load Balancer"
  value       = "http://${module.ecs_fargate.alb_dns_name}"
}

output "alb_dns_name" {
  description = "DNS name del ALB"
  value       = module.ecs_fargate.alb_dns_name
}

output "alb_zone_id" {
  description = "Zone ID del ALB (para Route53)"
  value       = module.ecs_fargate.alb_zone_id
}

output "alb_arn" {
  description = "ARN del ALB"
  value       = module.ecs_fargate.alb_arn
}

# Endpoints de cada servicio
output "service_endpoints" {
  description = "URLs de cada microservicio"
  value = {
    content_service = "http://${module.ecs_fargate.alb_dns_name}/content"
    user_service    = "http://${module.ecs_fargate.alb_dns_name}/users"
    ml_service      = "http://${module.ecs_fargate.alb_dns_name}/ml"
  }
}

# -----------------------------------------------------------------------------
# RDS Aurora Outputs
# -----------------------------------------------------------------------------

output "rds_cluster_endpoint" {
  description = "Endpoint del cluster RDS Aurora (read/write)"
  value       = module.rds_aurora.cluster_endpoint
}

output "rds_reader_endpoint" {
  description = "Endpoint reader del cluster RDS Aurora (read-only)"
  value       = module.rds_aurora.reader_endpoint
}

output "rds_cluster_id" {
  description = "ID del cluster RDS Aurora"
  value       = module.rds_aurora.cluster_id
}

output "rds_database_name" {
  description = "Nombre de la base de datos PostgreSQL"
  value       = module.rds_aurora.database_name
}

output "rds_port" {
  description = "Puerto de PostgreSQL"
  value       = module.rds_aurora.port
}

# IMPORTANTE: NO exportar password aquí
# Password está en AWS Secrets Manager
output "rds_secret_arn" {
  description = "ARN del secret en Secrets Manager con credenciales RDS"
  value       = module.rds_aurora.secret_arn
}

# -----------------------------------------------------------------------------
# DynamoDB Outputs
# -----------------------------------------------------------------------------

output "dynamodb_table_names" {
  description = "Nombres de tablas DynamoDB"
  value       = module.dynamodb.table_names
}

output "dynamodb_table_arns" {
  description = "ARNs de tablas DynamoDB"
  value       = module.dynamodb.table_arns
}

# -----------------------------------------------------------------------------
# S3 Outputs
# -----------------------------------------------------------------------------

output "s3_bucket_names" {
  description = "Nombres de buckets S3"
  value       = module.s3.bucket_names
}

output "s3_bucket_arns" {
  description = "ARNs de buckets S3"
  value       = module.s3.bucket_arns
}

output "s3_bucket_domains" {
  description = "Domain names de buckets S3"
  value       = module.s3.bucket_domains
}

# -----------------------------------------------------------------------------
# Cognito Outputs
# -----------------------------------------------------------------------------

output "cognito_user_pool_id" {
  description = "ID del Cognito User Pool"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_arn" {
  description = "ARN del Cognito User Pool"
  value       = module.cognito.user_pool_arn
}

output "cognito_user_pool_client_id" {
  description = "Client ID del Cognito User Pool"
  value       = module.cognito.user_pool_client_id
  sensitive   = true
}

output "cognito_user_pool_domain" {
  description = "Domain del Cognito User Pool"
  value       = module.cognito.user_pool_domain
}

# -----------------------------------------------------------------------------
# SQS Outputs
# -----------------------------------------------------------------------------

output "sqs_queue_urls" {
  description = "URLs de SQS queues"
  value       = module.sqs.queue_urls
}

output "sqs_queue_arns" {
  description = "ARNs de SQS queues"
  value       = module.sqs.queue_arns
}

# -----------------------------------------------------------------------------
# SNS Outputs
# -----------------------------------------------------------------------------

output "sns_topic_arns" {
  description = "ARNs de SNS topics"
  value       = module.sns.topic_arns
}

# -----------------------------------------------------------------------------
# IAM Outputs
# -----------------------------------------------------------------------------

output "ecs_task_role_arn" {
  description = "ARN del IAM role para ECS tasks"
  value       = module.iam.ecs_task_role_arn
}

output "ecs_execution_role_arn" {
  description = "ARN del IAM role para ECS task execution"
  value       = module.iam.ecs_execution_role_arn
}

# -----------------------------------------------------------------------------
# CloudWatch Outputs
# -----------------------------------------------------------------------------

output "cloudwatch_log_groups" {
  description = "Nombres de CloudWatch Log Groups"
  value       = module.ecs_fargate.log_group_names
}

# -----------------------------------------------------------------------------
# Summary Output (para fácil referencia)
# -----------------------------------------------------------------------------

output "deployment_summary" {
  description = "Resumen de deployment"
  value = {
    environment       = var.environment
    region            = data.aws_region.current.name
    vpc_id            = module.vpc.vpc_id
    alb_url           = "http://${module.ecs_fargate.alb_dns_name}"
    rds_endpoint      = module.rds_aurora.cluster_endpoint
    ecs_cluster       = module.ecs_fargate.cluster_name
    services_deployed = length(module.ecs_fargate.service_names)
  }
}

# -----------------------------------------------------------------------------
# Connection Strings (para configurar servicios)
# -----------------------------------------------------------------------------

output "connection_strings" {
  description = "Connection strings para configurar servicios (NO incluye passwords)"
  value = {
    postgres = "postgresql://${var.rds_master_username}@${module.rds_aurora.cluster_endpoint}:${module.rds_aurora.port}/${module.rds_aurora.database_name}"

    dynamodb_tables = {
      user_data     = module.dynamodb.table_names["UserData"]
      user_progress = module.dynamodb.table_names["UserProgress"]
      ai_sessions   = module.dynamodb.table_names["AiSessions"]
    }

    sqs_queues = {
      video_processing = module.sqs.queue_urls["video-processing"]
      ml_inference     = module.sqs.queue_urls["ml-inference"]
    }

    s3_buckets = {
      content_assets   = module.s3.bucket_names["content-assets"]
      user_uploads     = module.s3.bucket_names["user-uploads"]
      ml_models        = module.s3.bucket_names["ml-models"]
      video_processing = module.s3.bucket_names["video-processing"]
    }
  }
  sensitive = false
}
