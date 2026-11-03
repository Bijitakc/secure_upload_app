locals {
  bucket_name     = "${var.project_name}-${var.environment}-${var.aws_account_id}"
  iam_name_prefix = "${var.project_name}-${var.environment}"
  use_localstack  = var.localstack_endpoint != null
}