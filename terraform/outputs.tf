output "uploads_bucket_name" {
  description = "Name of the S3 bucket used for uploads"
  value       = aws_s3_bucket.uploads.id
}

output "uploads_bucket_arn" {
  description = "ARN of the S3 bucket used for uploads"
  value       = aws_s3_bucket.uploads.arn
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.uploads_app.id
}

output "instance_public_ip" {
  description = "EC2 public IP address"
  value       = aws_instance.uploads_app.public_ip
}

output "instance_elastic_ip" {
  description = "Elastic IP address of the uploads application"
  value       = aws_eip.uploads_app.public_ip
}

