# SQS Queues Module
locals { name = "${var.project_name}-${var.environment}" }

resource "aws_sqs_queue" "main" {
  for_each                   = var.queues
  name                       = "${local.name}-${each.key}"
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  max_message_size           = each.value.max_message_size
  receive_wait_time_seconds  = each.value.receive_wait_time_seconds
  sqs_managed_sse_enabled    = true
  tags                       = merge(var.tags, { Name = "${local.name}-${each.key}" })
}

resource "aws_sqs_queue" "dlq" {
  for_each                  = var.enable_dlq ? var.queues : {}
  name                      = "${local.name}-${each.key}-dlq"
  message_retention_seconds = 1209600 # 14 days
  tags                      = merge(var.tags, { Name = "${local.name}-${each.key}-dlq" })
}

resource "aws_sqs_queue_redrive_policy" "main" {
  for_each  = var.enable_dlq ? var.queues : {}
  queue_url = aws_sqs_queue.main[each.key].id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = 3
  })
}
