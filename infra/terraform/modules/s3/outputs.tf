output "bucket_names" {
  value = { for k, v in aws_s3_bucket.main : k => v.bucket }
}

output "bucket_arns" {
  value = { for k, v in aws_s3_bucket.main : k => v.arn }
}

output "bucket_domains" {
  value = { for k, v in aws_s3_bucket.main : k => v.bucket_domain_name }
}

output "bucket_ids" {
  value = { for k, v in aws_s3_bucket.main : k => v.id }
}
