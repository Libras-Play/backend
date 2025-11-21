# =============================================================================
# ECS Fargate Module - Security Groups for ECS Tasks
# =============================================================================

# Security Groups (uno por servicio)
resource "aws_security_group" "ecs_tasks" {
  for_each = var.services

  name        = "${local.name}-${each.key}-sg"
  description = "Security group for ${each.key} ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Traffic from ALB"
    from_port       = each.value.container_port
    to_port         = each.value.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name    = "${local.name}-${each.key}-sg"
      Service = each.key
    }
  )
}
