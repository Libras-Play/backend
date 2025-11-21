variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "ID de la VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "IDs de subnets públicas para ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "IDs de subnets privadas para ECS tasks"
  type        = list(string)
}

variable "execution_role_arn" {
  description = "ARN del IAM role para ECS task execution"
  type        = string
}

variable "task_role_arn" {
  description = "ARN del IAM role para ECS tasks"
  type        = string
}

variable "services" {
  description = "Map de servicios ECS a crear"
  type = map(object({
    image                = string
    cpu                  = number
    memory               = number
    desired_count        = number
    container_port       = number
    health_check_path    = string
    health_check_command = string
    path_pattern         = string
    priority             = number
    autoscaling_min      = number
    autoscaling_max      = number
    environment          = map(string)
    secrets              = map(string)
  }))
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks permitidos para ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_container_insights" {
  description = "Habilitar Container Insights"
  type        = bool
  default     = true
}

variable "enable_spot_instances" {
  description = "Usar Fargate Spot"
  type        = bool
  default     = false
}

variable "enable_autoscaling" {
  description = "Habilitar autoscaling"
  type        = bool
  default     = true
}

variable "enable_ecs_exec" {
  description = "Habilitar ECS Exec (SSH en containers)"
  type        = bool
  default     = false
}

variable "enable_deletion_protection" {
  description = "Habilitar deletion protection en ALB"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Días de retención de logs"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags adicionales"
  type        = map(string)
  default     = {}
}
