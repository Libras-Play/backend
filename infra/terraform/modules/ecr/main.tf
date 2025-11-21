# =============================================================================
# ECR Module - Container Registry
# =============================================================================

locals {
  name = "${var.project_name}-${var.environment}"
}

# ECR Repositories
resource "aws_ecr_repository" "main" {
  for_each = toset(var.repository_names)

  name                 = "${local.name}-${each.value}"
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(
    var.tags,
    {
      Name       = "${local.name}-${each.value}"
      Repository = each.value
    }
  )
}

# Lifecycle Policy (eliminar imágenes antiguas)
resource "aws_ecr_lifecycle_policy" "main" {
  for_each = aws_ecr_repository.main

  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last ${var.max_image_count} images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.max_image_count
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# Repository Policy (permitir pull desde ECS)
resource "aws_ecr_repository_policy" "main" {
  for_each = aws_ecr_repository.main

  repository = each.value.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowPullFromECS"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ]
    }]
  })
}
