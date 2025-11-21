# SNS Topics Module
locals { name = "${var.project_name}-${var.environment}" }

resource "aws_sns_topic" "main" {
  for_each = toset(var.topic_names)
  name     = "${local.name}-${each.value}"
  tags     = merge(var.tags, { Name = "${local.name}-${each.value}" })
}

resource "aws_sns_topic_subscription" "email" {
  for_each  = var.email_subscriptions
  topic_arn = aws_sns_topic.main[each.key].arn
  protocol  = "email"
  endpoint  = each.value
}
