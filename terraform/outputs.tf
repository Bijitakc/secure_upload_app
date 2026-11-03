output "uploads_bucket_name" {
  description = "Name of the S3 bucket used for uploads"
  value       = aws_s3_bucket.uploads.id
}

output "uploads_bucket_arn" {
  description = "ARN of the S3 bucket used for uploads"
  value       = aws_s3_bucket.uploads.arn
}

output "uploads_iam_user_name" {
  description = "IAM user used by the application"
  value       = aws_iam_user.uploads_app.name
}