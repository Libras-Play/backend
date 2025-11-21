# =============================================================================
# VPC Module - Variables
# =============================================================================

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block para VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Número de Availability Zones a usar"
  type        = number
  default     = 3
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

variable "enable_flow_logs" {
  description = "Habilitar VPC Flow Logs"
  type        = bool
  default     = false
}

variable "flow_logs_retention_days" {
  description = "Días de retención para Flow Logs"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags adicionales"
  type        = map(string)
  default     = {}
}
