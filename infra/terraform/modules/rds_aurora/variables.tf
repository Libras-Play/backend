variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "database_subnet_ids" {
  type = list(string)
}

variable "allowed_security_group_ids" {
  type = list(string)
}

variable "database_name" {
  type    = string
  default = "content_db"
}

variable "master_username" {
  type    = string
  default = "postgres"
}

variable "master_password" {
  type      = string
  default   = ""
  sensitive = true
}

variable "engine_version" {
  type    = string
  default = "15.4"
}

variable "serverless_min_capacity" {
  type    = number
  default = 0.5
}

variable "serverless_max_capacity" {
  type    = number
  default = 2
}

variable "backup_retention_days" {
  type    = number
  default = 7
}

variable "skip_final_snapshot" {
  type    = bool
  default = false
}

variable "enable_deletion_protection" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
