variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "bucket_names" {
  type = list(string)
}

variable "enable_versioning" {
  type    = bool
  default = true
}

variable "lifecycle_expiration_days" {
  type    = number
  default = 0
}

variable "tags" {
  type    = map(string)
  default = {}
}
