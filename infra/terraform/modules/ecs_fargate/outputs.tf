output "cluster_id" {
  description = "ID del cluster ECS"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Nombre del cluster ECS"
  value       = aws_ecs_cluster.main.name
}

output "cluster_arn" {
  description = "ARN del cluster ECS"
  value       = aws_ecs_cluster.main.arn
}

output "service_names" {
  description = "Nombres de servicios ECS"
  value       = [for k, v in aws_ecs_service.main : v.name]
}

output "service_arns" {
  description = "ARNs de servicios ECS"
  value       = { for k, v in aws_ecs_service.main : k => v.id }
}

output "task_definition_arns" {
  description = "ARNs de task definitions"
  value       = { for k, v in aws_ecs_task_definition.main : k => v.arn }
}

output "alb_arn" {
  description = "ARN del ALB"
  value       = aws_lb.main.arn
}

output "alb_dns_name" {
  description = "DNS name del ALB"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID del ALB"
  value       = aws_lb.main.zone_id
}

output "target_group_arns" {
  description = "ARNs de target groups"
  value       = { for k, v in aws_lb_target_group.main : k => v.arn }
}

output "log_group_names" {
  description = "Nombres de CloudWatch Log Groups"
  value       = { for k, v in aws_cloudwatch_log_group.ecs : k => v.name }
}

output "security_group_ids" {
  description = "IDs de security groups de ECS tasks"
  value       = { for k, v in aws_security_group.ecs_tasks : k => v.id }
}

output "alb_security_group_id" {
  description = "ID del security group del ALB"
  value       = aws_security_group.alb.id
}
