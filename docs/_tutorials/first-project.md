---
title: Your First Terry-Form Project
description: Build a Docker image, configure your AI assistant, and run your first Terraform validation
order: 1
duration: 15 minutes
difficulty: beginner
prerequisites:
  - Docker installed and running
  - An MCP-compatible AI assistant (Claude Desktop, VS Code with Continue, etc.)
  - Basic familiarity with the command line
topics:
  - docker
  - setup
  - validation
---

# Your First Terry-Form Project

This tutorial walks you through building Terry-Form MCP, connecting it to your AI assistant, and running your first Terraform init-validate-plan cycle.

## What You'll Learn

- How to build the Terry-Form MCP Docker image
- How to configure your AI assistant's MCP client
- How to create a basic Terraform configuration
- How to use the `terry` tool for init, validate, and plan

## Step 1: Build the Docker Image

Clone the repository and build the image:

```bash
git clone {{ site.data.project.repo_url }}.git
cd terry-form-mcp
docker build -t terry-form-mcp .
```

Verify the build succeeded:

```bash
docker images | grep terry-form-mcp
```

You should see an image around 150MB based on Alpine Linux.

## Step 2: Verify the Installation

Run the verification script to confirm everything is working:

```bash
scripts/verify.sh
```

This runs 8 checks: Docker availability, image size, Terraform version ({{ site.data.project.terraform }}), terraform-ls version ({{ site.data.project.terraform_ls }}), Python version ({{ site.data.project.python }}), required files, tool registration, and server startup.

## Step 3: Configure Your AI Assistant

Add Terry-Form MCP to your AI assistant's MCP configuration.

### Claude Desktop

Edit your Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add this configuration:

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/workspace:/mnt/workspace",
        "terry-form-mcp:latest"
      ]
    }
  }
}
```

Replace `/path/to/your/workspace` with the actual path where you'll store Terraform files.

{% include alert.html type="warning" title="Important" content="Always use the <code>-i</code> flag (interactive). Terry-Form MCP uses stdio for communication — it will exit immediately without <code>-i</code>. Do NOT use <code>-d</code> (detached mode)." %}

### Restart Your Assistant

After saving the configuration, restart your AI assistant. It should now have access to {{ site.data.project.tool_count }} Terry-Form tools.

## Step 4: Create a Terraform Configuration

Create a project directory in your workspace:

```
workspace/
└── hello-terraform/
    ├── main.tf
    └── variables.tf
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
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "hello-terraform"
      ManagedBy = "Terraform"
    }
  }
}

resource "aws_s3_bucket" "example" {
  bucket_prefix = "terry-form-tutorial-"

  tags = {
    Name = "terry-form-tutorial"
  }
}
```

**variables.tf:**
```hcl
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}
```

## Step 5: Initialize and Validate

Ask your AI assistant:

> "Initialize and validate my Terraform configuration in hello-terraform"

Behind the scenes, the assistant calls the `terry` tool:

```json
{
  "tool": "terry",
  "arguments": {
    "path": "hello-terraform",
    "actions": ["init", "validate"]
  }
}
```

Expected response:

```json
{
  "terry-results": [
    {
      "action": "init",
      "success": true,
      "stdout": "Terraform has been successfully initialized!"
    },
    {
      "action": "validate",
      "success": true,
      "stdout": "Success! The configuration is valid."
    }
  ]
}
```

## Step 6: Generate a Plan

Now ask your assistant:

> "Generate a Terraform plan for hello-terraform"

The assistant calls:

```json
{
  "tool": "terry",
  "arguments": {
    "path": "hello-terraform",
    "actions": ["plan"]
  }
}
```

The plan output shows what Terraform would create — in this case, one S3 bucket. No resources are actually created; Terry-Form MCP blocks `apply` and `destroy` operations for safety.

## Step 7: Check Your Work

Use the analysis tools to verify your configuration follows best practices:

> "Analyze my hello-terraform configuration"

The assistant uses `terry_analyze` to check for:

- Variables without descriptions
- Hardcoded values (AMI IDs, VPC IDs, etc.)
- Resources missing tags
- Other best practice violations

## What Just Happened?

You completed the standard Terry-Form workflow:

1. **init** — Downloaded the AWS provider plugin
2. **validate** — Verified the HCL syntax is correct
3. **plan** — Previewed what would be created
4. **analyze** — Checked for best practice violations

This init-validate-plan-analyze cycle is the foundation of all Terry-Form MCP workflows.

## Understanding the Safety Model

Terry-Form MCP is intentionally read-only:

| Allowed | Blocked |
|---------|---------|
| `init` | `apply` |
| `validate` | `destroy` |
| `fmt` | `import` |
| `plan` | `taint` |
| `show` | `untaint` |

To actually create infrastructure, run `terraform apply` through your standard deployment process or CI/CD pipeline.

## Next Steps

- [Building AWS Infrastructure]({{ site.baseurl }}/tutorials/aws-infrastructure/) — Create a full VPC with subnets, security groups, and load balancer
- [Security Scanning]({{ site.baseurl }}/tutorials/security-scanning/) — Learn to scan configurations for vulnerabilities
- [Configuration Guide]({{ site.baseurl }}/guides/configuration/) — All environment variables and options

---

<div class="tutorial-nav">
  <a href="{{ site.baseurl }}/tutorials/" class="btn">← Back to Tutorials</a>
  <a href="{{ site.baseurl }}/tutorials/aws-infrastructure/" class="btn btn-primary">Next: AWS Infrastructure →</a>
</div>
