---
layout: page
title: GitHub App Setup
description: Set up a GitHub App for Terry-Form MCP repository integration
---

# GitHub App Setup Guide

This guide will help you set up a GitHub App for the Terry-Form MCP server to access and work with Terraform repositories.

## Overview

The Terry-Form MCP server can integrate with GitHub to:
- Clone and access private repositories
- List and analyze Terraform configurations
- Prepare isolated workspaces from GitHub repos
- Manage repository access securely

## Creating a GitHub App

### 1. Navigate to GitHub App Settings

- Go to your GitHub account settings
- For personal apps: Settings > Developer settings > GitHub Apps > New GitHub App
- For organization apps: Organization Settings > Developer settings > GitHub Apps > New GitHub App

### 2. Configure Basic Information

**GitHub App name**: `Terry-Form MCP` (or your preferred name)

**Description**:
```
Terry-Form MCP integration for managing Terraform configurations from GitHub repositories.
```

**Homepage URL**: `{{ site.data.project.repo_url }}`

### 3. Configure Permissions

Set the following **Repository permissions**:

| Permission | Access | Purpose |
|-----------|--------|---------|
| Contents | Read | Clone and read repository files |
| Metadata | Read | Access repository information |
| Pull requests | Read | Optional, for future PR integration |

### 4. Where can this GitHub App be installed?

Choose based on your needs:
- **Only on this account**: For personal use
- **Any account**: If you want others to use your app

### 5. Create the App and Generate Private Key

After creating the app:
1. Note your **App ID** at the top of the settings page
2. Scroll to "Private keys" section
3. Click "Generate a private key"
4. Download the `.pem` file — **Keep this secure!**

### 6. Install the App

1. In your GitHub App settings, click "Install App"
2. Choose where to install (personal account or organization)
3. Select repositories to grant access
4. Note the **Installation ID** from the URL: `https://github.com/settings/installations/{INSTALLATION_ID}`

## Configuring Terry-Form MCP

### Environment Variables

```bash
# Required for GitHub integration
export GITHUB_APP_ID="your-app-id"
export GITHUB_APP_INSTALLATION_ID="your-installation-id"

# Private key - choose one method:
# Method 1: File path (recommended)
export GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"

# Method 2: Direct key (for containers/CI)
export GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
...key contents...
-----END RSA PRIVATE KEY-----"
```

### Docker Configuration

Mount the private key file into the container:

```bash
docker run -i --rm \
  -v /path/to/private-key.pem:/keys/github-app.pem:ro \
  -v /path/to/workspace:/mnt/workspace \
  -e GITHUB_APP_PRIVATE_KEY_PATH=/keys/github-app.pem \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  terry-form-mcp:latest
```

Or pass the key directly:

```bash
docker run -i --rm \
  -v /path/to/workspace:/mnt/workspace \
  -e GITHUB_APP_PRIVATE_KEY="$(cat /path/to/private-key.pem)" \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  terry-form-mcp:latest
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "./workspace:/mnt/workspace",
        "-v", "/path/to/private-key.pem:/keys/github-app.pem:ro",
        "-e", "GITHUB_APP_ID=12345",
        "-e", "GITHUB_APP_INSTALLATION_ID=67890",
        "-e", "GITHUB_APP_PRIVATE_KEY_PATH=/keys/github-app.pem",
        "terry-form-mcp:latest"
      ]
    }
  }
}
```

## Using GitHub Integration

Once configured, the following MCP tools become available:

### Clone a Repository

```json
{
  "tool": "github_clone_repo",
  "arguments": {
    "owner": "myorg",
    "repo": "terraform-configs",
    "branch": "main"
  }
}
```

### List Terraform Files

```json
{
  "tool": "github_list_terraform_files",
  "arguments": {
    "owner": "myorg",
    "repo": "terraform-configs",
    "path": "environments/prod"
  }
}
```

### Prepare Workspace from GitHub

```json
{
  "tool": "github_prepare_workspace",
  "arguments": {
    "owner": "myorg",
    "repo": "terraform-configs",
    "config_path": "environments/prod"
  }
}
```

## Security Best Practices

1. **Limit Repository Access**: Only grant access to repositories that need Terraform management
2. **Use Read-Only Permissions**: The app only needs read access
3. **Secure Private Key Storage**: Never commit the private key to version control. Use secret management tools
4. **Monitor App Activity**: Regularly review the app's activity in GitHub audit logs
5. **Use Installation Tokens**: The app automatically uses short-lived installation tokens (1 hour expiry)

## Troubleshooting

### Common Issues

**"Private key not found"**
- Check the file path is correct and mounted in the container
- Ensure the file has proper permissions (600)

**"Failed to get installation token"**
- Verify App ID and Installation ID are correct
- Check the app is still installed on the target account
- Ensure the private key matches the app

**"Repository not accessible"**
- Verify the app has access to the repository
- Check repository permissions in app settings

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

This will show detailed information about GitHub API calls and authentication.

## Rate Limits

GitHub Apps have higher rate limits than personal access tokens:
- **Authenticated requests**: 5,000 per hour per installation
- **Terry-Form internal limit**: {{ site.data.project.rate_limits.github }} requests per minute

## Revoking Access

To revoke access:
1. Go to Settings > Applications > Installed GitHub Apps
2. Find Terry-Form MCP
3. Click "Configure" > "Suspend" or "Uninstall"
