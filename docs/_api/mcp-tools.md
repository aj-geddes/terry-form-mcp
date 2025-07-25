---
title: MCP Tools Reference
description: Complete reference for all Terry-Form MCP tools
order: 1
---

# MCP Tools Reference

This document provides a complete reference for all tools available through the Terry-Form MCP protocol.

## Core Terraform Tools

### terry

The primary tool for executing Terraform operations.

```typescript
interface TerryParams {
  path: string;           // Workspace path relative to /mnt/workspace
  actions: string[];      // Array of Terraform actions to execute
  vars?: Record<string, any>;  // Terraform variables
}
```

**Supported Actions:**
- `init` - Initialize Terraform workspace
- `validate` - Validate configuration syntax
- `fmt` - Format Terraform files
- `plan` - Generate execution plan
- `show` - Show current state
- `graph` - Generate dependency graph
- `providers` - List required providers
- `version` - Show Terraform version

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
      "resources": [...]
    }
  ]
}
```

### terry_workspace_list

List all available Terraform workspaces.

```typescript
interface WorkspaceListParams {
  // No parameters required
}
```

**Example Response:**

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

### terry_version

Get Terraform version information.

```json
{
  "terraform_version": "1.6.5",
  "platform": "linux_amd64",
  "provider_selections": {
    "aws": "5.31.0",
    "kubernetes": "2.24.0"
  }
}
```

## GitHub Integration Tools

### github_clone_repo

Clone or update a GitHub repository.

```typescript
interface GitHubCloneParams {
  owner: string;        // Repository owner/organization
  repo: string;         // Repository name
  branch?: string;      // Branch to clone (optional)
  force?: boolean;      // Force update if exists
}
```

**Example:**

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

### github_list_terraform_files

List Terraform files in a GitHub repository.

```typescript
interface GitHubListParams {
  owner: string;
  repo: string;
  path?: string;        // Subdirectory path
  pattern?: string;     // File pattern (default: "*.tf")
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

### github_get_terraform_config

Analyze Terraform configuration in a repository.

```typescript
interface GitHubConfigParams {
  owner: string;
  repo: string;
  config_path: string;  // Path to Terraform config
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

### github_prepare_workspace

Prepare a Terraform workspace from a GitHub repository.

```typescript
interface GitHubPrepareParams {
  owner: string;
  repo: string;
  config_path: string;
  workspace_name?: string;
}
```

## Terraform Cloud Tools

### tf_cloud_list_workspaces

List Terraform Cloud workspaces.

```typescript
interface TFCloudListParams {
  organization: string;
  limit?: number;       // Max results (default: 20)
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
      "terraform_version": "1.6.5",
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

### tf_cloud_get_workspace

Get detailed workspace information.

```typescript
interface TFCloudGetParams {
  organization: string;
  workspace: string;
}
```

### tf_cloud_list_runs

List runs for a workspace.

```typescript
interface TFCloudRunsParams {
  organization: string;
  workspace: string;
  limit?: number;
}
```

### tf_cloud_get_state_outputs

Get state outputs from a workspace.

```typescript
interface TFCloudOutputsParams {
  organization: string;
  workspace: string;
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

## Intelligence Tools

### terry_analyze

Analyze Terraform configuration for best practices.

```typescript
interface AnalyzeParams {
  path: string;
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

### terry_security_scan

Run security scan on Terraform configuration.

```typescript
interface SecurityScanParams {
  path: string;
  severity?: "low" | "medium" | "high" | "critical";
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

### terry_recommendations

Get recommendations for Terraform configuration.

```typescript
interface RecommendationsParams {
  path: string;
  focus?: "cost" | "security" | "performance" | "reliability";
}
```

## LSP Tools

### terraform_validate_lsp

Validate Terraform file using Language Server Protocol.

```typescript
interface ValidateLSPParams {
  file_path: string;
  workspace_path?: string;
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

### terraform_hover

Get hover information for a position in a Terraform file.

```typescript
interface HoverParams {
  file_path: string;
  line: number;         // 0-based
  character: number;    // 0-based
  workspace_path?: string;
}
```

### terraform_complete

Get code completion suggestions.

```typescript
interface CompleteParams {
  file_path: string;
  line: number;
  character: number;
  workspace_path?: string;
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

### terraform_format_lsp

Format a Terraform document.

```typescript
interface FormatLSPParams {
  file_path: string;
  workspace_path?: string;
}
```

## Utility Tools

### terry_environment_check

Check Terry-Form environment and dependencies.

**Response:**

```json
{
  "terry-environment": {
    "environment": {
      "working_directory": "/app",
      "user": "terraform",
      "workspace_mount": true
    },
    "terraform": {
      "available": true,
      "path": "/usr/local/bin/terraform",
      "version": "Terraform v1.6.5"
    },
    "terraform_ls": {
      "available": true,
      "version": "v0.32.3"
    },
    "container": {
      "is_docker": true,
      "hostname": "terry-form-abc123"
    }
  }
}
```

### terry_workspace_setup

Create a properly structured Terraform workspace.

```typescript
interface WorkspaceSetupParams {
  path: string;
  project_name?: string;
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

- `VALIDATION_ERROR` - Invalid input parameters
- `PATH_TRAVERSAL` - Attempted access outside workspace
- `ACTION_BLOCKED` - Attempted blocked action
- `TERRAFORM_ERROR` - Terraform execution error
- `GITHUB_AUTH_ERROR` - GitHub authentication failed
- `WORKSPACE_NOT_FOUND` - Workspace doesn't exist

## Rate Limiting

The MCP server implements rate limiting:

- **Default**: 100 requests per minute
- **Terraform operations**: 20 per minute
- **GitHub operations**: 30 per minute

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705323600
```

## Best Practices

1. **Always validate before plan**: Run `validate` action before `plan`
2. **Use variables**: Pass sensitive values through `vars` parameter
3. **Check workspace**: Use `terry_workspace_list` to verify workspace exists
4. **Handle errors**: Check `success` field in responses
5. **Use transactions**: Group related actions in single `terry` call

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

```javascript
// 1. Clone repository
await mcp.call("github_clone_repo", {
  owner: "myorg",
  repo: "infrastructure"
});

// 2. Prepare workspace
await mcp.call("github_prepare_workspace", {
  owner: "myorg",
  repo: "infrastructure",
  config_path: "environments/staging"
});

// 3. Run Terraform
await mcp.call("terry", {
  path: "terraform-workspaces/myorg_infrastructure_environments_staging",
  actions: ["init", "plan"]
});
```

### Security Validation Pipeline

```javascript
// 1. Analyze configuration
const analysis = await mcp.call("terry_analyze", {
  path: "production"
});

// 2. Run security scan
const security = await mcp.call("terry_security_scan", {
  path: "production",
  severity: "medium"
});

// 3. Get recommendations
const recommendations = await mcp.call("terry_recommendations", {
  path: "production",
  focus: "security"
});

// 4. If all pass, proceed with plan
if (analysis.analysis.score > 80 && security.security_scan.summary.high === 0) {
  await mcp.call("terry", {
    path: "production",
    actions: ["plan"]
  });
}
```