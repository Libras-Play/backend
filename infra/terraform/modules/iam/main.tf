# =============================================================================
# IAM Module - Roles and Policies for ECS
# =============================================================================

locals {
  name = "${var.project_name}-${var.environment}"
}

# ECS Task Execution Role (para pull images de ECR, logs a CloudWatch)
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = merge(
    var.tags,
    {
      Name = "${local.name}-ecs-execution"
    }
  )
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for ECR and Secrets Manager
resource "aws_iam_role_policy" "ecs_execution_additional" {
  name = "${local.name}-ecs-execution-additional"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect = "Allow"
          Action = [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage"
          ]
          Resource = "*"
        },
        {
          Effect = "Allow"
          Action = [
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ]
          Resource = "*"
        }
      ],
      # Solo incluir Secrets Manager si hay secrets
      length(var.secrets_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue"
          ]
          Resource = var.secrets_arns
        }
      ] : []
    )
  })
}

# ECS Task Role (permisos para la aplicación en runtime)
resource "aws_iam_role" "ecs_task" {
  name = "${local.name}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = merge(
    var.tags,
    {
      Name = "${local.name}-ecs-task"
    }
  )
}

# Task Role Policy - Permisos mínimos para servicios
resource "aws_iam_role_policy" "ecs_task" {
  name = "${local.name}-ecs-task-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        # S3 - Get/Put objects
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:ListBucket"
          ]
          Resource = concat(
            [for bucket in var.s3_bucket_arns : "${bucket}/*"],
            var.s3_bucket_arns
          )
        },
        # DynamoDB - Full access a tablas específicas
        {
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem",
            "dynamodb:Query",
            "dynamodb:Scan",
            "dynamodb:BatchGetItem",
            "dynamodb:BatchWriteItem"
          ]
          Resource = var.dynamodb_table_arns
        },
        # SQS - Send/Receive messages
        {
          Effect = "Allow"
          Action = [
            "sqs:SendMessage",
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
          ]
          Resource = var.sqs_queue_arns
        },
        # SNS - Publish notifications
        {
          Effect = "Allow"
          Action = [
            "sns:Publish"
          ]
          Resource = var.sns_topic_arns
        },
        # CloudWatch - Put metrics
        {
          Effect = "Allow"
          Action = [
            "cloudwatch:PutMetricData"
          ]
          Resource = "*"
        }
      ],
      # Solo incluir Secrets Manager si hay secrets
      length(var.secrets_arns) > 0 ? [
        {
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Resource = var.secrets_arns
        }
      ] : []
    )
  })
}

# ECS Exec Role (opcional, para debugging)
resource "aws_iam_role_policy" "ecs_exec" {
  count = var.enable_ecs_exec ? 1 : 0

  name = "${local.name}-ecs-exec"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ]
      Resource = "*"
    }]
  })
}
