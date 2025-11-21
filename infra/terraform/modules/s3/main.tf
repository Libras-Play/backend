# S3 Buckets Module
locals { name = "${var.project_name}-${var.environment}" }

resource "aws_s3_bucket" "main" {
  for_each = toset(var.bucket_names)
  bucket   = "${local.name}-${each.value}"
  tags     = merge(var.tags, { Name = "${local.name}-${each.value}" })
}

resource "aws_s3_bucket_versioning" "main" {
  for_each = var.enable_versioning ? aws_s3_bucket.main : {}
  bucket   = each.value.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  for_each = aws_s3_bucket.main
  bucket   = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  for_each                = aws_s3_bucket.main
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "main" {
  for_each = var.lifecycle_expiration_days > 0 ? aws_s3_bucket.main : {}
  bucket   = each.value.id
  rule {
    id     = "expire-old-objects"
    status = "Enabled"
    expiration { days = var.lifecycle_expiration_days }
  }
}
