# Terraform Infrastructure Reference


### Current implementation status

| Area | Status |
|---|---|
| Terraform configuration for S3 and IAM | Implemented; applied against LocalStack |
| Custom VPC, public/private subnets and route tables | Implemented; applied against LocalStack |
| EC2, security group, instance profile and Elastic IP | Implemented; applied against LocalStack's EC2 emulator |
| EC2 bootstrap script for Docker Engine and Compose | Written; not executed on a real EC2 instance in this project run |
| SSM instance permissions | Attached to the EC2 role in Terraform; SSM connectivity not tested against AWS |

