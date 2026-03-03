---
layout: page
title: API Reference
description: Complete API reference for Terry-Form MCP
---

# API Reference

Complete reference documentation for the {{ site.data.project.tool_count }} tools available through {{ site.title }}.

## MCP Protocol Tools

{% for api in site.api %}
{% if api.title != page.title %}
- [{{ api.title }}]({{ api.url | relative_url }}) -- {{ api.description }}
{% endif %}
{% endfor %}

## Quick Reference

### Core Terraform Tools ({{ site.data.project.tools.core }})

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `terry` | Execute Terraform operations | Plan, validate, format |
| `terry_workspace_list` | List available workspaces | Discovery |
| `terry_version` | Get Terraform version info | Compatibility check |

### Workspace and Diagnostics ({{ site.data.project.tools.diagnostics }})

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `terry_environment_check` | Check environment and dependencies | Health check |
| `terry_workspace_setup` | Create a structured workspace | Project scaffolding |
| `terry_workspace_info` | Get workspace details | Workspace inspection |
| `terry_file_check` | Validate file syntax and structure | File validation |
| `terry_lsp_init` | Initialize LSP client for a workspace | LSP setup |
| `terry_lsp_debug` | Get LSP debugging information | Troubleshooting |

### LSP Intelligence ({{ site.data.project.tools.lsp }})

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `terraform_validate_lsp` | Validate Terraform via LSP | Deep validation |
| `terraform_hover` | Get hover info at a position | Documentation lookup |
| `terraform_complete` | Get completion suggestions | Code assistance |
| `terraform_format_lsp` | Format a Terraform document | Code formatting |
| `terraform_lsp_status` | Get LSP server status | Status check |

### Analysis and Recommendations ({{ site.data.project.tools.security }})

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `terry_analyze` | Best practice analysis | Code quality |
| `terry_security_scan` | Security vulnerability scan | Security audit |
| `terry_recommendations` | Get improvement suggestions | Optimization |

### GitHub Integration ({{ site.data.project.tools.github }})

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `github_clone_repo` | Clone or update repositories | Repository management |
| `github_list_terraform_files` | List .tf files in a repository | Code discovery |
| `github_get_terraform_config` | Analyze Terraform configs | Code analysis |
| `github_prepare_workspace` | Prepare workspace from GitHub | Pipeline setup |

### Terraform Cloud ({{ site.data.project.tools.terraform_cloud }})

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `tf_cloud_list_workspaces` | List Terraform Cloud workspaces | Workspace discovery |
| `tf_cloud_get_workspace` | Get workspace details | Workspace inspection |
| `tf_cloud_list_runs` | List runs for a workspace | Run history |
| `tf_cloud_get_state_outputs` | Get state outputs | Output retrieval |

## Response Formats

All {{ site.title }} tools follow consistent response patterns.

### Success Response

```json
{
  "tool-name-results": {
    "success": true,
    "data": {
      // Tool-specific data
    },
    "metadata": {
      "duration": 1.234,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  }
}
```

### Error Response

```json
{
  "error": "Descriptive error message",
  "code": "ERROR_CODE",
  "details": {
    // Additional error context
  }
}
```

## Authentication

### MCP Protocol

{{ site.title }} communicates over the MCP protocol using **stdio transport**. No additional authentication is required for tool calls -- the MCP host manages the connection to the server process directly.

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "./workspace:/mnt/workspace",
        "terry-form-mcp:latest"
      ]
    }
  }
}
```

### GitHub App

To use GitHub integration tools, configure the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_APP_ID` | GitHub App ID | Yes |
| `GITHUB_APP_PRIVATE_KEY` | RSA private key for JWT signing | Yes |
| `GITHUB_INSTALLATION_ID` | Installation ID for the target org | Yes |

### Terraform Cloud

To use Terraform Cloud tools, set the `TF_CLOUD_TOKEN` environment variable with a valid Terraform Cloud API token.

| Variable | Description | Required |
|----------|-------------|----------|
| `TF_CLOUD_TOKEN` | Terraform Cloud API token | Yes |

## Rate Limits

{{ site.title }} enforces internal rate limits to protect against excessive resource usage. These limits are applied within the server process and are not exposed as HTTP headers.

| Category | Limit | Window |
|----------|-------|--------|
| Terraform Operations | {{ site.data.project.rate_limits.terraform }} requests | 1 minute |
| GitHub Operations | {{ site.data.project.rate_limits.github }} requests | 1 minute |
| Terraform Cloud | {{ site.data.project.rate_limits.tf_cloud }} requests | 1 minute |
| Default (all others) | {{ site.data.project.rate_limits.default }} requests | 1 minute |

When a rate limit is exceeded, the tool returns an error response with a `RATE_LIMIT_EXCEEDED` code indicating the category and remaining cooldown time.

## Common Patterns

### Sequential Operations

```json
{
  "tool": "terry",
  "arguments": {
    "path": "production",
    "actions": ["init", "validate", "plan"],
    "vars": { "environment": "prod" }
  }
}
```

### Workspace Discovery

```json
{
  "tool": "terry_workspace_list",
  "arguments": {}
}
```

### GitHub to Terraform Pipeline

1. Clone the repository with `github_clone_repo`
2. Prepare the workspace with `github_prepare_workspace`
3. Run Terraform operations with `terry`

### Security Validation Pipeline

1. Analyze configuration with `terry_analyze`
2. Run security scan with `terry_security_scan`
3. Get recommendations with `terry_recommendations`
4. If passing, proceed with `terry` plan

## Need Help?

- [Getting Started Guide]({{ site.baseurl }}/getting-started)
- [Community Discussions]({{ site.data.project.repo_url }}/discussions)
- [Report an Issue]({{ site.data.project.repo_url }}/issues)
