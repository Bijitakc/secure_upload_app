variable "project_name" {
  description = "Project identifier used in resource names"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]*[a-z0-9]$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens, and must start and end with a letter or number."
  }
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
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
  description = "S3 object key prefix used to scope application access"
  type        = string

  validation {
    condition     = length(trim(var.s3_key_prefix, "/")) > 0
    error_message = "S3 key prefix must not be empty or contain only slashes"
  }
}