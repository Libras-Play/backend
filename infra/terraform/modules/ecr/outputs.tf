output "repository_urls" {
  description = "URLs de repositorios ECR"
  value       = { for k, v in aws_ecr_repository.main : k => v.repository_url }
}

output "repository_arns" {
  description = "ARNs de repositorios ECR"
  value       = { for k, v in aws_ecr_repository.main : k => v.arn }
}

output "repository_names" {
  description = "Nombres de repositorios ECR"
  value       = { for k, v in aws_ecr_repository.main : k => v.name }
}
