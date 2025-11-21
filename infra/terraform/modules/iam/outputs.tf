output "ecs_execution_role_arn" {
  description = "ARN del IAM role para ECS task execution"
  value       = aws_iam_role.ecs_execution.arn
}

output "ecs_execution_role_name" {
  description = "Nombre del IAM role para ECS task execution"
  value       = aws_iam_role.ecs_execution.name
}

output "ecs_task_role_arn" {
  description = "ARN del IAM role para ECS tasks"
  value       = aws_iam_role.ecs_task.arn
}

output "ecs_task_role_name" {
  description = "Nombre del IAM role para ECS tasks"
  value       = aws_iam_role.ecs_task.name
}
