# =============================================================================
# CloudWatch Module - Outputs
# =============================================================================

output "sns_topic_critical_arn" {
  description = "ARN of the critical alarms SNS topic"
  value       = aws_sns_topic.alarms_critical.arn
}

output "sns_topic_warning_arn" {
  description = "ARN of the warning alarms SNS topic"
  value       = aws_sns_topic.alarms_warning.arn
}

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "dashboard_url" {
  description = "URL to access the CloudWatch dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

output "alarm_names" {
  description = "Map of all alarm names by type"
  value = {
    alb = [
      aws_cloudwatch_metric_alarm.alb_high_5xx_errors.alarm_name,
      aws_cloudwatch_metric_alarm.alb_high_4xx_errors.alarm_name,
      aws_cloudwatch_metric_alarm.alb_high_response_time.alarm_name,
      aws_cloudwatch_metric_alarm.alb_unhealthy_hosts.alarm_name,
    ]

    ecs = flatten([
      [for alarm in aws_cloudwatch_metric_alarm.ecs_high_cpu : alarm.alarm_name],
      [for alarm in aws_cloudwatch_metric_alarm.ecs_high_memory : alarm.alarm_name],
      [for alarm in aws_cloudwatch_metric_alarm.ecs_low_running_tasks : alarm.alarm_name],
    ])

    rds = [
      aws_cloudwatch_metric_alarm.rds_high_cpu.alarm_name,
      aws_cloudwatch_metric_alarm.rds_low_memory.alarm_name,
      aws_cloudwatch_metric_alarm.rds_high_connections.alarm_name,
      aws_cloudwatch_metric_alarm.rds_high_read_latency.alarm_name,
    ]

    dynamodb = flatten([
      [for alarm in aws_cloudwatch_metric_alarm.dynamodb_read_throttles : alarm.alarm_name],
      [for alarm in aws_cloudwatch_metric_alarm.dynamodb_write_throttles : alarm.alarm_name],
    ])

    application = [
      for alarm in aws_cloudwatch_metric_alarm.high_application_errors : alarm.alarm_name
    ]
  }
}

output "log_group_arns" {
  description = "ARNs of CloudWatch Log Groups"
  value       = { for k, v in aws_cloudwatch_log_group.retention_policy : k => v.arn }
}

output "kms_key_id_logs" {
  description = "KMS key ID for CloudWatch Logs encryption"
  value       = var.enable_encryption ? aws_kms_key.logs[0].id : null
}

output "kms_key_id_sns" {
  description = "KMS key ID for SNS encryption"
  value       = var.enable_encryption ? aws_kms_key.sns[0].id : null
}
