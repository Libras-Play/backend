output "table_names" {
  value = { for k, v in aws_dynamodb_table.main : k => v.name }
}

output "table_arns" {
  value = { for k, v in aws_dynamodb_table.main : k => v.arn }
}

output "table_ids" {
  value = { for k, v in aws_dynamodb_table.main : k => v.id }
}
