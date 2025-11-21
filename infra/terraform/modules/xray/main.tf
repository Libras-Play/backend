# =============================================================================
# X-Ray Configuration for ECS Task Definition
# =============================================================================
# Configuración para habilitar AWS X-Ray tracing en servicios ECS.
# =============================================================================

# Agregar este contenedor sidecar al task definition de cada servicio

locals {
  xray_sidecar_container = {
    name      = "xray-daemon"
    image     = "amazon/aws-xray-daemon:latest"
    cpu       = 32
    memory    = 256
    essential = false # No crítico para la app principal

    portMappings = [
      {
        containerPort = 2000
        protocol      = "udp"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}/xray"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "xray-daemon"
      }
    }

    environment = [
      {
        name  = "AWS_REGION"
        value = var.aws_region
      }
    ]
  }
}

# =============================================================================
# CloudWatch Log Group para X-Ray
# =============================================================================

resource "aws_cloudwatch_log_group" "xray" {
  name              = "/ecs/${var.project_name}-${var.environment}/xray"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name    = "${var.project_name}-${var.environment}-xray-logs"
      Service = "xray"
    }
  )
}

# =============================================================================
# IAM Policy para X-Ray
# =============================================================================

data "aws_iam_policy_document" "xray" {
  statement {
    sid = "XRayAccess"

    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
      "xray:GetSamplingStatisticSummaries"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "xray" {
  name        = "${var.project_name}-${var.environment}-xray-policy"
  description = "Policy for ECS tasks to send data to X-Ray"
  policy      = data.aws_iam_policy_document.xray.json

  tags = var.tags
}

# Adjuntar a task role (hacer en el módulo ECS)
# resource "aws_iam_role_policy_attachment" "xray" {
#   role       = aws_iam_role.ecs_task_role.name
#   policy_arn = aws_iam_policy.xray.arn
# }

# =============================================================================
# Example: Updated Task Definition with X-Ray
# =============================================================================

# En modules/ecs_fargate/main.tf, actualizar container_definitions:

/*
resource "aws_ecs_task_definition" "main" {
  # ... otras configuraciones ...
  
  container_definitions = jsonencode(concat(
    [
      # Contenedor principal de la aplicación
      {
        name  = "app"
        image = "${var.ecr_repository_url}:latest"
        # ... configuración de la app ...
        
        environment = [
          # ... otras variables ...
          {
            name  = "AWS_XRAY_DAEMON_ADDRESS"
            value = "xray-daemon:2000"
          },
          {
            name  = "AWS_XRAY_TRACING_NAME"
            value = var.service_name
          }
        ]
      }
    ],
    # Agregar sidecar de X-Ray
    [local.xray_sidecar_container]
  ))
}
*/

# =============================================================================
# X-Ray Sampling Rules
# =============================================================================

resource "aws_xray_sampling_rule" "default" {
  rule_name      = "${var.project_name}-${var.environment}-default"
  priority       = 1000
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.05 # 5% de requests
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*"
  resource_arn   = "*"

  attributes = {
    Environment = var.environment
  }
}

# Regla con mayor sampling para endpoints críticos
resource "aws_xray_sampling_rule" "critical_endpoints" {
  rule_name      = "${var.project_name}-${var.environment}-critical"
  priority       = 100 # Mayor prioridad (menor número)
  version        = 1
  reservoir_size = 5
  fixed_rate     = 0.50           # 50% de requests en endpoints críticos
  url_path       = "/exercises/*" # Endpoints críticos
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*"
  resource_arn   = "*"

  attributes = {
    Environment = var.environment
    Critical    = "true"
  }
}

# Regla para errores (100% sampling)
resource "aws_xray_sampling_rule" "errors" {
  rule_name      = "${var.project_name}-${var.environment}-errors"
  priority       = 50
  version        = 1
  reservoir_size = 10
  fixed_rate     = 1.0 # 100% de requests con errores
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "*"
  resource_arn   = "*"

  attributes = {
    Environment = var.environment
    ErrorTrace  = "true"
  }
}

# =============================================================================
# X-Ray Group para análisis
# =============================================================================

resource "aws_xray_group" "main" {
  group_name        = "${var.project_name}-${var.environment}-main"
  filter_expression = "service(\"${var.project_name}-${var.environment}*\")"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = var.enable_xray_notifications
  }

  tags = var.tags
}

# Grupo para latencia alta
resource "aws_xray_group" "high_latency" {
  group_name        = "${var.project_name}-${var.environment}-high-latency"
  filter_expression = "service(\"${var.project_name}-${var.environment}*\") AND responsetime > 2"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = true
  }

  tags = merge(
    var.tags,
    { Type = "performance" }
  )
}

# Grupo para errores
resource "aws_xray_group" "errors" {
  group_name        = "${var.project_name}-${var.environment}-errors"
  filter_expression = "service(\"${var.project_name}-${var.environment}*\") AND (error OR fault)"

  insights_configuration {
    insights_enabled      = true
    notifications_enabled = true
  }

  tags = merge(
    var.tags,
    { Type = "errors" }
  )
}
