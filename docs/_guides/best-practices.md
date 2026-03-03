---
title: Best Practices
description: Workspace organization, file structure, recommended workflows, and AI assistant tips
order: 10
---

# Best Practices Guide

Recommendations for getting the most out of Terry-Form MCP.

## Workspace Organization

### Recommended Structure

Organize your `/mnt/workspace` with a clear directory structure:

```
/mnt/workspace/
├── shared-modules/           # Reusable modules
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── security-group/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev/
│   │   ├── main.tf          # Uses shared modules
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── prod/
└── experiments/              # Scratch space for learning
    └── test-project/
```

### File Naming Conventions

| File | Purpose |
|------|---------|
| `main.tf` | Primary resource definitions |
| `variables.tf` | Input variable declarations |
| `outputs.tf` | Output value declarations |
| `providers.tf` | Provider configuration |
| `versions.tf` | Terraform and provider version constraints |
| `locals.tf` | Local values |
| `data.tf` | Data source definitions |
| `terraform.tfvars` | Variable values (never commit secrets) |

## Recommended Workflow

### The init-validate-plan Pattern

Always follow this sequence:

```json
{
  "path": "environments/dev",
  "actions": ["init", "validate", "plan"],
  "vars": {"environment": "dev"}
}
```

1. **init**: Downloads providers, initializes backend
2. **validate**: Checks HCL syntax and configuration
3. **plan**: Shows what would change

### Analysis Pipeline

After the basic workflow, run analysis tools:

1. `terry_analyze` — Check for best practices (variable descriptions, hardcoded values, missing tags)
2. `terry_security_scan` — Find security vulnerabilities (public buckets, open security groups, unencrypted resources)
3. `terry_recommendations` — Get improvement suggestions for security, cost, performance, or reliability

### Format Before Committing

Always format before validation:

```json
{
  "path": "my-project",
  "actions": ["fmt", "validate"]
}
```

## Working with AI Assistants

### Be Specific

Instead of:
> "Check my Terraform"

Try:
> "Validate and plan my Terraform configuration in environments/dev with variable environment=development"

### Use Discovery Tools First

Start new sessions by discovering what's available:

1. `terry_environment_check` — Verify the environment is healthy
2. `terry_workspace_list` — See all available workspaces
3. `terry_workspace_info` — Understand a specific workspace's structure

### Leverage LSP Features

Ask your AI assistant to use LSP tools for code intelligence:

> "Can you check the documentation for the aws_instance resource type at line 15 of my main.tf?"

This uses `terraform_hover` to get provider documentation directly.

### Iterative Development

Build configurations incrementally:

1. Start with a minimal `main.tf` (provider block only)
2. `init` to download providers
3. Add resources one at a time
4. `validate` after each addition
5. `plan` when ready to review

## Security Best Practices

### Variable Descriptions

Always add descriptions to variables. The `terry_analyze` tool checks for this:

```hcl
# Good
variable "instance_type" {
  description = "EC2 instance type for web servers"
  type        = string
  default     = "t3.micro"
}

# Bad - will trigger a warning
variable "instance_type" {
  type    = string
  default = "t3.micro"
}
```

### Avoid Hardcoded Values

Don't hardcode AMI IDs, instance IDs, or VPC IDs. Use variables or data sources:

```hcl
# Good
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-amd64-server-*"]
  }
}

# Bad - will trigger a warning
resource "aws_instance" "web" {
  ami = "ami-0123456789abcdef0"
}
```

### Tag All Resources

Add tags to every taggable resource:

```hcl
resource "aws_instance" "web" {
  # ... configuration ...

  tags = {
    Name        = "${var.project_name}-web"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
```

### Use Default Tags

Configure default tags in the provider block:

```hcl
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
```

## Performance Tips

### Minimize Workspace Size

- Keep only relevant `.tf` files in each workspace
- Use a modular structure with small, focused workspaces
- Large monolithic workspaces slow down `init`, `plan`, and LSP operations

### Pre-initialize Workspaces

If you'll use the same workspace repeatedly, run `init` once and reuse:

```json
{"path": "my-project", "actions": ["init"]}
```

Subsequent operations skip provider downloads.

### Warm Up LSP

If you plan to use LSP features, initialize early:

```json
{"tool": "terry_lsp_init", "arguments": {"workspace_path": "my-project"}}
```

This avoids the 1-2 second startup delay on the first LSP call.

## What Terry-Form MCP Is NOT For

- **Applying changes** — Use your CI/CD pipeline or manual `terraform apply`
- **State management** — Managing remote state backends, state locking
- **Secret management** — Use dedicated tools (Vault, AWS Secrets Manager)
- **Monitoring** — Use your existing monitoring stack
- **Multi-tenancy** — Each container is single-user, single-session
