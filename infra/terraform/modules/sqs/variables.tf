variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "queues" {
  type = map(object({
    visibility_timeout_seconds = number
    message_retention_seconds  = number
    max_message_size           = number
    receive_wait_time_seconds  = number
  }))
}

variable "enable_dlq" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
