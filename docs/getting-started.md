---
layout: page
title: Getting Started
description: Quick start guide for Terry-Form MCP v3.1.0
toc: true
---

# Getting Started with Terry-Form MCP

Welcome to Terry-Form MCP! This guide will help you get up and running quickly.

## Prerequisites

Before you begin, ensure you have:

- **Docker** (recommended) or Python {{ site.data.project.python }}
- An AI assistant that supports MCP (Claude Desktop, etc.)
- A workspace directory for your Terraform configurations

## Installation

### Option 1: Docker (Recommended)

Docker provides the easiest and most secure way to run Terry-Form MCP.

```bash
# Clone the repository
git clone {{ site.data.project.repo_url }}.git
cd terry-form-mcp

# Build the image
scripts/build.sh

# Verify the build (8 checks)
scripts/verify.sh
```

### Option 2: Local Development

For development or testing:

```bash
# Clone the repository
git clone {{ site.data.project.repo_url }}.git
cd terry-form-mcp

# Install dependencies (requires Python {{ site.data.project.python }})
pip install -r requirements.txt

# Run the server directly
python3 src/server_enhanced_with_lsp.py
```

## Configuration

### MCP Client Configuration

Configure your AI assistant to use Terry-Form MCP. For Claude Desktop, edit your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/workspace:/mnt/workspace",
        "terry-form-mcp:latest"
      ]
    }
  }
}
```

<div class="alert alert-info">
<strong>Note</strong><br>
Terry-Form MCP uses stdio transport for the MCP protocol. The Docker container runs interactively (<code>-i</code>) and is invoked by your MCP client — it is not a daemon or HTTP server.
</div>

### Environment Variables

Optional environment variables for extended features:

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_APP_ID` | GitHub App ID for repo integration | No |
| `GITHUB_APP_INSTALLATION_ID` | GitHub App installation ID | No |
| `GITHUB_APP_PRIVATE_KEY` | GitHub App private key (PEM) | No |
| `TF_CLOUD_TOKEN` | Terraform Cloud API token | No |
| `LOG_LEVEL` | Logging level (INFO, DEBUG) | No |

### Forced Environment Variables

These are always set inside the container and cannot be overridden:

| Variable | Value | Purpose |
|----------|-------|---------|
| `TF_IN_AUTOMATION` | `true` | Suppresses interactive prompts |
| `TF_INPUT` | `false` | Prevents input requests |
| `CHECKPOINT_DISABLE` | `true` | Disables Terraform update checks |

### Security Configuration

Terry-Form MCP includes several security features by default:

- **Allowed actions**: `init`, `validate`, `plan`, `fmt`, `show`, `graph`, `providers`, `version`
- **Blocked actions**: `apply`, `destroy`, `import`, `taint`, `untaint`
- **Path validation**: All paths restricted to `/mnt/workspace`
- **Input sanitization**: Dangerous characters blocked in variable values
- **Rate limiting**: {{ site.data.project.rate_limits.terraform }} req/min (Terraform), {{ site.data.project.rate_limits.github }} req/min (GitHub)

## Your First Terraform Operation

### 1. Create a Simple Configuration

Create a file `workspace/main.tf`:

```hcl
terraform {
  required_version = ">= 1.0"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "my-first-project"
}

output "project_info" {
  value = "Project: ${var.project_name}"
}
```

### 2. Use Terry-Form with Your AI Assistant

Ask your AI assistant:

```
Can you help me validate and plan my Terraform configuration in the workspace directory?
```

The assistant will use Terry-Form MCP to:
1. Initialize the Terraform workspace (`terry` with `actions: ["init"]`)
2. Validate the configuration (`terry` with `actions: ["validate"]`)
3. Generate an execution plan (`terry` with `actions: ["plan"]`)
4. Provide feedback and recommendations

### 3. Example Response

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
    },
    {
      "action": "plan",
      "success": true,
      "plan_summary": {
        "add": 0,
        "change": 0,
        "destroy": 0
      }
    }
  ]
}
```

## Common Use Cases

### Managing Multiple Environments

Ask your AI assistant to plan different environments:

```
Plan my Terraform configuration at "environments/dev" with variable env="development"
```

```
Plan my Terraform configuration at "environments/prod" with variable env="production"
```

### Working with Modules

```hcl
# workspace/modules/vpc/main.tf
module "vpc" {
  source = "./modules/vpc"

  cidr_block  = var.vpc_cidr
  environment = var.environment
}
```

### GitHub Integration

If you've configured GitHub App integration:

```
Clone the repository myorg/infrastructure from GitHub and list its Terraform files
```

The assistant will use `github_clone_repo` followed by `github_list_terraform_files`.

## Troubleshooting

### Common Issues

<div class="alert alert-info">
<strong>Permission Denied</strong><br>
Ensure the workspace directory has proper permissions. The container runs as UID {{ site.data.project.container_uid }}:
<code>chmod -R 755 /path/to/workspace</code>
</div>

<div class="alert alert-warning">
<strong>Terraform Not Found</strong><br>
If using Docker, Terraform {{ site.data.project.terraform }} is included in the image. For local setup, install Terraform separately.
</div>

<div class="alert alert-danger">
<strong>MCP Connection Failed</strong><br>
Ensure Docker is running and the image is built. Test with:
<code>docker run -i --rm terry-form-mcp:latest python3 -c "print('OK')"</code>
</div>

### Debug Mode

Enable debug logging:

```bash
docker run -i --rm \
  -e LOG_LEVEL=DEBUG \
  -v /path/to/workspace:/mnt/workspace \
  terry-form-mcp:latest
```

## Best Practices

1. **Use Version Control**: Always version control your Terraform configurations
2. **Plan Before Apply**: Review plans carefully (apply is blocked by design)
3. **Use Workspaces**: Separate environments using directory structure
4. **Secure Secrets**: Pass cloud credentials via environment variables
5. **Regular Updates**: Keep the Docker image updated for security patches

## Next Steps

- Read the [Architecture Overview]({{ site.baseurl }}/architecture/)
- Review the [Security Guide]({{ site.baseurl }}/guides/security)
- Try the [First Project Tutorial]({{ site.baseurl }}/tutorials/first-project)
- Explore the [API Reference]({{ site.baseurl }}/api/mcp-tools)

## Getting Help

- [GitHub Discussions]({{ site.data.project.repo_url }}/discussions)
- [Report Issues]({{ site.data.project.repo_url }}/issues)

---

<div class="alert alert-success">
<strong>Congratulations!</strong><br>
You've successfully set up Terry-Form MCP. Start exploring its features and automate your infrastructure with confidence!
</div>
