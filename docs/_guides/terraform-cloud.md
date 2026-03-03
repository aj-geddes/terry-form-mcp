---
title: Terraform Cloud
description: All 4 Terraform Cloud tools for workspace monitoring and state output retrieval
order: 7
---

# Terraform Cloud Guide

Terry-Form MCP can connect to Terraform Cloud to list workspaces, view runs, and retrieve state outputs.

## Overview

4 Terraform Cloud tools are available:

| Tool | Description |
|------|-------------|
| `tf_cloud_list_workspaces` | List organization workspaces |
| `tf_cloud_get_workspace` | Get workspace details |
| `tf_cloud_list_runs` | List runs for a workspace |
| `tf_cloud_get_state_outputs` | Get state outputs |

## Configuration

Set the `TF_CLOUD_TOKEN` environment variable:

```bash
export TF_CLOUD_TOKEN="your-terraform-cloud-api-token"
```

In Docker:
```bash
docker run -i --rm \
  -v /path/to/workspace:/mnt/workspace \
  -e TF_CLOUD_TOKEN="your-token" \
  terry-form-mcp:latest
```

Generate a token at: [app.terraform.io/settings/tokens](https://app.terraform.io/app/settings/tokens)

## Listing Workspaces

```json
{
  "tool": "tf_cloud_list_workspaces",
  "arguments": {
    "organization": "my-org",
    "limit": 20
  }
}
```

Response:
```json
{
  "workspaces": [
    {
      "id": "ws-abc123",
      "name": "production-vpc",
      "environment": "production",
      "terraform_version": "1.12.0",
      "current_run": {
        "id": "run-xyz789",
        "status": "applied",
        "created_at": "2025-01-15T10:30:00Z"
      },
      "resource_count": 42,
      "auto_apply": false
    }
  ]
}
```

## Getting Workspace Details

```json
{
  "tool": "tf_cloud_get_workspace",
  "arguments": {
    "organization": "my-org",
    "workspace": "production-vpc"
  }
}
```

Returns detailed information including VCS repo, execution mode, working directory, tags, and current state version.

## Listing Runs

```json
{
  "tool": "tf_cloud_list_runs",
  "arguments": {
    "organization": "my-org",
    "workspace": "production-vpc",
    "limit": 10
  }
}
```

Response includes run status, resource changes, and cost estimation (if available):

```json
{
  "runs": [
    {
      "id": "run-xyz789",
      "status": "applied",
      "created_at": "2025-01-15T10:30:00Z",
      "message": "Update VPC CIDR ranges",
      "has_changes": true,
      "resource_additions": 2,
      "resource_changes": 1,
      "resource_destructions": 0
    }
  ]
}
```

## Getting State Outputs

```json
{
  "tool": "tf_cloud_get_state_outputs",
  "arguments": {
    "organization": "my-org",
    "workspace": "production-vpc"
  }
}
```

Response:
```json
{
  "outputs": {
    "vpc_id": {
      "value": "vpc-12345678",
      "type": "string",
      "sensitive": false
    },
    "database_endpoint": {
      "value": "[SENSITIVE]",
      "type": "string",
      "sensitive": true
    }
  }
}
```

Sensitive outputs are masked in the response.

## Rate Limits

| Limit | Value |
|-------|-------|
| Terry-Form internal | {{ site.data.project.rate_limits.tf_cloud }} requests/minute |
| Terraform Cloud API | 30 requests/second |

## Limitations

- **Read-only access**: These tools only read data from Terraform Cloud. They do not trigger runs, approve applies, or modify configuration.
- **Token scope**: The API token must have appropriate permissions for the organization and workspaces you want to access.
- **No run triggers**: To trigger new runs, use the Terraform Cloud UI or API directly.
