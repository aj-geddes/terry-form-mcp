---
title: Terraform Operations
description: Deep dive into the terry tool — all actions, blocked operations, sequential workflows, and workspace management
order: 4
---

# Terraform Operations Guide

The `terry` tool is the core of Terry-Form MCP. This guide covers every supported action, how to chain operations, and workspace management.

## The `terry` Tool

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | Yes | — | Workspace path relative to `/mnt/workspace` |
| `actions` | string[] | No | `["plan"]` | Terraform actions to execute sequentially |
| `vars` | object | No | `{}` | Terraform variables to pass |

### Example Usage

```json
{
  "tool": "terry",
  "arguments": {
    "path": "environments/dev",
    "actions": ["init", "validate", "plan"],
    "vars": {
      "environment": "development",
      "region": "us-east-1"
    }
  }
}
```

## Supported Actions

### `init` — Initialize Workspace

Downloads providers and sets up the backend.

```json
{"path": "my-project", "actions": ["init"]}
```

**Output**: Provider download progress, initialization status.

### `validate` — Validate Configuration

Checks HCL syntax and configuration validity.

```json
{"path": "my-project", "actions": ["validate"]}
```

**Output**: Success message or detailed validation errors with file and line numbers.

### `plan` — Generate Execution Plan

Shows what Terraform would do without making changes.

```json
{"path": "my-project", "actions": ["plan"], "vars": {"env": "dev"}}
```

**Output**: Plan summary with resource additions, changes, and destructions.

### `fmt` — Format Files

Rewrites Terraform files to canonical format.

```json
{"path": "my-project", "actions": ["fmt"]}
```

**Output**: List of formatted files.

### `show` — Show State

Displays the current state of managed resources.

```json
{"path": "my-project", "actions": ["show"]}
```

### `graph` — Dependency Graph

Generates a DOT-format dependency graph.

```json
{"path": "my-project", "actions": ["graph"]}
```

### `providers` — List Providers

Shows required and installed providers.

```json
{"path": "my-project", "actions": ["providers"]}
```

### `version` — Terraform Version

Returns the Terraform version.

```json
{"path": "my-project", "actions": ["version"]}
```

## Blocked Actions

The following actions are **permanently blocked** and cannot be enabled:

| Action | Reason |
|--------|--------|
| `apply` | Modifies real infrastructure |
| `destroy` | Deletes real infrastructure |
| `import` | Modifies state file |
| `taint` | Modifies state file |
| `untaint` | Modifies state file |

<div class="alert alert-info">
<strong>By Design</strong><br>
Blocking destructive operations is a core safety feature. Terry-Form MCP is designed for planning and analysis — actual infrastructure changes should be made through your CI/CD pipeline or manual Terraform runs with proper approvals.
</div>

## Sequential Workflows

Actions are executed in the order specified. If any action fails, subsequent actions are skipped.

### Standard Workflow

```json
{
  "path": "my-project",
  "actions": ["init", "validate", "plan"]
}
```

Returns results for each action:

```json
{
  "terry-results": [
    {"action": "init", "success": true, "exit_code": 0, "stdout": "..."},
    {"action": "validate", "success": true, "exit_code": 0, "stdout": "..."},
    {"action": "plan", "success": true, "exit_code": 0, "stdout": "..."}
  ]
}
```

### Format and Validate

```json
{
  "path": "my-project",
  "actions": ["fmt", "validate"]
}
```

### Full Analysis Pipeline

Combine `terry` with analysis tools for comprehensive review:

1. `terry` with `["init", "validate", "plan"]`
2. `terry_analyze` for best practices
3. `terry_security_scan` for vulnerabilities
4. `terry_recommendations` for improvements

## Workspace Management

### Discovering Workspaces

Use `terry_workspace_list` to find all workspaces:

```json
{"tool": "terry_workspace_list"}
```

Returns:
```json
{
  "workspaces": [
    {
      "path": "project-a",
      "initialized": true,
      "has_state": true,
      "providers": ["aws"],
      "modules": 2,
      "last_modified": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### Creating Workspaces

Use `terry_workspace_setup` to scaffold a new workspace:

```json
{
  "tool": "terry_workspace_setup",
  "arguments": {
    "path": "new-project",
    "project_name": "My New Project"
  }
}
```

Creates `main.tf`, `variables.tf`, and `outputs.tf` with boilerplate.

### Inspecting Workspaces

Use `terry_workspace_info` for detailed workspace analysis:

```json
{
  "tool": "terry_workspace_info",
  "arguments": {"path": "my-project"}
}
```

Returns file listings, initialization status, and LSP readiness.

### Checking Files

Use `terry_file_check` to validate individual files:

```json
{
  "tool": "terry_file_check",
  "arguments": {"file_path": "my-project/main.tf"}
}
```

## Passing Variables

Variables are passed as key-value pairs. They map to Terraform's `-var` flag:

```json
{
  "path": "my-project",
  "actions": ["plan"],
  "vars": {
    "environment": "production",
    "instance_count": 3,
    "enable_monitoring": true
  }
}
```

<div class="alert alert-warning">
<strong>Variable Safety</strong><br>
Variable values are sanitized to prevent injection attacks. Special characters that could be used for command injection are blocked.
</div>

## Environment Check

Use `terry_environment_check` to verify the container environment:

```json
{"tool": "terry_environment_check"}
```

Returns Terraform availability, terraform-ls status, container info, and workspace mount status.

## Error Handling

When an action fails, the response includes:

```json
{
  "action": "validate",
  "success": false,
  "exit_code": 1,
  "stderr": "Error: Invalid resource type...",
  "duration": 0.5
}
```

Common error scenarios:
- **Path not found**: The workspace path doesn't exist in `/mnt/workspace`
- **Not initialized**: Run `init` before other actions
- **Validation errors**: HCL syntax or configuration problems
- **Provider errors**: Missing or incompatible providers
