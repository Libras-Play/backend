# RDS PostgreSQL Free Tier Module
# Uses db.t3.micro (Free Tier eligible: 750 hrs/month, 20GB storage)

# Generate a random password for the database
resource "random_password" "db_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet"
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id
  
  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}

# RDS PostgreSQL Instance (Free Tier)
resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-${var.environment}-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  
  # Free Tier: db.t3.micro with 20GB storage
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"
  
  # Database configuration
  db_name  = var.db_name
  username = var.db_master_username
  password = random_password.db_password.result
  port     = 5432
  
  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  
  # Backup configuration
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"
  
  # High availability (disabled for cost savings in dev)
  multi_az = false
  
  # Deletion protection (disabled for dev)
  skip_final_snapshot       = true
  deletion_protection       = false
  delete_automated_backups  = true
  
  # Performance Insights (disabled for cost savings)
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-postgres"
    Environment = var.environment
  }
}

# Store credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}-${var.environment}-db-credentials"
  description = "Database credentials for ${var.project_name} ${var.environment}"
  
  tags = {
    Name = "${var.project_name}-${var.environment}-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_master_username
    password = random_password.db_password.result
    host     = aws_db_instance.postgres.endpoint
    address  = aws_db_instance.postgres.address
    port     = aws_db_instance.postgres.port
    database = var.db_name
    engine   = "postgres"
  })
}
