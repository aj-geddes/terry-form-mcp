---
title: MCP Tools Reference
description: Complete reference for all 25 Terry-Form MCP tools
order: 1
---

# MCP Tools Reference

This document provides a complete reference for all {{ site.data.project.tool_count }} tools available through the {{ site.title }} server (v{{ site.data.project.version }}). The server communicates over MCP stdio transport -- all tools are invoked as MCP tool calls, not HTTP requests.

---

## Core Terraform Tools

### terry

The primary tool for executing Terraform operations. Supports `init`, `validate`, `fmt`, `plan`, `show`, `graph`, `providers`, and `version`. Destructive operations (`apply`, `destroy`) are intentionally blocked.

```typescript
interface TerryParams {
  path: string;                    // Workspace path relative to /mnt/workspace
  actions: string[];               // Array of Terraform actions to execute
  vars?: Record<string, any>;     // Terraform variables
}
```

**Supported Actions:**

| Action | Description |
|--------|-------------|
| `init` | Initialize Terraform workspace |
| `validate` | Validate configuration syntax |
| `fmt` | Format Terraform files |
| `plan` | Generate execution plan |
| `show` | Show current state |
| `graph` | Generate dependency graph |
| `providers` | List required providers |
| `version` | Show Terraform version |

**Example Usage:**

```json
{
  "tool": "terry",
  "arguments": {
    "path": "environments/production",
    "actions": ["init", "validate", "plan"],
    "vars": {
      "environment": "prod",
      "region": "us-east-1"
    }
  }
}
```

**Response Format:**

```json
{
  "terry-results": [
    {
      "action": "init",
      "success": true,
      "exit_code": 0,
      "stdout": "Terraform has been successfully initialized!",
      "stderr": "",
      "duration": 2.34
    },
    {
      "action": "plan",
      "success": true,
      "exit_code": 0,
      "plan_summary": {
        "add": 5,
        "change": 2,
        "destroy": 0
      },
      "resources": []
    }
  ]
}
```

---

### terry_workspace_list

List all available Terraform workspaces under `/mnt/workspace`.

```typescript
interface WorkspaceListParams {
  // No parameters required
}
```

**Example Usage:**

```json
{
  "tool": "terry_workspace_list",
  "arguments": {}
}
```

**Response:**

```json
{
  "workspaces": [
    {
      "path": "environments/dev",
      "initialized": true,
      "has_state": true,
      "last_modified": "2024-01-15T10:30:00Z",
      "providers": ["aws", "kubernetes"],
      "modules": 3
    }
  ]
}
```

---

### terry_version

Get Terraform version information and provider selections.

```typescript
interface VersionParams {
  // No parameters required
}
```

**Example Usage:**

```json
{
  "tool": "terry_version",
  "arguments": {}
}
```

**Response:**

```json
{
  "terraform_version": "{{ site.data.project.terraform }}",
  "platform": "linux_amd64",
  "provider_selections": {
    "aws": "5.31.0",
    "kubernetes": "2.24.0"
  }
}
```

---

## Workspace and Diagnostics Tools

### terry_environment_check

Check the {{ site.title }} environment and all dependencies.

```typescript
interface EnvironmentCheckParams {
  // No parameters required
}
```

**Example Usage:**

```json
{
  "tool": "terry_environment_check",
  "arguments": {}
}
```

**Response:**

```json
{
  "terry-environment": {
    "environment": {
      "working_directory": "/app",
      "user": "{{ site.data.project.container_user }}",
      "workspace_mount": true
    },
    "terraform": {
      "available": true,
      "path": "/usr/local/bin/terraform",
      "version": "Terraform v{{ site.data.project.terraform }}"
    },
    "terraform_ls": {
      "available": true,
      "version": "v{{ site.data.project.terraform_ls }}"
    },
    "container": {
      "is_docker": true,
      "hostname": "terry-form-abc123"
    }
  }
}
```

---

### terry_workspace_setup

Create a properly structured Terraform workspace with starter files.

```typescript
interface WorkspaceSetupParams {
  path: string;              // Workspace path relative to /mnt/workspace
  project_name?: string;     // Optional project name for file headers
}
```

**Example Usage:**

```json
{
  "tool": "terry_workspace_setup",
  "arguments": {
    "path": "my-project",
    "project_name": "My Infrastructure"
  }
}
```

**Response:**

```json
{
  "terry-workspace-setup": {
    "success": true,
    "workspace_path": "/mnt/workspace/my-project",
    "created_files": ["main.tf", "variables.tf", "outputs.tf"],
    "message": "Workspace setup complete. Created 3 files."
  }
}
```

---

### terry_workspace_info

Get detailed information about a Terraform workspace.

```typescript
interface WorkspaceInfoParams {
  path?: string;   // Workspace path, defaults to "."
}
```

**Example Usage:**

```json
{
  "tool": "terry_workspace_info",
  "arguments": {
    "path": "project1"
  }
}
```

**Response:**

```json
{
  "terry-workspace": {
    "path_info": {
      "requested_path": "project1",
      "full_path": "/mnt/workspace/project1",
      "exists": true,
      "is_directory": true
    },
    "terraform_files": ["main.tf", "variables.tf", "outputs.tf"],
    "terraform_state": {
      "initialized": true,
      "state_file_exists": true
    },
    "common_files": {
      "main.tf": true,
      "variables.tf": true,
      "outputs.tf": true
    }
  }
}
```

---

### terry_file_check

Validate a Terraform file's syntax and structure.

```typescript
interface FileCheckParams {
  file_path: string;   // Path to the Terraform file
}
```

**Example Usage:**

```json
{
  "tool": "terry_file_check",
  "arguments": {
    "file_path": "main.tf"
  }
}
```

**Response:**

```json
{
  "terry-file-check": {
    "file_path": "main.tf",
    "exists": true,
    "readable": true,
    "size_bytes": 2048,
    "syntax_valid": true
  }
}
```

---

### terry_lsp_init

Manually initialize the terraform-ls Language Server for a workspace. The first call may take 1-2 seconds for LSP startup.

```typescript
interface LSPInitParams {
  workspace_path: string;   // Absolute or relative workspace path
}
```

**Example Usage:**

```json
{
  "tool": "terry_lsp_init",
  "arguments": {
    "workspace_path": "/mnt/workspace/project"
  }
}
```

**Response:**

```json
{
  "terry-lsp-init": {
    "success": true,
    "workspace_path": "/mnt/workspace/project",
    "message": "LSP client initialized successfully"
  }
}
```

---

### terry_lsp_debug

Get detailed LSP debugging information including status, capabilities, and diagnostics.

```typescript
interface LSPDebugParams {
  // No parameters required
}
```

**Example Usage:**

```json
{
  "tool": "terry_lsp_debug",
  "arguments": {}
}
```

**Response:**

```json
{
  "terry-lsp-debug": {
    "lsp_status": "initialized",
    "workspace_path": "/mnt/workspace/project",
    "capabilities": ["completion", "hover", "validation"],
    "diagnostics_count": 0
  }
}
```

---

## LSP Intelligence Tools

These tools use terraform-ls v{{ site.data.project.terraform_ls }} to provide Language Server Protocol features for Terraform files.

### terraform_validate_lsp

Validate a Terraform file using the Language Server Protocol for deeper analysis than `terraform validate`.

```typescript
interface ValidateLSPParams {
  file_path: string;           // Path to the Terraform file
  workspace_path?: string;     // Optional workspace path
}
```

**Example Usage:**

```json
{
  "tool": "terraform_validate_lsp",
  "arguments": {
    "file_path": "main.tf",
    "workspace_path": "/mnt/workspace/project"
  }
}
```

**Response:**

```json
{
  "terraform-ls-validation": {
    "file_path": "main.tf",
    "diagnostics": [
      {
        "range": {
          "start": {"line": 10, "character": 5},
          "end": {"line": 10, "character": 15}
        },
        "severity": "error",
        "message": "Unknown resource type 'aws_s3_buckt'",
        "code": "invalid_resource_type"
      }
    ],
    "valid": false
  }
}
```

---

### terraform_hover

Get hover information (documentation, type info) for a position in a Terraform file.

```typescript
interface HoverParams {
  file_path: string;           // Path to the Terraform file
  line: number;                // 0-based line number
  character: number;           // 0-based character position
  workspace_path?: string;     // Optional workspace path
}
```

**Example Usage:**

```json
{
  "tool": "terraform_hover",
  "arguments": {
    "file_path": "main.tf",
    "line": 5,
    "character": 12,
    "workspace_path": "/mnt/workspace/project"
  }
}
```

**Response:**

```json
{
  "terraform-hover": {
    "contents": {
      "kind": "markdown",
      "value": "**aws_instance** (Resource)\n\nProvides an EC2 instance resource."
    },
    "range": {
      "start": {"line": 5, "character": 10},
      "end": {"line": 5, "character": 22}
    }
  }
}
```

---

### terraform_complete

Get code completion suggestions at a given position in a Terraform file.

```typescript
interface CompleteParams {
  file_path: string;           // Path to the Terraform file
  line: number;                // 0-based line number
  character: number;           // 0-based character position
  workspace_path?: string;     // Optional workspace path
}
```

**Example Usage:**

```json
{
  "tool": "terraform_complete",
  "arguments": {
    "file_path": "main.tf",
    "line": 8,
    "character": 4,
    "workspace_path": "/mnt/workspace/project"
  }
}
```

**Response:**

```json
{
  "terraform-completions": {
    "completions": [
      {
        "label": "instance_type",
        "kind": "Property",
        "detail": "string",
        "documentation": "The instance type to use for the instance",
        "insertText": "instance_type = \"${1:t3.micro}\""
      }
    ]
  }
}
```

---

### terraform_format_lsp

Format a Terraform document using terraform-ls.

```typescript
interface FormatLSPParams {
  file_path: string;           // Path to the Terraform file
  workspace_path?: string;     // Optional workspace path
}
```

**Example Usage:**

```json
{
  "tool": "terraform_format_lsp",
  "arguments": {
    "file_path": "main.tf",
    "workspace_path": "/mnt/workspace/project"
  }
}
```

**Response:**

```json
{
  "terraform-format": {
    "file_path": "main.tf",
    "formatted": true,
    "changes": 3
  }
}
```

---

### terraform_lsp_status

Get the current status of the terraform-ls Language Server.

```typescript
interface LSPStatusParams {
  // No parameters required
}
```

**Example Usage:**

```json
{
  "tool": "terraform_lsp_status",
  "arguments": {}
}
```

**Response:**

```json
{
  "terraform-lsp-status": {
    "initialized": true,
    "server_version": "{{ site.data.project.terraform_ls }}",
    "active_workspace": "/mnt/workspace/project",
    "capabilities_supported": ["completion", "hover", "validation", "formatting"]
  }
}
```

---

## Analysis and Recommendations Tools

### terry_analyze

Analyze Terraform configuration for best practices, code quality, and structural issues.

```typescript
interface AnalyzeParams {
  path: string;   // Workspace path relative to /mnt/workspace
}
```

**Example Usage:**

```json
{
  "tool": "terry_analyze",
  "arguments": {
    "path": "production"
  }
}
```

**Response:**

```json
{
  "analysis": {
    "score": 85,
    "issues": [
      {
        "severity": "warning",
        "type": "security",
        "message": "S3 bucket lacks encryption configuration",
        "file": "s3.tf",
        "line": 15,
        "recommendation": "Add server_side_encryption_configuration block"
      }
    ],
    "statistics": {
      "resources": 25,
      "data_sources": 5,
      "modules": 3,
      "providers": 2
    }
  }
}
```

---

### terry_security_scan

Run a security scan on Terraform configuration to identify vulnerabilities.

```typescript
interface SecurityScanParams {
  path: string;                                           // Workspace path
  severity?: "low" | "medium" | "high" | "critical";     // Minimum severity filter
}
```

**Example Usage:**

```json
{
  "tool": "terry_security_scan",
  "arguments": {
    "path": "production",
    "severity": "medium"
  }
}
```

**Response:**

```json
{
  "security_scan": {
    "vulnerabilities": [
      {
        "id": "CKV_AWS_20",
        "severity": "high",
        "resource": "aws_s3_bucket.data",
        "message": "S3 Bucket has an ACL defined which allows public access",
        "remediation": "Set bucket ACL to 'private'"
      }
    ],
    "summary": {
      "critical": 0,
      "high": 2,
      "medium": 5,
      "low": 3
    }
  }
}
```

---

### terry_recommendations

Get actionable recommendations for improving Terraform configuration.

```typescript
interface RecommendationsParams {
  path: string;                                                    // Workspace path
  focus?: "cost" | "security" | "performance" | "reliability";    // Recommendation focus area
}
```

**Example Usage:**

```json
{
  "tool": "terry_recommendations",
  "arguments": {
    "path": "production",
    "focus": "security"
  }
}
```

**Response:**

```json
{
  "recommendations": [
    {
      "category": "security",
      "priority": "high",
      "title": "Enable encryption at rest",
      "description": "Several resources lack encryption configuration",
      "affected_resources": ["aws_s3_bucket.data", "aws_rds_instance.main"],
      "remediation": "Add encryption configuration blocks to each resource"
    }
  ]
}
```

---

## GitHub Integration Tools

These tools require GitHub App authentication. See the [Authentication](#) section in the API Reference for setup details.

### github_clone_repo

Clone or update a GitHub repository into the workspace.

```typescript
interface GitHubCloneParams {
  owner: string;         // Repository owner or organization
  repo: string;          // Repository name
  branch?: string;       // Branch to clone (optional, defaults to default branch)
  force?: boolean;       // Force update if the repository already exists
}
```

**Example Usage:**

```json
{
  "tool": "github_clone_repo",
  "arguments": {
    "owner": "myorg",
    "repo": "infrastructure",
    "branch": "main"
  }
}
```

**Response:**

```json
{
  "success": true,
  "repository": "myorg/infrastructure",
  "branch": "main",
  "clone_path": "/mnt/workspace/github-repos/myorg/infrastructure",
  "message": "Repository cloned successfully"
}
```

---

### github_list_terraform_files

List Terraform files in a GitHub repository.

```typescript
interface GitHubListParams {
  owner: string;         // Repository owner or organization
  repo: string;          // Repository name
  path?: string;         // Subdirectory path (optional)
  pattern?: string;      // File pattern, defaults to "*.tf"
}
```

**Example Usage:**

```json
{
  "tool": "github_list_terraform_files",
  "arguments": {
    "owner": "myorg",
    "repo": "infrastructure",
    "path": "modules/vpc"
  }
}
```

**Response:**

```json
{
  "success": true,
  "repository": "myorg/infrastructure",
  "files": [
    {
      "path": "modules/vpc/main.tf",
      "name": "main.tf",
      "size": 2048,
      "modified": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 15
}
```

---

### github_get_terraform_config

Analyze Terraform configuration structure in a GitHub repository.

```typescript
interface GitHubConfigParams {
  owner: string;           // Repository owner or organization
  repo: string;            // Repository name
  config_path: string;     // Path to Terraform configuration directory
}
```

**Example Usage:**

```json
{
  "tool": "github_get_terraform_config",
  "arguments": {
    "owner": "myorg",
    "repo": "infrastructure",
    "config_path": "environments/prod"
  }
}
```

**Response:**

```json
{
  "success": true,
  "repository": "myorg/infrastructure",
  "config_path": "environments/prod",
  "terraform_files": ["main.tf", "variables.tf", "outputs.tf"],
  "has_backend": true,
  "has_variables": true,
  "has_outputs": true,
  "providers": ["aws", "kubernetes"],
  "modules": ["vpc", "eks", "rds"]
}
```

---

### github_prepare_workspace

Prepare a local Terraform workspace from a GitHub repository, cloning and setting up the configuration for Terraform operations.

```typescript
interface GitHubPrepareParams {
  owner: string;              // Repository owner or organization
  repo: string;               // Repository name
  config_path: string;        // Path to Terraform configuration in the repository
  workspace_name?: string;    // Optional custom workspace name
}
```

**Example Usage:**

```json
{
  "tool": "github_prepare_workspace",
  "arguments": {
    "owner": "myorg",
    "repo": "infrastructure",
    "config_path": "environments/staging",
    "workspace_name": "staging-review"
  }
}
```

**Response:**

```json
{
  "success": true,
  "workspace_path": "/mnt/workspace/terraform-workspaces/staging-review",
  "source_repository": "myorg/infrastructure",
  "config_path": "environments/staging",
  "terraform_files": ["main.tf", "variables.tf", "outputs.tf", "backend.tf"],
  "message": "Workspace prepared and ready for Terraform operations"
}
```

---

## Terraform Cloud Tools

These tools require a `TF_CLOUD_TOKEN` environment variable with a valid Terraform Cloud API token.

### tf_cloud_list_workspaces

List workspaces in a Terraform Cloud organization.

```typescript
interface TFCloudListParams {
  organization: string;    // Terraform Cloud organization name
  limit?: number;          // Maximum number of results (default: 20)
}
```

**Example Usage:**

```json
{
  "tool": "tf_cloud_list_workspaces",
  "arguments": {
    "organization": "my-org",
    "limit": 10
  }
}
```

**Response:**

```json
{
  "workspaces": [
    {
      "id": "ws-abc123",
      "name": "production-vpc",
      "environment": "production",
      "terraform_version": "{{ site.data.project.terraform }}",
      "current_run": {
        "id": "run-xyz789",
        "status": "applied",
        "created_at": "2024-01-15T10:30:00Z"
      },
      "resource_count": 42,
      "auto_apply": false
    }
  ]
}
```

---

### tf_cloud_get_workspace

Get detailed information about a specific Terraform Cloud workspace.

```typescript
interface TFCloudGetParams {
  organization: string;    // Terraform Cloud organization name
  workspace: string;       // Workspace name
}
```

**Example Usage:**

```json
{
  "tool": "tf_cloud_get_workspace",
  "arguments": {
    "organization": "my-org",
    "workspace": "production-vpc"
  }
}
```

**Response:**

```json
{
  "workspace": {
    "id": "ws-abc123",
    "name": "production-vpc",
    "environment": "production",
    "terraform_version": "{{ site.data.project.terraform }}",
    "auto_apply": false,
    "working_directory": "environments/production",
    "vcs_repo": {
      "identifier": "myorg/infrastructure",
      "branch": "main"
    },
    "resource_count": 42,
    "current_run": {
      "id": "run-xyz789",
      "status": "applied",
      "created_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

---

### tf_cloud_list_runs

List runs for a Terraform Cloud workspace.

```typescript
interface TFCloudRunsParams {
  organization: string;    // Terraform Cloud organization name
  workspace: string;       // Workspace name
  limit?: number;          // Maximum number of results
}
```

**Example Usage:**

```json
{
  "tool": "tf_cloud_list_runs",
  "arguments": {
    "organization": "my-org",
    "workspace": "production-vpc",
    "limit": 5
  }
}
```

**Response:**

```json
{
  "runs": [
    {
      "id": "run-xyz789",
      "status": "applied",
      "source": "tfe-api",
      "created_at": "2024-01-15T10:30:00Z",
      "plan_only": false,
      "has_changes": true,
      "resource_additions": 2,
      "resource_changes": 1,
      "resource_destructions": 0
    }
  ]
}
```

---

### tf_cloud_get_state_outputs

Get state outputs from a Terraform Cloud workspace.

```typescript
interface TFCloudOutputsParams {
  organization: string;    // Terraform Cloud organization name
  workspace: string;       // Workspace name
}
```

**Example Usage:**

```json
{
  "tool": "tf_cloud_get_state_outputs",
  "arguments": {
    "organization": "my-org",
    "workspace": "production-vpc"
  }
}
```

**Response:**

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

---

## Error Handling

All tools follow a consistent error response format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional error context"
  }
}
```

**Common Error Codes:**

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid input parameters |
| `PATH_TRAVERSAL` | Attempted access outside `/mnt/workspace` |
| `ACTION_BLOCKED` | Attempted blocked action (e.g., `apply`, `destroy`) |
| `TERRAFORM_ERROR` | Terraform execution error |
| `GITHUB_AUTH_ERROR` | GitHub authentication failed |
| `WORKSPACE_NOT_FOUND` | Workspace does not exist |
| `RATE_LIMIT_EXCEEDED` | Internal rate limit exceeded |

## Rate Limiting

{{ site.title }} enforces internal rate limits to prevent resource exhaustion. These limits are applied per-category within the server process.

| Category | Limit | Window |
|----------|-------|--------|
| Terraform Operations | {{ site.data.project.rate_limits.terraform }} requests | 1 minute |
| GitHub Operations | {{ site.data.project.rate_limits.github }} requests | 1 minute |
| Terraform Cloud | {{ site.data.project.rate_limits.tf_cloud }} requests | 1 minute |
| Default (all others) | {{ site.data.project.rate_limits.default }} requests | 1 minute |

When a rate limit is exceeded, the tool returns an error with code `RATE_LIMIT_EXCEEDED` and a message indicating when the limit resets.

## Best Practices

1. **Always validate before plan** -- Run `validate` action before `plan` in the `terry` tool.
2. **Use variables** -- Pass sensitive values through the `vars` parameter rather than hardcoding.
3. **Check workspace first** -- Use `terry_workspace_list` or `terry_workspace_info` to verify a workspace exists before operating on it.
4. **Handle errors** -- Check the `success` field in responses and handle error codes appropriately.
5. **Group related actions** -- Combine related actions (e.g., `init`, `validate`, `plan`) in a single `terry` call.
6. **Initialize LSP once** -- Call `terry_lsp_init` at the start of a session; subsequent LSP calls reuse the connection.

## Examples

### Complete Terraform Workflow

```json
{
  "tool": "terry",
  "arguments": {
    "path": "production",
    "actions": ["init", "validate", "fmt", "plan"],
    "vars": {
      "environment": "prod",
      "region": "us-east-1",
      "instance_count": 3
    }
  }
}
```

### GitHub to Workspace Pipeline

Step 1 -- Clone the repository:

```json
{
  "tool": "github_clone_repo",
  "arguments": {
    "owner": "myorg",
    "repo": "infrastructure"
  }
}
```

Step 2 -- Prepare the workspace:

```json
{
  "tool": "github_prepare_workspace",
  "arguments": {
    "owner": "myorg",
    "repo": "infrastructure",
    "config_path": "environments/staging"
  }
}
```

Step 3 -- Run Terraform operations:

```json
{
  "tool": "terry",
  "arguments": {
    "path": "terraform-workspaces/myorg_infrastructure_environments_staging",
    "actions": ["init", "plan"]
  }
}
```

### Security Validation Pipeline

Step 1 -- Analyze configuration:

```json
{
  "tool": "terry_analyze",
  "arguments": {
    "path": "production"
  }
}
```

Step 2 -- Run security scan:

```json
{
  "tool": "terry_security_scan",
  "arguments": {
    "path": "production",
    "severity": "medium"
  }
}
```

Step 3 -- Get recommendations:

```json
{
  "tool": "terry_recommendations",
  "arguments": {
    "path": "production",
    "focus": "security"
  }
}
```

Step 4 -- If all checks pass, run the plan:

```json
{
  "tool": "terry",
  "arguments": {
    "path": "production",
    "actions": ["plan"]
  }
}
```
