variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "tables" {
  type = map(object({
    hash_key       = string
    range_key      = string
    billing_mode   = string
    read_capacity  = number
    write_capacity = number
  }))
}

variable "enable_point_in_time_recovery" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
