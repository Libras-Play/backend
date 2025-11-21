variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "password_minimum_length" {
  type    = number
  default = 8
}

variable "mfa_configuration" {
  type    = string
  default = "OPTIONAL"
}

variable "tags" {
  type    = map(string)
  default = {}
}
