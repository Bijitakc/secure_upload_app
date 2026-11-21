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

  depends_on = [
    aws_s3_bucket_public_access_block.uploads
  ]

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

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {

    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
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
        Resource = "${aws_s3_bucket.uploads.arn}/${trim(var.s3_key_prefix, "/")}/*"
      }
    ]
  })
}

resource "aws_iam_role" "uploads_app" {
  name               = local.iam_name_prefix
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "uploads_app" {
  role       = aws_iam_role.uploads_app.name
  policy_arn = aws_iam_policy.uploads_access.arn
}

resource "aws_iam_instance_profile" "uploads_app" {
  name = local.iam_name_prefix
  role = aws_iam_role.uploads_app.name
}

resource "aws_security_group" "uploads_app" {
  name        = "${local.iam_name_prefix}-sg"
  description = "Security group for the uploads application"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.iam_name_prefix}-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.uploads_app.id

  description = "HTTP access"
  ip_protocol = "tcp"
  from_port   = 80
  to_port     = 80
  cidr_ipv4   = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.uploads_app.id

  description = "HTTPS access"
  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443
  cidr_ipv4   = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "http" {
  security_group_id = aws_security_group.uploads_app.id

  description = "Allow outbound HTTP"
  ip_protocol = "tcp"
  from_port   = 80
  to_port     = 80
  cidr_ipv4   = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.uploads_app.id

  description = "Allow outbound HTTPS"
  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443
  cidr_ipv4   = "0.0.0.0/0"
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.uploads_app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_ami" "ubuntu" {
  count       = var.localstack_endpoint == null ? 1 : 0
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "uploads_app" {
  ami                         = var.localstack_endpoint != null ? var.localstack_ami_id : data.aws_ami.ubuntu[0].id
  instance_type               = var.instance_type
  iam_instance_profile        = aws_iam_instance_profile.uploads_app.name
  associate_public_ip_address = var.localstack_endpoint != null ? true : false
  user_data                   = file("${path.module}/user_data.sh")
  user_data_replace_on_change = true
  subnet_id                   = aws_subnet.public.id

  vpc_security_group_ids = [
    aws_security_group.uploads_app.id
  ]

  root_block_device {
    volume_size           = 8
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = {
    Name        = "${local.iam_name_prefix}-ec2"
    Environment = var.environment
  }
}

resource "aws_eip" "uploads_app" {
  domain = "vpc"

  tags = {
    Name = "${local.iam_name_prefix}-eip"
  }
}

resource "aws_eip_association" "uploads_app" {
  instance_id   = aws_instance.uploads_app.id
  allocation_id = aws_eip.uploads_app.id
}