# DynamoDB Table: User Path Progress (FASE 2)
# Stores guided learning path progression per user x learning_language

resource "aws_dynamodb_table" "user_path_progress" {
  name         = "${var.project_name}-${var.environment}-user-path-progress"
  billing_mode = "PAY_PER_REQUEST" # On-demand pricing

  hash_key  = "PK"  # USER#<userId>#LL#<learningLanguage>
  range_key = "SK"  # PATH#<topicId>

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI for querying by topic and language (analytics)
  attribute {
    name = "GSI1_PK"
    type = "S"
  }

  attribute {
    name = "GSI1_SK"
    type = "S"
  }

  global_secondary_index {
    name            = "TopicLanguageIndex"
    hash_key        = "GSI1_PK"  # TOPIC#<topicId>#LL#<learningLanguage>
    range_key       = "GSI1_SK"  # USER#<userId>
    projection_type = "ALL"
  }

  # Enable point-in-time recovery for production
  point_in_time_recovery {
    enabled = var.environment == "production" ? true : false
  }

  # Server-side encryption
  server_side_encryption {
    enabled = true
  }

  # TTL disabled (we want to keep path history)
  # ttl {
  #   attribute_name = "expiresAt"
  #   enabled        = false
  # }

  tags = {
    Name        = "${var.project_name}-user-path-progress"
    Environment = var.environment
    ManagedBy   = "Terraform"
    Service     = "user-service"
    Purpose     = "Guided learning path progression (FASE 2)"
  }
}

# Output the table name for use in other modules
output "user_path_progress_table_name" {
  description = "Name of the User Path Progress DynamoDB table"
  value       = aws_dynamodb_table.user_path_progress.name
}

output "user_path_progress_table_arn" {
  description = "ARN of the User Path Progress DynamoDB table"
  value       = aws_dynamodb_table.user_path_progress.arn
}
