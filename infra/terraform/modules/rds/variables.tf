variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where RDS will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for RDS subnet group"
  type        = list(string)
}

variable "db_name" {
  description = "Name of the PostgreSQL database"
  type        = string
}

variable "db_master_username" {
  description = "Master username for PostgreSQL"
  type        = string
}

# Note: min_capacity and max_capacity are kept for backward compatibility
# but are not used in db.t3.micro instance
variable "min_capacity" {
  description = "(Unused) Kept for backward compatibility"
  type        = number
  default     = 0.5
}

variable "max_capacity" {
  description = "(Unused) Kept for backward compatibility"
  type        = number
  default     = 1.0
}
