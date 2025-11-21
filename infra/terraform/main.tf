# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  az_count     = 2
}

# IAM Module
module "iam" {
  source = "./modules/iam"
  
  project_name = var.project_name
  environment  = var.environment
}

# ECR Repositories
module "ecr" {
  source = "./modules/ecr"
  
  project_name = var.project_name
  environment  = var.environment
}

# RDS Aurora Serverless
module "rds" {
  source = "./modules/rds"
  
  project_name       = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_name            = var.db_name
  db_master_username = var.db_master_username
  min_capacity       = var.db_min_capacity
  max_capacity       = var.db_max_capacity
}

# DynamoDB Tables
module "dynamodb" {
  source = "./modules/dynamodb"
  
  project_name = var.project_name
  environment  = var.environment
  billing_mode = var.dynamodb_billing_mode
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"
  
  project_name = var.project_name
  environment  = var.environment
  bucket_names = var.s3_buckets
}

# Cognito User Pool
module "cognito" {
  source = "./modules/cognito"
  
  project_name = var.project_name
  environment  = var.environment
}

# ECS Cluster
module "ecs" {
  source = "./modules/ecs"
  
  project_name        = var.project_name
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  public_subnet_ids   = module.vpc.public_subnet_ids
  private_subnet_ids  = module.vpc.private_subnet_ids
  
  # Service images
  content_service_image = var.content_service_image
  user_service_image    = var.user_service_image
  ml_service_image      = var.ml_service_image
  
  # Task configuration
  task_cpu           = var.ecs_task_cpu
  task_memory        = var.ecs_task_memory
  desired_count      = var.ecs_desired_count
  
  # Dependencies
  ecs_task_role_arn      = module.iam.ecs_task_role_arn
  ecs_execution_role_arn = module.iam.ecs_execution_role_arn
  db_secret_arn          = module.rds.db_secret_arn
  
  # Environment variables
  database_url            = module.rds.database_url
  dynamodb_users_table    = module.dynamodb.users_table_name
  dynamodb_progress_table = module.dynamodb.progress_table_name
  s3_content_bucket       = module.s3.content_bucket_name
  s3_ml_models_bucket     = module.s3.ml_models_bucket_name
  cognito_pool_id         = module.cognito.user_pool_id
  cognito_client_id       = module.cognito.user_pool_client_id
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "content_service" {
  name              = "/ecs/${var.project_name}-${var.environment}/content-service"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "user_service" {
  name              = "/ecs/${var.project_name}-${var.environment}/user-service"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "ml_service" {
  name              = "/ecs/${var.project_name}-${var.environment}/ml-service"
  retention_in_days = 7
}
