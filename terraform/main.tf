terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

variable "project_name" {
  description = "Project identifier used in resource names"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "aws_account_id" {
  description = "AWS account ID used to distinguish bucket names"
  type        = string
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "localstack_endpoint" {
  description = "LocalStack endpoint, null uses the normal AWS endpoints"
  type        = string
  default     = null
}

variable "frontend_origin" {
  description = "Allowed frontend origin for browser-based S3 uploads"
  type        = string
}

variable "s3_key_prefix" {
  type = string
}

locals {
  bucket_name     = "${var.project_name}-${var.environment}-${var.aws_account_id}"
  iam_name_prefix = "${var.project_name}-${var.environment}"
}

provider "aws" {
  region = var.aws_region

  endpoints {
    s3        = var.localstack_endpoint
    s3control = var.localstack_endpoint
    sts       = var.localstack_endpoint
    iam       = var.localstack_endpoint
  }

  s3_use_path_style = true
}

resource "aws_s3_bucket" "uploads" {
  bucket = local.bucket_name
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.uploads.arn,
          "${aws_s3_bucket.uploads.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_iam_user" "uploads_app" {
  name = local.iam_name_prefix
}

resource "aws_iam_user_policy_attachment" "uploads_app" {
  user       = aws_iam_user.uploads_app.name
  policy_arn = aws_iam_policy.uploads_access.arn
}

resource "aws_iam_policy" "uploads_access" {
  name        = "${local.iam_name_prefix}-s3-access"
  description = "Allow the app to upload, download, and delete attachment objects"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "UploadAttachments"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.uploads.arn}/${var.s3_key_prefix}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_cors_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  cors_rule {
    allowed_origins = [var.frontend_origin]
    allowed_methods = ["POST", "GET", "HEAD"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}