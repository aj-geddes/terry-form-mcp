---
title: Terraform Module Development
description: Build, validate, and test reusable Terraform modules using LSP features
order: 4
duration: 25 minutes
difficulty: intermediate
prerequisites:
  - Terry-Form MCP installed and configured
  - Completed the "Your First Project" tutorial
  - Understanding of Terraform resource blocks
topics:
  - modules
  - lsp
  - validation
---

# Terraform Module Development

This tutorial walks you through building a reusable Terraform module, validating it with Terry-Form MCP, and using LSP features for code intelligence during development.

## What You'll Learn

- How to structure a Terraform module
- How to use LSP hover and completions for faster development
- How to validate modules with `terry`
- How to test modules by calling them from a root configuration

## Module Architecture

We'll build a VPC module that creates a complete network setup:

```mermaid
graph TB
    subgraph "Module: vpc"
        A[VPC] --> B[Internet Gateway]
        A --> C[Public Subnets]
        A --> D[Private Subnets]
        C --> E[Public Route Table]
        D --> F[Private Route Table]
        B --> E
    end

    subgraph "Root Configuration"
        G[module "vpc"] --> A
        G --> H[Variables passed in]
        A --> I[Outputs returned]
    end
```

## Step 1: Create the Module Structure

Set up your workspace:

```
workspace/
├── modules/
│   └── vpc/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    └── dev/
        ├── main.tf
        └── variables.tf
```

## Step 2: Define Module Variables

Start with the module's interface — its input variables.

**modules/vpc/variables.tf:**
```hcl
variable "name" {
  description = "Name prefix for all VPC resources"
  type        = string

  validation {
    condition     = length(var.name) > 0 && length(var.name) <= 32
    error_message = "Name must be between 1 and 32 characters."
  }
}

variable "cidr_block" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "Must be a valid CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
}

variable "enable_nat_gateway" {
  description = "Whether to create a NAT gateway for private subnets"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
```

### Use LSP Hover for Documentation

While writing resource blocks, ask your assistant to check documentation:

> "Can you hover over the aws_vpc resource type at line 1 of modules/vpc/main.tf to see its documentation?"

```json
{
  "tool": "terraform_hover",
  "arguments": {
    "file_path": "modules/vpc/main.tf",
    "line": 0,
    "character": 10
  }
}
```

This returns provider documentation for the `aws_vpc` resource, including all available attributes.

## Step 3: Create Module Resources

**modules/vpc/main.tf:**
```hcl
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.name}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-igw"
  })
}

resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.name}-public-${count.index + 1}"
    Type = "public"
  })
}

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.name}-private-${count.index + 1}"
    Type = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, {
    Name = "${var.name}-public-rt"
  })
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-private-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name}-nat-eip"
  })
}

resource "aws_nat_gateway" "this" {
  count = var.enable_nat_gateway ? 1 : 0

  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  tags = merge(var.tags, {
    Name = "${var.name}-nat"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route" "private_nat" {
  count = var.enable_nat_gateway ? 1 : 0

  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[0].id
}
```

## Step 4: Define Module Outputs

**modules/vpc/outputs.tf:**
```hcl
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.this.id
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway (null if disabled)"
  value       = var.enable_nat_gateway ? aws_nat_gateway.this[0].id : null
}
```

## Step 5: Use LSP Completions

While editing, use LSP completions to discover available attributes:

> "Get Terraform completions in modules/vpc/main.tf at line 3, character 2 to see what attributes aws_vpc supports"

```json
{
  "tool": "terraform_complete",
  "arguments": {
    "file_path": "modules/vpc/main.tf",
    "line": 2,
    "character": 2
  }
}
```

This returns available attributes like `assign_generated_ipv6_cidr_block`, `enable_dns_hostnames`, `instance_tenancy`, and more.

## Step 6: Validate the Module

Initialize and validate the module in isolation:

> "Initialize and validate the VPC module at modules/vpc"

```json
{
  "tool": "terry",
  "arguments": {
    "path": "modules/vpc",
    "actions": ["init", "validate"]
  }
}
```

{% include alert.html type="info" title="Note" content="Validating a module directory directly checks HCL syntax and variable declarations, but won't catch errors that depend on how the module is called (like missing required variables)." %}

## Step 7: Call the Module

Create a root configuration that uses your module.

**environments/dev/main.tf:**
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
      Project     = "module-tutorial"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

module "vpc" {
  source = "../../modules/vpc"

  name               = "module-tutorial"
  cidr_block         = "10.0.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b"]

  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]

  enable_nat_gateway = var.environment == "prod"

  tags = {
    Environment = var.environment
  }
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnets" {
  value = module.vpc.public_subnet_ids
}

output "private_subnets" {
  value = module.vpc.private_subnet_ids
}
```

**environments/dev/variables.tf:**
```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
```

## Step 8: Validate the Full Configuration

Now validate the root configuration with the module:

> "Initialize and plan my dev environment at environments/dev"

```json
{
  "tool": "terry",
  "arguments": {
    "path": "environments/dev",
    "actions": ["init", "validate", "plan"],
    "vars": {"environment": "dev"}
  }
}
```

The plan will show all the resources the module creates — VPC, subnets, route tables, and internet gateway. Since `environment` is `"dev"`, the NAT gateway will be skipped.

## Step 9: Analyze the Module

Run the analysis tools on your module:

> "Analyze the VPC module for best practices"

```json
{
  "tool": "terry_analyze",
  "arguments": {
    "path": "modules/vpc"
  }
}
```

A well-structured module should pass with zero or minimal warnings because every variable has a description, resources use variables (not hardcoded values), and tags are applied via `merge()`.

## Step 10: Format the Code

Ensure consistent formatting:

> "Format the VPC module and the dev environment"

```json
{
  "tool": "terry",
  "arguments": {
    "path": "modules/vpc",
    "actions": ["fmt"]
  }
}
```

```json
{
  "tool": "terry",
  "arguments": {
    "path": "environments/dev",
    "actions": ["fmt"]
  }
}
```

## Module Best Practices

| Practice | Example |
|----------|---------|
| All variables have descriptions | `description = "CIDR block for the VPC"` |
| Use validation blocks | `validation { condition = ... }` |
| Use `merge()` for tags | `tags = merge(var.tags, { Name = "..." })` |
| Name resources `this` for single instances | `resource "aws_vpc" "this"` |
| Provide sensible defaults | `default = "10.0.0.0/16"` |
| Document every output | `description = "ID of the VPC"` |

## Summary

In this tutorial, you learned how to:

- Structure a reusable Terraform module with variables, resources, and outputs
- Use LSP hover and completions for provider documentation
- Validate modules both in isolation and as part of a root configuration
- Apply best practices: descriptions, validation blocks, tag merging

## Next Steps

- [GitHub Actions Pipeline]({{ site.baseurl }}/tutorials/github-actions-pipeline/) — Automate validation in CI/CD
- [Multi-Environment Setup]({{ site.baseurl }}/tutorials/multi-environment/) — Use modules across dev/staging/prod
- [LSP Integration Guide]({{ site.baseurl }}/guides/lsp-integration/) — Full LSP reference

---

<div class="tutorial-nav">
  <a href="{{ site.baseurl }}/tutorials/security-scanning/" class="btn">← Security Scanning</a>
  <a href="{{ site.baseurl }}/tutorials/github-actions-pipeline/" class="btn btn-primary">Next: GitHub Actions →</a>
</div>
