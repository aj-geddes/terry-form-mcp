# GitHub Integration Workflows

This document shows common workflows using the Terry-Form MCP GitHub integration.

## Prerequisites

Ensure you have configured the GitHub App as described in `/docs/GITHUB_APP_SETUP.md`.

## Example Workflows

### 1. Clone and Analyze a Repository

```json
{
  "tool": "github_clone_repo",
  "arguments": {
    "owner": "hashicorp",
    "repo": "terraform-aws-vault",
    "branch": "main"
  }
}
```

Then list the Terraform files:

```json
{
  "tool": "github_list_terraform_files",
  "arguments": {
    "owner": "hashicorp",
    "repo": "terraform-aws-vault",
    "path": "examples"
  }
}
```

### 2. Run Terraform Plan on GitHub Repository

Direct approach using `github://` prefix:

```json
{
  "tool": "terry",
  "arguments": {
    "path": "github://hashicorp/terraform-aws-vault/examples/vault-cluster",
    "actions": ["init", "validate", "plan"],
    "vars": {
      "aws_region": "us-east-1",
      "vault_cluster_name": "my-vault"
    }
  }
}
```

### 3. Prepare Isolated Workspace

```json
{
  "tool": "github_prepare_workspace",
  "arguments": {
    "owner": "myorg",
    "repo": "infrastructure",
    "config_path": "environments/production",
    "workspace_name": "prod-deployment"
  }
}
```

Then work with the prepared workspace:

```json
{
  "tool": "terry",
  "arguments": {
    "path": "/mnt/workspace/terraform-workspaces/prod-deployment",
    "actions": ["plan"]
  }
}
```

### 4. Analyze Repository Structure

```json
{
  "tool": "github_get_terraform_config",
  "arguments": {
    "owner": "myorg",
    "repo": "terraform-modules",
    "config_path": "modules/networking"
  }
}
```

### 5. Clean Up Old Repositories

```json
{
  "tool": "github_cleanup_repos",
  "arguments": {
    "days_old": 14
  }
}
```

## Security Notes

- The GitHub App only has read access to repositories
- All cloned repositories are isolated in the workspace
- Destructive Terraform operations (apply, destroy) are blocked
- Repository names and paths are validated to prevent injection attacks

## Troubleshooting

### Repository Not Found

If you get a "repository not found" error, check:
1. The GitHub App has access to the repository
2. The owner and repo names are correct
3. The repository exists and is not archived

### Authentication Errors

If you get authentication errors:
1. Check the GitHub App ID and Installation ID are correct
2. Verify the private key is properly configured
3. Ensure the installation is active

### Rate Limiting

The GitHub App has higher rate limits than personal tokens:
- 5,000 requests per hour per installation
- The integration handles rate limiting automatically