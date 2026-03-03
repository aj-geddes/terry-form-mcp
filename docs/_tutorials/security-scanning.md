---
title: Security Scanning Pipeline
description: Use Terry-Form's analysis tools to find vulnerabilities and enforce best practices
order: 3
duration: 20 minutes
difficulty: intermediate
prerequisites:
  - Terry-Form MCP installed and configured
  - A Terraform workspace with AWS resources
  - Completed the "Your First Project" tutorial
topics:
  - security
  - analysis
  - best-practices
---

# Security Scanning Pipeline

This tutorial teaches you to use Terry-Form MCP's three analysis tools — `terry_analyze`, `terry_security_scan`, and `terry_recommendations` — to build a comprehensive security review pipeline.

## What You'll Learn

- How to check for best practice violations with `terry_analyze`
- How to scan for security vulnerabilities with `terry_security_scan`
- How to get improvement suggestions with `terry_recommendations`
- How to combine all three into an analysis pipeline

## The Three Analysis Tools

| Tool | Purpose | Checks |
|------|---------|--------|
| `terry_analyze` | Best practices | Variable descriptions, hardcoded values, missing tags |
| `terry_security_scan` | Security vulnerabilities | Public buckets, open security groups, unencrypted resources |
| `terry_recommendations` | Improvement suggestions | Security, cost, performance, reliability improvements |

## Step 1: Create a Test Configuration

Create a workspace with intentional issues to scan:

```
workspace/
└── security-tutorial/
    ├── main.tf
    ├── variables.tf
    └── storage.tf
```

**main.tf:**
```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "t3.micro"

  tags = {
    Name = "web-server"
  }
}

resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Web security group"

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

**variables.tf:**
```hcl
variable "instance_type" {
  type    = string
  default = "t3.micro"
}
```

**storage.tf:**
```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-app-data-bucket"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
```

This configuration has several deliberate issues. Let's find them.

## Step 2: Run Best Practice Analysis

Ask your AI assistant:

> "Analyze the Terraform configuration in security-tutorial for best practice issues"

The assistant calls `terry_analyze`:

```json
{
  "tool": "terry_analyze",
  "arguments": {
    "path": "security-tutorial"
  }
}
```

Expected findings:

```json
{
  "analysis": {
    "total_issues": 4,
    "issues": [
      {
        "severity": "warning",
        "type": "best_practice",
        "file": "variables.tf",
        "message": "Variable 'instance_type' is missing a description"
      },
      {
        "severity": "warning",
        "type": "hardcoded_value",
        "file": "main.tf",
        "message": "Hardcoded AMI ID detected: ami-0123456789abcdef0"
      },
      {
        "severity": "warning",
        "type": "hardcoded_value",
        "file": "main.tf",
        "message": "Hardcoded region in provider block"
      },
      {
        "severity": "info",
        "type": "best_practice",
        "file": "main.tf",
        "message": "Consider using default_tags in provider block"
      }
    ]
  }
}
```

### What It Found

1. **Missing variable description** — `instance_type` has no `description` attribute
2. **Hardcoded AMI** — AMI IDs should be variables or data sources
3. **Hardcoded region** — Region should come from a variable
4. **No default tags** — Provider should set default tags for consistency

## Step 3: Run Security Scan

Now scan for security vulnerabilities:

> "Run a security scan on security-tutorial with medium severity"

```json
{
  "tool": "terry_security_scan",
  "arguments": {
    "path": "security-tutorial",
    "severity": "medium"
  }
}
```

Expected findings:

```json
{
  "security_scan": {
    "total_findings": 3,
    "findings": [
      {
        "severity": "high",
        "type": "open_security_group",
        "resource": "aws_security_group.web",
        "message": "Security group allows all inbound traffic (0.0.0.0/0 on all ports)",
        "recommendation": "Restrict ingress to specific ports and CIDR ranges"
      },
      {
        "severity": "high",
        "type": "public_bucket",
        "resource": "aws_s3_bucket_public_access_block.data",
        "message": "S3 bucket public access block is disabled",
        "recommendation": "Set all public access block settings to true"
      },
      {
        "severity": "medium",
        "type": "unencrypted_resource",
        "resource": "aws_s3_bucket.data",
        "message": "S3 bucket does not have server-side encryption configured",
        "recommendation": "Enable SSE-S3 or SSE-KMS encryption"
      }
    ]
  }
}
```

### What It Found

1. **Open security group** (HIGH) — All traffic allowed from anywhere on all ports
2. **Public S3 bucket** (HIGH) — Public access block is disabled
3. **Unencrypted storage** (MEDIUM) — S3 bucket has no encryption configured

The `severity` parameter filters results: `"high"` shows only high severity, `"medium"` shows medium and above, `"low"` shows everything.

## Step 4: Get Recommendations

Ask for improvement suggestions across multiple categories:

> "Get security and cost recommendations for security-tutorial"

```json
{
  "tool": "terry_recommendations",
  "arguments": {
    "path": "security-tutorial",
    "category": "security"
  }
}
```

Then run again for cost:

```json
{
  "tool": "terry_recommendations",
  "arguments": {
    "path": "security-tutorial",
    "category": "cost"
  }
}
```

Available categories: `security`, `cost`, `performance`, `reliability`.

## Step 5: Fix the Issues

Now let's fix every finding. Update your files:

**main.tf** (fixed):
```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  vpc_security_group_ids = [aws_security_group.web.id]

  tags = {
    Name = "${var.project_name}-web"
  }
}

resource "aws_security_group" "web" {
  name_prefix = "${var.project_name}-web-"
  description = "Security group for web servers"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
    description = "HTTPS from allowed range"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
    description = "HTTP from allowed range"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}
```

**variables.tf** (fixed):
```hcl
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project for resource tagging"
  type        = string
  default     = "security-tutorial"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "instance_type" {
  description = "EC2 instance type for web servers"
  type        = string
  default     = "t3.micro"
}

variable "allowed_cidr" {
  description = "CIDR block allowed to access web servers"
  type        = string
  default     = "10.0.0.0/8"
}
```

**storage.tf** (fixed):
```hcl
resource "aws_s3_bucket" "data" {
  bucket_prefix = "${var.project_name}-data-"

  tags = {
    Name = "${var.project_name}-data"
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}
```

## Step 6: Re-scan to Verify

Run all three tools again to confirm the fixes:

> "Run a full analysis pipeline on security-tutorial: analyze, security scan, and recommendations"

The assistant runs all three sequentially:

```json
{"tool": "terry_analyze", "arguments": {"path": "security-tutorial"}}
```
```json
{"tool": "terry_security_scan", "arguments": {"path": "security-tutorial", "severity": "low"}}
```
```json
{"tool": "terry_recommendations", "arguments": {"path": "security-tutorial", "category": "security"}}
```

All three should report zero or minimal issues.

## The Analysis Pipeline Pattern

For any Terraform workspace, use this three-step pattern:

1. **`terry_analyze`** — Are we following best practices?
2. **`terry_security_scan`** — Are there security vulnerabilities?
3. **`terry_recommendations`** — What else can we improve?

This is the same pattern used in the [CI/CD Integration Guide]({{ site.baseurl }}/guides/ci-cd-integration/) for automated pull request checks.

## Summary

In this tutorial, you learned how to:

- Use `terry_analyze` to find best practice violations
- Use `terry_security_scan` to identify security vulnerabilities
- Use `terry_recommendations` to get improvement suggestions
- Fix common issues: open security groups, public S3 buckets, hardcoded values
- Re-scan to verify your fixes

## Next Steps

- [Module Development]({{ site.baseurl }}/tutorials/module-development/) — Build reusable Terraform modules
- [GitHub Actions Pipeline]({{ site.baseurl }}/tutorials/github-actions-pipeline/) — Automate scanning in CI/CD
- [Security Guide]({{ site.baseurl }}/guides/security/) — Comprehensive security reference

---

<div class="tutorial-nav">
  <a href="{{ site.baseurl }}/tutorials/aws-infrastructure/" class="btn">← AWS Infrastructure</a>
  <a href="{{ site.baseurl }}/tutorials/module-development/" class="btn btn-primary">Next: Module Development →</a>
</div>
