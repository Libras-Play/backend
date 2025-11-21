# RDS Aurora Serverless v2 Module
locals {
  name = "${var.project_name}-${var.environment}"
}

resource "random_password" "master" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret" "rds" {
  name = "${local.name}-rds-credentials"
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "rds" {
  secret_id = aws_secretsmanager_secret.rds.id
  secret_string = jsonencode({
    username = var.master_username
    password = var.master_password != "" ? var.master_password : random_password.master.result
    engine   = "postgres"
    host     = aws_rds_cluster.main.endpoint
    port     = aws_rds_cluster.main.port
    dbname   = var.database_name
  })
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-rds-subnet-group"
  subnet_ids = var.database_subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "Security group for RDS Aurora"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }

  tags = var.tags
}

resource "aws_rds_cluster" "main" {
  cluster_identifier = "${local.name}-aurora-cluster"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = var.engine_version
  database_name      = var.database_name
  master_username    = var.master_username
  master_password    = var.master_password != "" ? var.master_password : random_password.master.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  serverlessv2_scaling_configuration {
    max_capacity = var.serverless_max_capacity
    min_capacity = var.serverless_min_capacity
  }

  backup_retention_period      = var.backup_retention_days
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  skip_final_snapshot          = var.skip_final_snapshot
  final_snapshot_identifier    = var.skip_final_snapshot ? null : "${local.name}-final-snapshot"
  deletion_protection          = var.enable_deletion_protection

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = var.tags
}

resource "aws_rds_cluster_instance" "main" {
  identifier         = "${local.name}-aurora-instance"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  tags = var.tags
}
