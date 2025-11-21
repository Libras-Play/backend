output "topic_arns" {
  value = { for k, v in aws_sns_topic.main : k => v.arn }
}

output "topic_ids" {
  value = { for k, v in aws_sns_topic.main : k => v.id }
}
