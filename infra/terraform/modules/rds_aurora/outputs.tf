output "cluster_id" {
  value = aws_rds_cluster.main.id
}

output "cluster_endpoint" {
  value = aws_rds_cluster.main.endpoint
}

output "reader_endpoint" {
  value = aws_rds_cluster.main.reader_endpoint
}

output "database_name" {
  value = aws_rds_cluster.main.database_name
}

output "port" {
  value = aws_rds_cluster.main.port
}

output "secret_arn" {
  value = aws_secretsmanager_secret.rds.arn
}

output "security_group_id" {
  value = aws_security_group.rds.id
}
