# ============================================================================
# DynamoDB Table: User Streaks (FASE 3)
# ============================================================================
# 
# Purpose: Track daily activity streaks per user per learning_language
# with timezone awareness, anti-cheat protections, and reward management.
#
# Primary Key:
#   PK: USER#<userId>#LL#<learning_language>
#   SK: STREAK#<periodType>#<periodValue>
#
# Examples:
#   PK: USER#user-123#LL#LSB, SK: STREAK#DAILY#current       → Current streak state
#   PK: USER#user-123#LL#LSB, SK: STREAK#DAILY#2025-11-19    → Historical daily record
#   PK: USER#user-123#LL#ASL, SK: STREAK#DAILY#current       → Separate streak for ASL
#
# Item Structure (current streak):
# {
#   "PK": "USER#user-123#LL#LSB",
#   "SK": "STREAK#DAILY#current",
#   "userId": "user-123",
#   "learning_language": "LSB",
#   "current_streak": 5,
#   "best_streak": 12,
#   "last_activity_day": "2025-11-18",
#   "last_claimed_at": "2025-11-18T20:00:00Z",
#   "metric_count_today": 3,
#   "metric_required": 3,
#   "reward_granted_today": true,
#   "pending_reward": {"coins": 10, "gems": 0},
#   "timezone": "America/Sao_Paulo",
#   "timezone_last_changed": "2025-11-01T10:00:00Z",
#   "suspicious_activity_count": 0,
#   "createdAt": "2025-11-18T15:30:00Z",
#   "updatedAt": "2025-11-18T20:00:00Z",
#   "TTL": 1763611200  // Only for history items (365 days)
# }
# ============================================================================

resource "aws_dynamodb_table" "user_streaks" {
  name         = "${var.project_name}-${var.environment}-user-streaks"
  billing_mode = "PAY_PER_REQUEST" # Auto-scaling for variable load
  hash_key     = "PK"
  range_key    = "SK"

  # Primary Key Attributes
  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI: Query all streaks by learning_language (analytics)
  attribute {
    name = "GSI1_PK"
    type = "S"
  }

  attribute {
    name = "GSI1_SK"
    type = "S"
  }

  global_secondary_index {
    name            = "LanguageStreakIndex"
    hash_key        = "GSI1_PK"
    range_key       = "GSI1_SK"
    projection_type = "ALL"
  }

  # GSI Design:
  # GSI1_PK: LANG#<learning_language>#DAY#<date>  (e.g., LANG#LSB#DAY#2025-11-19)
  # GSI1_SK: USER#<userId>
  # Use case: Get all users with streaks for LSB on a specific day (analytics, leaderboards)

  # Time-To-Live for historical items (365 days)
  ttl {
    attribute_name = "TTL"
    enabled        = true
  }

  # Point-in-Time Recovery (enabled for production only)
  point_in_time_recovery {
    enabled = var.environment == "production" ? true : false
  }

  # Server-Side Encryption
  server_side_encryption {
    enabled = true
  }

  # Tags
  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-${var.environment}-user-streaks"
      Description = "User daily streaks per learning_language with timezone support"
      FASE        = "3"
      DataType    = "user-streaks"
    }
  )
}

# ============================================================================
# Outputs
# ============================================================================

output "user_streaks_table_name" {
  description = "DynamoDB table name for user streaks"
  value       = aws_dynamodb_table.user_streaks.name
}

output "user_streaks_table_arn" {
  description = "ARN of the user streaks DynamoDB table"
  value       = aws_dynamodb_table.user_streaks.arn
}

# ============================================================================
# Access Patterns Supported:
# ============================================================================
# 
# 1. Get current streak for user + learning_language:
#    Query: PK = "USER#<userId>#LL#<LL>", SK = "STREAK#DAILY#current"
#
# 2. Get historical streak for specific day:
#    Query: PK = "USER#<userId>#LL#<LL>", SK = "STREAK#DAILY#2025-11-19"
#
# 3. Get all history for user + learning_language:
#    Query: PK = "USER#<userId>#LL#<LL>", SK BEGINS_WITH "STREAK#DAILY#"
#
# 4. Analytics - All users with streak on specific day for language:
#    GSI Query: GSI1_PK = "LANG#LSB#DAY#2025-11-19"
#
# 5. Leaderboard - Top streaks for language (requires scan or cache):
#    Scan with FilterExpression on current_streak (consider caching in ElastiCache)
# ============================================================================
