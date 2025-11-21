# =============================================================================
# ECS Fargate Module - Main Configuration
# =============================================================================

locals {
  name = "${var.project_name}-${var.environment}"
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name}-cluster"

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = merge(
    var.tags,
    {
      Name = "${local.name}-cluster"
    }
  )
}

# ECS Cluster Capacity Providers
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = var.enable_spot_instances ? ["FARGATE", "FARGATE_SPOT"] : ["FARGATE"]

  default_capacity_provider_strategy {
    capacity_provider = var.enable_spot_instances ? "FARGATE_SPOT" : "FARGATE"
    weight            = 1
    base              = 1
  }
}

# CloudWatch Log Groups (uno por servicio)
resource "aws_cloudwatch_log_group" "ecs" {
  for_each = var.services

  name              = "/ecs/${local.name}/${each.key}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name    = "${local.name}-${each.key}-logs"
      Service = each.key
    }
  )
}

# Task Definitions (uno por servicio)
resource "aws_ecs_task_definition" "main" {
  for_each = var.services

  family                   = "${local.name}-${each.key}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name  = each.key
    image = each.value.image

    essential = true

    portMappings = [{
      containerPort = each.value.container_port
      hostPort      = each.value.container_port
      protocol      = "tcp"
    }]

    environment = [
      for k, v in each.value.environment : {
        name  = k
        value = v
      }
    ]

    secrets = [
      for k, v in each.value.secrets : {
        name      = k
        valueFrom = v
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs[each.key].name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = each.key
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", each.value.health_check_command]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = merge(
    var.tags,
    {
      Name    = "${local.name}-${each.key}"
      Service = each.key
    }
  )
}

# ECS Services (uno por servicio)
resource "aws_ecs_service" "main" {
  for_each = var.services

  name            = "${local.name}-${each.key}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main[each.key].arn
  desired_count   = each.value.desired_count
  launch_type     = var.enable_spot_instances ? null : "FARGATE"

  # Capacity Provider Strategy (si usa Spot)
  dynamic "capacity_provider_strategy" {
    for_each = var.enable_spot_instances ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 1
      base              = 1
    }
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks[each.key].id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main[each.key].arn
    container_name   = each.key
    container_port   = each.value.container_port
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  enable_execute_command = var.enable_ecs_exec

  depends_on = [aws_lb_listener_rule.services]

  tags = merge(
    var.tags,
    {
      Name    = "${local.name}-${each.key}"
      Service = each.key
    }
  )
}

# Auto Scaling Targets
resource "aws_appautoscaling_target" "ecs" {
  for_each = var.enable_autoscaling ? var.services : {}

  max_capacity       = each.value.autoscaling_max
  min_capacity       = each.value.autoscaling_min
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main[each.key].name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "ecs_cpu" {
  for_each = var.enable_autoscaling ? var.services : {}

  name               = "${local.name}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs[each.key].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs[each.key].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs[each.key].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto Scaling Policy - Memory
resource "aws_appautoscaling_policy" "ecs_memory" {
  for_each = var.enable_autoscaling ? var.services : {}

  name               = "${local.name}-${each.key}-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs[each.key].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs[each.key].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs[each.key].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

data "aws_region" "current" {}
