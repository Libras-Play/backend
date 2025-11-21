# Variables for DynamoDB tables

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "user_table_name" {
  description = "Name of the UserData DynamoDB table"
  type        = string
  default     = "UserData"
}

variable "progress_table_name" {
  description = "Name of the UserProgress DynamoDB table"
  type        = string
  default     = "UserProgress"
}

variable "ai_sessions_table_name" {
  description = "Name of the AiSessions DynamoDB table"
  type        = string
  default     = "AiSessions"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
