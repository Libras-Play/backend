# DynamoDB Tables for User Service

# UserData table - Main user information
resource "aws_dynamodb_table" "user_data" {
  name           = var.user_table_name
  billing_mode   = "PAY_PER_REQUEST"  # On-demand scaling
  hash_key       = "userId"
  
  attribute {
    name = "userId"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = false
  }
  
  tags = {
    Name        = "UserData"
    Service     = "user-service"
    Environment = var.environment
  }
}

# UserProgress table - Exercise progress tracking
resource "aws_dynamodb_table" "user_progress" {
  name           = var.progress_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "userId"
  range_key      = "levelId"
  
  attribute {
    name = "userId"
    type = "S"
  }
  
  attribute {
    name = "levelId"
    type = "S"
  }
  
  attribute {
    name = "levelIdNumber"
    type = "N"
  }
  
  # GSI for querying all users' progress for a specific level
  global_secondary_index {
    name            = "levelId-index"
    hash_key        = "levelIdNumber"
    projection_type = "ALL"
  }
  
  tags = {
    Name        = "UserProgress"
    Service     = "user-service"
    Environment = var.environment
  }
}

# AiSessions table - AI processing sessions
resource "aws_dynamodb_table" "ai_sessions" {
  name           = var.ai_sessions_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "sessionId"
  
  attribute {
    name = "sessionId"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true  # Auto-delete old sessions after 30 days
  }
  
  tags = {
    Name        = "AiSessions"
    Service     = "user-service"
    Environment = var.environment
  }
}

# Outputs
output "user_table_name" {
  value = aws_dynamodb_table.user_data.name
}

output "progress_table_name" {
  value = aws_dynamodb_table.user_progress.name
}

output "ai_sessions_table_name" {
  value = aws_dynamodb_table.ai_sessions.name
}
