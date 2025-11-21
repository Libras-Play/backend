# ECS Module - Placeholder
# Creates ECS cluster, services, and ALB
# TODO: Implement complete ECS Fargate setup with ALB

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"
}

# Placeholder outputs
output "cluster_name" { value = aws_ecs_cluster.main.name }
output "alb_dns_name" { value = "placeholder-alb-dns.us-east-1.elb.amazonaws.com" }
