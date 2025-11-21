variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "repository_names" {
  description = "Lista de nombres de repositorios ECR"
  type        = list(string)
  default     = ["content-service", "user-service", "ml-service", "adaptive-service"]
}

variable "image_tag_mutability" {
  description = "Tag mutability (MUTABLE o IMMUTABLE)"
  type        = string
  default     = "MUTABLE"
}

variable "scan_on_push" {
  description = "Escanear imágenes en push"
  type        = bool
  default     = true
}

variable "max_image_count" {
  description = "Número máximo de imágenes a mantener"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags adicionales"
  type        = map(string)
  default     = {}
}
