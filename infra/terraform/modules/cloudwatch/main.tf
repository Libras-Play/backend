# =============================================================================
# CloudWatch Monitoring Module - Main Configuration
# =============================================================================
# Configuración de alarmas, dashboards y métricas custom para monitoreo
# completo de la aplicación.
# =============================================================================

locals {
  name = "${var.project_name}-${var.environment}"

  # Prefijo para recursos de CloudWatch
  alarm_prefix = "${local.name}-alarm"

  # Tags comunes
  common_tags = merge(
    var.tags,
    {
      Module      = "cloudwatch"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# =============================================================================
# SNS Topics for Alarms
# =============================================================================

resource "aws_sns_topic" "alarms_critical" {
  name              = "${local.name}-alarms-critical"
  display_name      = "Critical Alarms - ${var.project_name}"
  kms_master_key_id = var.enable_encryption ? aws_kms_key.sns[0].id : null

  tags = merge(
    local.common_tags,
    {
      Name     = "${local.name}-alarms-critical"
      Severity = "critical"
    }
  )
}

resource "aws_sns_topic" "alarms_warning" {
  name              = "${local.name}-alarms-warning"
  display_name      = "Warning Alarms - ${var.project_name}"
  kms_master_key_id = var.enable_encryption ? aws_kms_key.sns[0].id : null

  tags = merge(
    local.common_tags,
    {
      Name     = "${local.name}-alarms-warning"
      Severity = "warning"
    }
  )
}

# KMS Key for SNS encryption (optional)
resource "aws_kms_key" "sns" {
  count = var.enable_encryption ? 1 : 0

  description             = "KMS key for SNS topic encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-sns-kms" }
  )
}

resource "aws_kms_alias" "sns" {
  count = var.enable_encryption ? 1 : 0

  name          = "alias/${local.name}-sns"
  target_key_id = aws_kms_key.sns[0].key_id
}

# =============================================================================
# ALB Alarms - Application Load Balancer
# =============================================================================

# Alarm: High 5xx error rate (> 1%)
resource "aws_cloudwatch_metric_alarm" "alb_high_5xx_errors" {
  alarm_name          = "${local.alarm_prefix}-alb-high-5xx-errors"
  alarm_description   = "ALB 5xx error rate exceeds 1% for 5 consecutive minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60 # 1 minute
  statistic           = "Sum"
  threshold           = var.alb_5xx_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.alarms_critical.arn]
  ok_actions    = [aws_sns_topic.alarms_critical.arn]

  tags = local.common_tags
}

# Alarm: High 4xx error rate (> 5%)
resource "aws_cloudwatch_metric_alarm" "alb_high_4xx_errors" {
  alarm_name          = "${local.alarm_prefix}-alb-high-4xx-errors"
  alarm_description   = "ALB 4xx error rate exceeds 5% for 10 minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 10
  metric_name         = "HTTPCode_Target_4XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = var.alb_4xx_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# Alarm: High response time (p95 > 2s)
resource "aws_cloudwatch_metric_alarm" "alb_high_response_time" {
  alarm_name          = "${local.alarm_prefix}-alb-high-response-time"
  alarm_description   = "ALB p95 response time exceeds 2 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5

  metric_query {
    id          = "e1"
    expression  = "m1 / 1000" # Convert ms to seconds
    label       = "Target Response Time (s)"
    return_data = true
  }

  metric_query {
    id = "m1"

    metric {
      metric_name = "TargetResponseTime"
      namespace   = "AWS/ApplicationELB"
      period      = 60
      stat        = "p95"

      dimensions = {
        LoadBalancer = var.alb_arn_suffix
      }
    }
  }

  threshold          = 2 # 2 seconds
  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# Alarm: Low healthy host count
resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  alarm_name          = "${local.alarm_prefix}-alb-unhealthy-hosts"
  alarm_description   = "Less than ${var.minimum_healthy_hosts} healthy hosts in target group"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = var.minimum_healthy_hosts
  treat_missing_data  = "breaching"

  dimensions = {
    TargetGroup  = var.target_group_arn_suffix
    LoadBalancer = var.alb_arn_suffix
  }

  alarm_actions = [aws_sns_topic.alarms_critical.arn]

  tags = local.common_tags
}

# =============================================================================
# ECS Alarms - Container Service
# =============================================================================

# Alarm: High CPU utilization (> 80%)
resource "aws_cloudwatch_metric_alarm" "ecs_high_cpu" {
  for_each = toset(var.ecs_service_names)

  alarm_name          = "${local.alarm_prefix}-ecs-${each.key}-high-cpu"
  alarm_description   = "ECS service ${each.key} CPU utilization exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = each.key
    ClusterName = var.ecs_cluster_name
  }

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# Alarm: High memory utilization (> 85%)
resource "aws_cloudwatch_metric_alarm" "ecs_high_memory" {
  for_each = toset(var.ecs_service_names)

  alarm_name          = "${local.alarm_prefix}-ecs-${each.key}-high-memory"
  alarm_description   = "ECS service ${each.key} memory utilization exceeds 85%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 85
  treat_missing_data  = "notBreaching"

  dimensions = {
    ServiceName = each.key
    ClusterName = var.ecs_cluster_name
  }

  alarm_actions = [aws_sns_topic.alarms_critical.arn]

  tags = local.common_tags
}

# Alarm: Service tasks running count too low
resource "aws_cloudwatch_metric_alarm" "ecs_low_running_tasks" {
  for_each = toset(var.ecs_service_names)

  alarm_name          = "${local.alarm_prefix}-ecs-${each.key}-low-tasks"
  alarm_description   = "ECS service ${each.key} has fewer than desired tasks running"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = var.minimum_running_tasks
  treat_missing_data  = "breaching"

  dimensions = {
    ServiceName = each.key
    ClusterName = var.ecs_cluster_name
  }

  alarm_actions = [aws_sns_topic.alarms_critical.arn]

  tags = local.common_tags
}

# =============================================================================
# RDS Alarms - Database
# =============================================================================

# Alarm: High CPU utilization (> 75%)
resource "aws_cloudwatch_metric_alarm" "rds_high_cpu" {
  alarm_name          = "${local.alarm_prefix}-rds-high-cpu"
  alarm_description   = "RDS CPU utilization exceeds 75%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 75
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = var.rds_cluster_id
  }

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# Alarm: Low freeable memory (< 512MB)
resource "aws_cloudwatch_metric_alarm" "rds_low_memory" {
  alarm_name          = "${local.alarm_prefix}-rds-low-memory"
  alarm_description   = "RDS freeable memory below 512MB"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 536870912 # 512MB in bytes
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = var.rds_cluster_id
  }

  alarm_actions = [aws_sns_topic.alarms_critical.arn]

  tags = local.common_tags
}

# Alarm: High database connections (> 80% of max)
resource "aws_cloudwatch_metric_alarm" "rds_high_connections" {
  alarm_name          = "${local.alarm_prefix}-rds-high-connections"
  alarm_description   = "RDS connection count exceeds 80% of max"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = var.rds_max_connections * 0.8
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = var.rds_cluster_id
  }

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# Alarm: Read latency too high (> 100ms)
resource "aws_cloudwatch_metric_alarm" "rds_high_read_latency" {
  alarm_name          = "${local.alarm_prefix}-rds-high-read-latency"
  alarm_description   = "RDS read latency exceeds 100ms"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "ReadLatency"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 0.1 # 100ms
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBClusterIdentifier = var.rds_cluster_id
  }

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# =============================================================================
# DynamoDB Alarms
# =============================================================================

# Alarm: Read throttle events
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttles" {
  for_each = toset(var.dynamodb_table_names)

  alarm_name          = "${local.alarm_prefix}-dynamodb-${each.key}-read-throttles"
  alarm_description   = "DynamoDB table ${each.key} experiencing read throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = each.key
  }

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# Alarm: Write throttle events
resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttles" {
  for_each = toset(var.dynamodb_table_names)

  alarm_name          = "${local.alarm_prefix}-dynamodb-${each.key}-write-throttles"
  alarm_description   = "DynamoDB table ${each.key} experiencing write throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = each.key
  }

  alarm_actions = [aws_sns_topic.alarms_warning.arn]

  tags = local.common_tags
}

# =============================================================================
# Custom Application Metrics (via CloudWatch Logs Metric Filters)
# =============================================================================

# Metric Filter: Error rate from application logs
resource "aws_cloudwatch_log_metric_filter" "application_errors" {
  for_each = toset(var.log_group_names)

  name           = "${each.key}-error-count"
  log_group_name = each.key
  pattern        = "[time, request_id, level=ERROR*, ...]"

  metric_transformation {
    name      = "ApplicationErrors"
    namespace = "Senas/Application"
    value     = "1"
    unit      = "Count"

    dimensions = {
      Service = each.key
    }
  }
}

# Alarm: High application error rate
resource "aws_cloudwatch_metric_alarm" "high_application_errors" {
  for_each = toset(var.log_group_names)

  alarm_name          = "${local.alarm_prefix}-${each.key}-high-errors"
  alarm_description   = "Application error rate exceeds threshold in ${each.key}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApplicationErrors"
  namespace           = "Senas/Application"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 50 # 50 errors in 5 minutes
  treat_missing_data  = "notBreaching"

  dimensions = {
    Service = each.key
  }

  alarm_actions = [aws_sns_topic.alarms_critical.arn]

  tags = local.common_tags
}

# Metric Filter: XP earned (business metric)
resource "aws_cloudwatch_log_metric_filter" "xp_earned" {
  for_each = toset(var.log_group_names)

  name           = "${each.key}-xp-earned"
  log_group_name = each.key
  pattern        = "[time, request_id, level, msg=\"XP earned\", xp_amount]"

  metric_transformation {
    name      = "XPEarned"
    namespace = "Senas/Business"
    value     = "$xp_amount"
    unit      = "None"

    dimensions = {
      Service = each.key
    }
  }
}

# Metric Filter: Exercises completed
resource "aws_cloudwatch_log_metric_filter" "exercises_completed" {
  for_each = toset(var.log_group_names)

  name           = "${each.key}-exercises-completed"
  log_group_name = each.key
  pattern        = "[time, request_id, level, msg=\"Exercise completed\", ...]"

  metric_transformation {
    name      = "ExercisesCompleted"
    namespace = "Senas/Business"
    value     = "1"
    unit      = "Count"

    dimensions = {
      Service = each.key
    }
  }
}

# =============================================================================
# CloudWatch Dashboard
# =============================================================================

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name}-dashboard"

  dashboard_body = templatefile("${path.module}/dashboard_template.json", {
    region               = var.aws_region
    alb_name             = var.alb_name
    ecs_cluster_name     = var.ecs_cluster_name
    ecs_service_names    = jsonencode(var.ecs_service_names)
    rds_cluster_id       = var.rds_cluster_id
    dynamodb_table_names = jsonencode(var.dynamodb_table_names)
    log_group_names      = jsonencode(var.log_group_names)
  })
}

# =============================================================================
# CloudWatch Log Groups Retention
# =============================================================================

resource "aws_cloudwatch_log_group" "retention_policy" {
  for_each = toset(var.log_group_names)

  name              = each.key
  retention_in_days = var.log_retention_days
  kms_key_id        = var.enable_encryption ? aws_kms_key.logs[0].arn : null

  tags = merge(
    local.common_tags,
    { Name = each.key }
  )
}

resource "aws_kms_key" "logs" {
  count = var.enable_encryption ? 1 : 0

  description             = "KMS key for CloudWatch Logs encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${var.aws_region}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          ArnLike = {
            "kms:EncryptionContext:aws:logs:arn" = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
          }
        }
      }
    ]
  })

  tags = merge(
    local.common_tags,
    { Name = "${local.name}-logs-kms" }
  )
}

data "aws_caller_identity" "current" {}
