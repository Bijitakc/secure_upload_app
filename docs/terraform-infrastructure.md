# Terraform Infrastructure Reference


### Current implementation status

| Area | Status |
|---|---|
| Terraform configuration for S3 and IAM | Implemented; applied against LocalStack |
| Custom VPC, public/private subnets and route tables | Implemented; applied against LocalStack |
| EC2, security group, instance profile and Elastic IP | Implemented; applied against LocalStack's EC2 emulator |
| EC2 bootstrap script for Docker Engine and Compose | Written; not executed on a real EC2 instance in this project run |
| SSM instance permissions | Attached to the EC2 role in Terraform; SSM connectivity not tested against AWS |

---

## 1. Architecture overview

The current Terraform configuration provisions the infrastructure foundation for secure_upload_app. It creates a custom VPC for the compute resources, an EC2 instance in the public subnet, the security group and Elastic IP for that instance, an S3 bucket for uploaded objects, and an IAM role that can be attached to EC2.

### Resources provisioned

- One custom VPC.
- One public subnet and one private subnet, currently in the same Availability Zone.
- One Internet Gateway.
- Separate route tables for the public and private subnets.
- One security group for the application EC2 instance.
- One EC2 instance, one Elastic IP and an Elastic IP association.
- One S3 bucket and its security/configuration resources.
- One EC2 IAM role, a customer-managed S3 access policy, an instance profile and the AWS-managed SSM core policy attachment.


## 2. Terraform project layout

The current Terraform configuration is in `terraform/`:

| File | Responsibility |
|---|---|
| `providers.tf` | AWS provider configuration and LocalStack endpoint overrides |
| `variables.tf` | Input variables, defaults and validation rules |
| `locals.tf` | Derived names and the LocalStack boolean |
| `main.tf` | S3, IAM, security group, EC2 and Elastic IP resources |
| `vpc.tf` | VPC, subnets, Internet Gateway and route tables |
| `outputs.tf` | Useful resource identifiers and addresses |
| `user_data.sh` | EC2 first-boot installation of Docker Engine and Compose plugin |
| `tf-localstack.sh` | Loads the LocalStack environment file and runs Terraform |
| `deploy.sh` | Pulls a selected Flask application image from GHCR; Not complete |


## 3. Provider configuration and LocalStack support

### AWS provider

`providers.tf` configures the AWS provider with `var.aws_region`. It also applies default tags to resources:

- `Project`
- `Environment`
- `ManagedBy = "terraform"`

The provider has endpoint overrides for S3, STS, IAM and EC2. Each endpoint is set to `var.localstack_endpoint`.

### Selecting LocalStack or AWS

`locals.tf` contains:

```hcl
locals {
  bucket_name     = "${var.project_name}-${var.environment}-${var.aws_account_id}"
  iam_name_prefix = "${var.project_name}-${var.environment}"
  use_localstack  = var.localstack_endpoint != null
}
```

When `localstack_endpoint` is set:

- The AWS provider sends supported service requests to LocalStack.
- The provider skips selected AWS credential, metadata and account-ID checks that are not useful for the emulator.
- S3 path-style addressing is enabled for LocalStack.
- The EC2 resource uses the configured placeholder AMI ID instead of looking up a real Ubuntu AMI.

When `localstack_endpoint` is `null`, the provider uses normal AWS endpoints and the EC2 AMI data source looks up an Ubuntu AMI from Canonical.

The same Terraform resource definitions are therefore used for both targets, while a few provider and EC2 settings change based on the target.

### LocalStack environment variables

The local wrapper, `tf-localstack.sh`, runs the following sequence:

```bash
set -eu
set -a
source .env.terraform
set +a
terraform "$@"
```

- `source .env.terraform` loads the local environment configuration.
- `set -a` exports variables defined while sourcing the file.
- Terraform receives `TF_VAR_*` variables as Terraform input variables.
- `terraform "$@"` forwards the command and arguments, for example `plan`, `apply` or `output`.

Run the wrapper from the directory where `.env.terraform` is located, because the script sources that file using a relative path.

The LocalStack configuration used during this work included these Terraform inputs:

| Variable | Example LocalStack value | Purpose |
|---|---|---|
| `TF_VAR_project_name` | `secure-upload-app` | Prefix used in names |
| `TF_VAR_environment` | `dev` | Environment name |
| `TF_VAR_aws_account_id` | `000000000000` | LocalStack placeholder account ID used in the bucket name |
| `TF_VAR_aws_region` | `us-east-1` | Provider region |
| `TF_VAR_localstack_endpoint` | `http://localhost:4566` | LocalStack endpoint |
| `TF_VAR_frontend_origin` | `http://localhost:3000` | Allowed browser origin in S3 CORS |
| `TF_VAR_s3_key_prefix` | `attachments/files` | S3 object-key prefix granted to the app |
| `TF_VAR_localstack_ami_id` | `ami-785db401` | Placeholder AMI ID for LocalStack EC2 emulation |

LocalStack test credentials such as `AWS_ACCESS_KEY_ID=test` and `AWS_SECRET_ACCESS_KEY=test` are emulator credentials, not real AWS credentials. Do not put real credentials in a committed environment file.

## 4. Input variables and naming

The important variables in `variables.tf` are:

| Variable | Default / requirement | Explanation |
|---|---|---|
| `project_name` | Required | Lowercase project identifier; validation restricts its characters and length |
| `environment` | `dev` | Restricted to `dev`, `staging` or `prod` |
| `aws_account_id` | Required | Must contain 12 digits; LocalStack uses a placeholder value |
| `aws_region` | Required | AWS region for resource creation |
| `localstack_endpoint` | `null` | `null` selects normal AWS endpoints |
| `frontend_origin` | Required | Exact origin permitted by the bucket's CORS configuration |
| `s3_key_prefix` | Required | Prefix that scopes the application's object-level S3 permissions; cannot be empty or contain `*` or `?` |
| `instance_type` | `t3.micro` | EC2 instance type |
| `localstack_ami_id` | `ami-785db401` | Placeholder AMI ID for LocalStack |
| `vpc_cidr` | `10.0.0.0/24` | Address range for the VPC |
| `public_subnet_cidr` | `10.0.0.0/25` | Address range for the public subnet |
| `private_subnet_cidr` | `10.0.0.128/25` | Address range for the private subnet |

The bucket name is derived from the project, environment and account ID:

```text
<project_name>-<environment>-<aws_account_id>
```

For the LocalStack values above, this becomes:

```text
secure-upload-app-dev-000000000000
```

This naming pattern helps separate buckets across projects, environments and AWS accounts.


## 5. S3 bucket configuration

The S3 bucket and its related configuration are declared in `main.tf`.

### 5.1 Bucket creation

`aws_s3_bucket.uploads` creates the bucket using `local.bucket_name`.

### 5.2 Default server-side encryption

`aws_s3_bucket_server_side_encryption_configuration.uploads` sets the default encryption algorithm to `AES256` (SSE-S3).

New objects written to the bucket use S3-managed server-side encryption by default. This configuration uses SSE-S3; it does not configure a customer-managed AWS KMS key.

### 5.3 Block public access

`aws_s3_bucket_public_access_block.uploads` enables all four public-access-block settings:

- `block_public_acls`
- `block_public_policy`
- `ignore_public_acls`
- `restrict_public_buckets`

The intent is to prevent public access from being granted through bucket or object ACLs and public bucket policies.

### 5.4 Deny insecure transport

`aws_s3_bucket_policy.uploads` adds an explicit `Deny` for `s3:*` when the request condition `aws:SecureTransport` is `false`.

The policy covers both the bucket ARN and all objects under it. This denies requests made without TLS. It does not itself grant access; the application's IAM identity policy supplies the allowed S3 actions.

The policy explicitly depends on the public access block so Terraform creates that configuration before attaching the bucket policy.

### 5.5 Object ownership controls

`aws_s3_bucket_ownership_controls.uploads` sets `BucketOwnerEnforced`.

This disables object ACLs and makes the bucket owner the owner of objects in the bucket. Access is intended to be controlled through policies rather than ACLs.

### 5.6 CORS

The bucket's CORS rule uses `var.frontend_origin` and currently allows:

| Setting | Value |
|---|---|
| Allowed origin | The configured frontend origin |
| Allowed methods | `POST`, `GET`, `HEAD` |
| Allowed headers | `*` |
| Exposed headers | `ETag` |
| Max age | `3000` seconds |

CORS controls which browser-based cross-origin requests are permitted by the browser. It is not an authentication or authorization mechanism; IAM and the application's presigned-URL flow still control access.

## 6. IAM: EC2 role and least-privilege S3 access

The application is intended to access S3 using temporary credentials supplied through the EC2 instance role, rather than storing long-lived AWS access keys on the server.

### 6.1 Trust policy

`data.aws_iam_policy_document.ec2_assume_role` creates the role trust policy. It permits the AWS EC2 service principal (`ec2.amazonaws.com`) to call `sts:AssumeRole`.

This answers **who can assume the role**. It does not define what the role can do.

### 6.2 S3 permissions policy

`aws_iam_policy.uploads_access` grants these object-level actions:

- `s3:PutObject`
- `s3:GetObject`
- `s3:DeleteObject`

The resource ARN is scoped to the configured prefix:

```hcl
Resource = "${aws_s3_bucket.uploads.arn}/${trim(var.s3_key_prefix, "/")}/*"
```

With `s3_key_prefix = "attachments/files"`, the policy applies to objects under:

```text
s3://<bucket-name>/attachments/files/*
```

The policy does not grant `s3:ListBucket`, and it does not grant object access outside the configured prefix. This matches the application's object-level upload, download and delete operations; it is not a general bucket-administration policy.

### 6.3 Role, policy attachment and instance profile

The configuration creates:

1. `aws_iam_role.uploads_app` — the role with the EC2 trust policy.
2. `aws_iam_role_policy_attachment.uploads_app` — attaches the custom S3 permissions policy.
3. `aws_iam_instance_profile.uploads_app` — makes the role available to an EC2 instance.
4. `aws_iam_role_policy_attachment.ssm_core` — attaches AWS-managed `AmazonSSMManagedInstanceCore` to support Systems Manager's instance-side permissions.

The instance profile is attached to `aws_instance.uploads_app` through `iam_instance_profile`.


## 7. Custom VPC and network design

The configuration creates and uses a dedicated VPC instead. This makes the network layout explicit and gives the project separate public and private subnets for future workloads.

### 7.1 VPC CIDR planning

The VPC CIDR is:

```text
10.0.0.0/24
```

A `/24` contains 256 IPv4 addresses. It is divided into two non-overlapping `/25` subnets:

| Subnet | CIDR | Address count before AWS reservations |
|---|---|---:|
| Public | `10.0.0.0/25` | 128 |
| Private | `10.0.0.128/25` | 128 |

The first subnet covers `10.0.0.0` through `10.0.0.127`; the second begins at `10.0.0.128` and covers through `10.0.0.255`.

In AWS, five IPv4 addresses in each subnet are reserved by the platform, leaving 123 addresses assignable in each `/25` subnet. The `/24` was chosen as a modest practice-project network while still leaving room for additional resources within the two subnets.

### 7.2 VPC DNS settings

`aws_vpc.main` enables:

- `enable_dns_support = true`
- `enable_dns_hostnames = true`

These settings enable VPC DNS resolution and DNS hostnames for resources that support them.

### 7.3 Availability Zone selection

`data.aws_availability_zones.available` retrieves the available Availability Zones in the selected region. Both subnets use `names[0]`, so they are currently placed in the same Availability Zone.

This is sufficient for the current learning setup, but it is not a multi-AZ or highly available network design. A future resilient design would place suitable subnets and workloads across more than one Availability Zone.

### 7.4 Public subnet

`aws_subnet.public` uses `var.public_subnet_cidr` and sets:

```hcl
map_public_ip_on_launch = true
```

This enables automatic public IPv4 assignment by default for instances launched in the subnet, unless an instance-level setting overrides it.

### 7.5 Private subnet

`aws_subnet.private` uses `var.private_subnet_cidr`. It does not enable automatic public IPv4 assignment.

The subnet is associated with a separate route table that has no default route to an Internet Gateway or NAT Gateway. It is therefore not configured for direct internet access.

### 7.6 Internet Gateway

`aws_internet_gateway.main` is attached to the custom VPC. An Internet Gateway provides the VPC's target for internet-bound routes, but creating and attaching it alone does not make a subnet public. The route table must direct internet traffic to it, and an instance also needs a public IP address and suitable security rules.

### 7.7 Public route table

`aws_route_table.public` has this route:

```hcl
route {
  cidr_block = "0.0.0.0/0"
  gateway_id = aws_internet_gateway.main.id
}
```

`0.0.0.0/0` is the default IPv4 route. Traffic not matched by a more specific route is sent to the Internet Gateway.

`aws_route_table_association.public` associates this route table with the public subnet.

### 7.8 Private route table

`aws_route_table.private` has no custom internet-bound route. `aws_route_table_association.private` associates it with the private subnet.

AWS automatically provides a local route for communication within the VPC. Because no `0.0.0.0/0` route is configured, the subnet has no direct internet route. No NAT Gateway has been created.

The private subnet currently has no workload deployed into it; it is provisioned as a place for future private resources.

## 8. Security group

`aws_security_group.uploads_app` is associated with `aws_vpc.main` and is attached to the EC2 instance.

The rules are defined using separate `aws_vpc_security_group_ingress_rule` and `aws_vpc_security_group_egress_rule` resources.

### Inbound rules

| Protocol | Port | Source | Purpose |
|---|---:|---|---|
| TCP | 80 | `0.0.0.0/0` | HTTP access |
| TCP | 443 | `0.0.0.0/0` | HTTPS access, retained for the planned HTTPS setup |

There is no inbound SSH rule on port 22. The chosen administration approach is AWS Systems Manager Session Manager rather than opening SSH access to the instance.

### Outbound rules

| Protocol | Port | Destination | Purpose |
|---|---:|---|---|
| TCP | 80 | `0.0.0.0/0` | Outbound HTTP, including package/repository access where required |
| TCP | 443 | `0.0.0.0/0` | Outbound HTTPS, including GHCR image pulls and Systems Manager communication |

These rules restrict outbound TCP traffic to HTTP and HTTPS instead of allowing all outbound ports. The security group does not open PostgreSQL port 5432 to the internet. In the planned container deployment, the database is expected to communicate with the application over the Docker network on the same host rather than through an external database port.

The inbound HTTPS rule is retained for the planned HTTPS configuration even though the current Terraform work has not deployed or verified an HTTPS listener on EC2.

## 9. EC2 instance

`aws_instance.uploads_app` creates the application host in the public subnet.

### 9.1 AMI selection

For AWS, `data.aws_ami.ubuntu` searches for an Ubuntu 24.04 LTS (Noble) image with:

- Canonical as the AMI owner (`099720109477`).
- An Ubuntu Noble 24.04 AMD64 server image name.
- `x86_64` architecture.
- HVM virtualization.
- `most_recent = true` to select the newest matching image at lookup time.

The data source has `count = 0` when LocalStack is selected, avoiding a real AWS AMI lookup for the emulator. The EC2 resource then uses `var.localstack_ami_id` for LocalStack and the data source result for AWS.

Because the AWS AMI lookup selects the latest matching image, a later plan may detect a changed AMI if Canonical publishes a newer matching image. `most_recent` does not update an already-running instance in place; an AMI change can lead Terraform to plan an instance replacement.

### 9.2 Instance type

The default instance type is `t3.micro`, controlled by `var.instance_type`.

### 9.3 Subnet, security group and instance profile

The instance is configured with:

- `subnet_id = aws_subnet.public.id`
- `vpc_security_group_ids = [aws_security_group.uploads_app.id]`
- `iam_instance_profile = aws_iam_instance_profile.uploads_app.name`

The references also establish Terraform dependencies: the subnet, security group and instance profile must exist before the instance can be created.

### 9.4 Public IP and Elastic IP

The EC2 resource sets `associate_public_ip_address` conditionally:

- For LocalStack, it is `true` to accommodate the LocalStack EC2 behaviour encountered during testing.
- For AWS, it is `false`, because the configuration explicitly allocates and associates an Elastic IP.

The public subnet's `map_public_ip_on_launch` setting is a subnet default; the explicit instance-level setting controls this instance's automatic public-IP association.

`aws_eip.uploads_app` allocates an Elastic IP for the VPC. `aws_eip_association.uploads_app` associates it with the EC2 instance.

A LocalStack output such as `127.145.15.133` is an emulator-mapped address, not a real public EC2 address and not proof of public internet reachability.

### 9.5 Root volume

The root block device is configured as:

| Setting | Value | Meaning |
|---|---|---|
| Size | 8 GiB | Root volume capacity |
| Type | `gp3` | General Purpose SSD volume type |
| Encryption | Enabled | Encrypt the EBS root volume |
| Delete on termination | `true` | Remove the root volume when the EC2 instance is terminated |

The 8 GiB size was selected for the current practice configuration. Reassess it before a real deployment: Ubuntu, Docker images, application files and PostgreSQL data can require more space. A production design should also decide explicitly where database data is persisted and how it is backed up.

### 9.6 Instance metadata service

The instance metadata options set:

```hcl
metadata_options {
  http_endpoint = "enabled"
  http_tokens   = "required"
}
```

Requiring a token enforces IMDSv2 for instance metadata requests. This is a security hardening measure that reduces exposure to certain classes of metadata-service request abuse.

## 10. EC2 user data: installing Docker

The EC2 resource supplies `terraform/user_data.sh` through:

```hcl
user_data                   = file("${path.module}/user_data.sh")
user_data_replace_on_change = true
```

`path.module` refers to the directory of the Terraform module, so the script path resolves relative to the Terraform configuration directory.

The script:

1. Runs `apt-get update`.
2. Installs `ca-certificates` and `curl`.
3. Creates `/etc/apt/keyrings`.
4. Downloads Docker's Ubuntu repository signing key.
5. Adds Docker's official Ubuntu APT repository using the instance's Ubuntu codename and architecture.
6. Updates package metadata again.
7. Installs Docker Engine, the Docker CLI, containerd, Buildx and the Docker Compose plugin.
8. Enables and starts the Docker service.

`user_data_replace_on_change = true` means a change to the user-data content causes Terraform to replace the EC2 instance so the updated first-boot script can run on a new instance. This is consequential: changing the script is not simply an in-place edit to the existing server.

LocalStack's mocked EC2 resource does not execute this script as a real Ubuntu boot would. 

## 11. Outputs

`outputs.tf` exposes:

| Output | Value |
|---|---|
| `uploads_bucket_name` | S3 bucket name |
| `uploads_bucket_arn` | S3 bucket ARN |
| `instance_id` | EC2 instance ID |
| `instance_public_ip` | EC2 instance public IP field |
| `instance_elastic_ip` | Allocated Elastic IP address |

Retrieve them with:

```bash
./tf-localstack.sh output
```

The values are useful for identifying resources and for later deployment automation. LocalStack-generated IDs and addresses may change when its resources are reset and recreated.

## 12. Terraform workflow used

The workflow used during development was:

```bash
# Format Terraform files in the current directory
./tf-localstack.sh fmt

# Check the configuration
./tf-localstack.sh validate

# Preview proposed changes
./tf-localstack.sh plan

# Apply the proposed changes
./tf-localstack.sh apply

# Inspect outputs
./tf-localstack.sh output

# Confirm the configuration is converged
./tf-localstack.sh plan
```

All Terraform files are currently in the same `terraform/` directory, so `terraform fmt` is sufficient. `terraform fmt -recursive` is only needed when formatting Terraform files in nested directories as well.

The final plan after a successful apply reported:

```text
No changes. Your infrastructure matches the configuration.
```

This means Terraform found no planned differences between the configuration and the state after refreshing the resources through the configured provider. It is a useful convergence check, but it is not an end-to-end functional test of AWS networking or EC2 boot behaviour.

### Terraform state

No remote backend is configured in the current provider configuration, so Terraform uses its default local state backend. The state file is part of Terraform's record of managed resources and must be protected. It can contain sensitive resource attributes even when outputs or variables are marked sensitive.

The repository `.gitignore` excludes `.terraform/`, Terraform state files, `.tfvars`, plan files and CLI override files. Keep `.env.terraform` and any real AWS credentials out of version control as well. Do not commit `terraform.tfstate` or state backups.


## 13. Deployment work not included yet

The current infrastructure prepares an EC2 host, but it does not yet deploy and run the complete application.

The current `deploy.sh` accepts an image tag and pulls:

```text
ghcr.io/bijitakc/secure-upload-app:<image-tag>
```

It does not:

- Build or publish an Nginx image.
- Create or populate a production environment file.
- Retrieve production secrets from SSM Parameter Store or Secrets Manager.
- Start the application and database containers.
- Configure or verify a production reverse proxy and TLS listener.
- Run database migrations or health checks.
- Perform deployment orchestration through SSM.

These are follow-up deployment tasks, not completed features of the current Terraform milestone.
