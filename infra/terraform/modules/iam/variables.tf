variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "s3_bucket_arns" {
  description = "ARNs de buckets S3"
  type        = list(string)
  default     = []
}

variable "dynamodb_table_arns" {
  description = "ARNs de tablas DynamoDB"
  type        = list(string)
  default     = []
}

variable "secrets_arns" {
  description = "ARNs de secrets en Secrets Manager"
  type        = list(string)
  default     = []
}

variable "sqs_queue_arns" {
  description = "ARNs de SQS queues"
  type        = list(string)
  default     = []
}

variable "sns_topic_arns" {
  description = "ARNs de SNS topics"
  type        = list(string)
  default     = []
}

variable "sagemaker_endpoint_arns" {
  description = "ARNs de SageMaker endpoints"
  type        = list(string)
  default     = []
}

variable "enable_ecs_exec" {
  description = "Habilitar ECS Exec (debugging)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags adicionales"
  type        = map(string)
  default     = {}
}
