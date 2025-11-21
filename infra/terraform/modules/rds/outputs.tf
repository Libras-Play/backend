output "db_instance_endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
}

output "db_instance_address" {
  description = "RDS instance address (hostname only)"
  value       = aws_db_instance.postgres.address
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = aws_db_instance.postgres.port
}

output "database_url" {
  description = "PostgreSQL connection string for asyncpg"
  value       = "postgresql+asyncpg://${var.db_master_username}:${random_password.db_password.result}@${aws_db_instance.postgres.address}:${aws_db_instance.postgres.port}/${var.db_name}"
  sensitive   = true
}

output "db_secret_arn" {
  description = "ARN of Secrets Manager secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "db_security_group_id" {
  description = "Security group ID for RDS instance"
  value       = aws_security_group.rds.id
}
