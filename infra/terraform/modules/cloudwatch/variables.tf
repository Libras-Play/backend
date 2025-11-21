# =============================================================================
# CloudWatch Module - Variables
# =============================================================================

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# =============================================================================
# ALB Configuration
# =============================================================================

variable "alb_name" {
  description = "Name of the Application Load Balancer"
  type        = string
}

variable "alb_arn_suffix" {
  description = "ARN suffix of the ALB (for CloudWatch dimensions)"
  type        = string
}

variable "target_group_arn_suffix" {
  description = "ARN suffix of the target group"
  type        = string
}

variable "alb_5xx_threshold" {
  description = "Threshold for 5xx errors (count per minute)"
  type        = number
  default     = 10
}

variable "alb_4xx_threshold" {
  description = "Threshold for 4xx errors (count per minute)"
  type        = number
  default     = 50
}

variable "minimum_healthy_hosts" {
  description = "Minimum number of healthy hosts required"
  type        = number
  default     = 2
}

# =============================================================================
# ECS Configuration
# =============================================================================

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "ecs_service_names" {
  description = "List of ECS service names to monitor"
  type        = list(string)
}

variable "minimum_running_tasks" {
  description = "Minimum number of running tasks per service"
  type        = number
  default     = 2
}

# =============================================================================
# RDS Configuration
# =============================================================================

variable "rds_cluster_id" {
  description = "RDS cluster identifier"
  type        = string
}

variable "rds_max_connections" {
  description = "Maximum connections for RDS"
  type        = number
  default     = 100
}

# =============================================================================
# DynamoDB Configuration
# =============================================================================

variable "dynamodb_table_names" {
  description = "List of DynamoDB table names to monitor"
  type        = list(string)
}

# =============================================================================
# CloudWatch Logs Configuration
# =============================================================================

variable "log_group_names" {
  description = "List of CloudWatch Log Group names"
  type        = list(string)
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

# =============================================================================
# Encryption
# =============================================================================

variable "enable_encryption" {
  description = "Enable encryption for SNS topics and logs"
  type        = bool
  default     = true
}

# =============================================================================
# Tags
# =============================================================================

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
