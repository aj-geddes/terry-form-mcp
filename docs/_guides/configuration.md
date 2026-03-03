---
title: Configuration
description: Environment variables, MCP client config, Docker options, and rate limits
order: 2
---

# Configuration Guide

This guide covers all configuration options for Terry-Form MCP.

## MCP Client Configuration

Terry-Form MCP uses stdio transport for the MCP protocol. Configure your AI assistant to invoke it via Docker.

### Claude Desktop

Edit `claude_desktop_config.json`:

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

### With Cloud Credentials (AWS)

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/workspace:/mnt/workspace",
        "-e", "AWS_ACCESS_KEY_ID",
        "-e", "AWS_SECRET_ACCESS_KEY",
        "-e", "AWS_DEFAULT_REGION",
        "terry-form-mcp:latest"
      ]
    }
  }
}
```

### With GitHub Integration

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/workspace:/mnt/workspace",
        "-v", "/path/to/github-app.pem:/keys/github-app.pem:ro",
        "-e", "GITHUB_APP_ID=12345",
        "-e", "GITHUB_APP_INSTALLATION_ID=67890",
        "-e", "GITHUB_APP_PRIVATE_KEY_PATH=/keys/github-app.pem",
        "terry-form-mcp:latest"
      ]
    }
  }
}
```

## Environment Variables

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

### GitHub Integration

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_APP_ID` | GitHub App ID | For GitHub features |
| `GITHUB_APP_INSTALLATION_ID` | Installation ID | For GitHub features |
| `GITHUB_APP_PRIVATE_KEY` | PEM private key content | For GitHub features |
| `GITHUB_APP_PRIVATE_KEY_PATH` | Path to PEM key file | Alternative to above |

### Terraform Cloud

| Variable | Description | Required |
|----------|-------------|----------|
| `TF_CLOUD_TOKEN` | Terraform Cloud API token | For TF Cloud features |

### Cloud Provider Credentials

**AWS:**
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_DEFAULT_REGION`, `AWS_REGION`, `AWS_PROFILE`

**Google Cloud:**
`GOOGLE_CREDENTIALS`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_PROJECT`, `GOOGLE_REGION`, `GOOGLE_ZONE`

**Azure:**
`ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_SUBSCRIPTION_ID`, `ARM_TENANT_ID`

## Forced Environment Variables

These are always set inside the container and **cannot be overridden**:

| Variable | Value | Purpose |
|----------|-------|---------|
| `TF_IN_AUTOMATION` | `true` | Suppresses interactive prompts |
| `TF_INPUT` | `false` | Prevents input requests |
| `CHECKPOINT_DISABLE` | `true` | Disables update checks |

## Docker Options

### Basic Run

```bash
docker run -i --rm \
  -v /path/to/workspace:/mnt/workspace \
  terry-form-mcp:latest
```

### Security-Hardened Run

```bash
docker run -i --rm \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  --read-only \
  --tmpfs /tmp \
  -v /path/to/workspace:/mnt/workspace:rw \
  terry-form-mcp:latest
```

### With Resource Limits

```bash
docker run -i --rm \
  --memory=1g \
  --cpus=2 \
  -v /path/to/workspace:/mnt/workspace \
  terry-form-mcp:latest
```

## Rate Limits

Terry-Form MCP implements internal rate limiting to prevent abuse:

| Operation Type | Limit | Window |
|---------------|-------|--------|
| Terraform operations | {{ site.data.project.rate_limits.terraform }} requests | 1 minute |
| GitHub operations | {{ site.data.project.rate_limits.github }} requests | 1 minute |
| Terraform Cloud | {{ site.data.project.rate_limits.tf_cloud }} requests | 1 minute |
| Default | {{ site.data.project.rate_limits.default }} requests | 1 minute |

Rate limits are enforced per-process (not per-user). When a rate limit is exceeded, the tool returns an error response.

## Workspace Configuration

All Terraform operations are restricted to `/mnt/workspace`. The directory structure inside determines your available workspaces:

```
/mnt/workspace/
├── project-a/          # terry path: "project-a"
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── project-b/          # terry path: "project-b"
│   └── main.tf
└── environments/
    ├── dev/            # terry path: "environments/dev"
    └── prod/           # terry path: "environments/prod"
```

Use `terry_workspace_list` to discover all available workspaces.

## Allowed Terraform Actions

| Action | Allowed | Description |
|--------|---------|-------------|
| `init` | Yes | Initialize workspace |
| `validate` | Yes | Validate configuration |
| `plan` | Yes | Generate execution plan |
| `fmt` | Yes | Format files |
| `show` | Yes | Show current state |
| `graph` | Yes | Generate dependency graph |
| `providers` | Yes | List providers |
| `version` | Yes | Show version |
| `apply` | **Blocked** | Cannot be enabled |
| `destroy` | **Blocked** | Cannot be enabled |
| `import` | **Blocked** | Cannot be enabled |
| `taint` | **Blocked** | Cannot be enabled |
| `untaint` | **Blocked** | Cannot be enabled |

## Local Development

For development without Docker:

```bash
# Requires Python {{ site.data.project.python }}
pip install -r requirements.txt

# Run directly
python3 server_enhanced_with_lsp.py
```

<div class="alert alert-warning">
<strong>Note</strong><br>
Local development requires Terraform and terraform-ls to be installed separately. The Docker image includes both.
</div>
