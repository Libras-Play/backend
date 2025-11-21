# DynamoDB Tables Module
locals { name = "${var.project_name}-${var.environment}" }

resource "aws_dynamodb_table" "main" {
  for_each = var.tables

  name         = "${local.name}-${each.key}"
  billing_mode = each.value.billing_mode
  hash_key     = each.value.hash_key
  range_key    = each.value.range_key != "" ? each.value.range_key : null

  dynamic "attribute" {
    for_each = each.value.range_key != "" ? [each.value.hash_key, each.value.range_key] : [each.value.hash_key]
    content {
      name = attribute.value
      type = "S"
    }
  }

  point_in_time_recovery { enabled = var.enable_point_in_time_recovery }
  server_side_encryption { enabled = true }

  tags = merge(var.tags, { Name = "${local.name}-${each.key}" })
}
