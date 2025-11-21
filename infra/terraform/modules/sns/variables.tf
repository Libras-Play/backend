variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "topic_names" {
  type = list(string)
}

variable "email_subscriptions" {
  type    = map(string)
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}
