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
- For personal apps: Settings → Developer settings → GitHub Apps → New GitHub App
- For organization apps: Organization Settings → Developer settings → GitHub Apps → New GitHub App

### 2. Configure Basic Information

**GitHub App name**: `Terry-Form MCP` (or your preferred name)

**Description**: 
```
Terry-Form MCP integration for managing Terraform configurations from GitHub repositories.
```

**Homepage URL**: `https://github.com/aj-geddes/terry-form-mcp`

### 3. Configure Permissions

Set the following **Repository permissions**:

- **Contents**: Read (to clone and read repository files)
- **Metadata**: Read (to access repository information)
- **Pull requests**: Read (optional, for future PR integration)
- **Actions**: Read (optional, for workflow integration)

### 4. Configure Events (Optional)

If you want to use webhooks, subscribe to:
- Push events
- Pull request events
- Repository events

**Webhook URL**: Leave blank if not using webhooks

### 5. Where can this GitHub App be installed?

Choose based on your needs:
- **Only on this account**: For personal use
- **Any account**: If you want others to use your app

### 6. Create the App

Click "Create GitHub App"

### 7. Generate Private Key

After creating the app:
1. Scroll to "Private keys" section
2. Click "Generate a private key"
3. Download the `.pem` file - **Keep this secure!**

### 8. Note Your App ID

Find your App ID at the top of the app settings page.

## Installing the GitHub App

### 1. Install to Your Account/Organization

1. In your GitHub App settings, click "Install App"
2. Choose where to install (personal account or organization)
3. Select repositories:
   - **All repositories**: Grants access to all current and future repos
   - **Selected repositories**: Choose specific repos

### 2. Note the Installation ID

After installation, you'll be redirected to the installation settings page.
The URL will be: `https://github.com/settings/installations/{INSTALLATION_ID}`

Note this Installation ID.

## Configuring Terry-Form MCP

### Environment Variables

Set the following environment variables:

```bash
# Required
export GITHUB_APP_ID="your-app-id"
export GITHUB_APP_INSTALLATION_ID="your-installation-id"

# Private key - choose one method:
# Method 1: File path (recommended)
export GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"

# Method 2: Direct key (use for containers/CI)
export GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
...key contents...
-----END RSA PRIVATE KEY-----"

# Optional
export GITHUB_APP_WEBHOOK_SECRET="your-webhook-secret"
```

### Docker Configuration

When using Docker, you can:

1. Mount the private key file:
```bash
docker run -v /path/to/private-key.pem:/keys/github-app.pem \
  -e GITHUB_APP_PRIVATE_KEY_PATH=/keys/github-app.pem \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  terry-form-mcp
```

2. Or pass the key directly:
```bash
docker run \
  -e GITHUB_APP_PRIVATE_KEY="$(cat /path/to/private-key.pem)" \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  terry-form-mcp
```

### Kubernetes Configuration

Use secrets for sensitive data:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: github-app-secret
type: Opaque
data:
  private-key: <base64-encoded-private-key>
  
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: terry-form-mcp
spec:
  template:
    spec:
      containers:
      - name: terry-form-mcp
        env:
        - name: GITHUB_APP_ID
          value: "12345"
        - name: GITHUB_APP_INSTALLATION_ID
          value: "67890"
        - name: GITHUB_APP_PRIVATE_KEY
          valueFrom:
            secretKeyRef:
              name: github-app-secret
              key: private-key
```

## Using GitHub Integration

Once configured, you can use the GitHub tools:

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

### Run Terraform on GitHub Repository
```json
{
  "tool": "terry",
  "arguments": {
    "path": "github://myorg/terraform-configs/environments/prod",
    "actions": ["init", "plan"]
  }
}
```

## Security Best Practices

1. **Limit Repository Access**: Only grant access to repositories that need Terraform management
2. **Use Read-Only Permissions**: The app only needs read access for Terraform operations
3. **Secure Private Key Storage**: 
   - Never commit the private key to version control
   - Use secure secret management (Vault, AWS Secrets Manager, etc.)
   - Rotate keys periodically
4. **Monitor App Activity**: Regularly review the app's activity in GitHub audit logs
5. **Use Installation Tokens**: The app automatically uses short-lived installation tokens

## Troubleshooting

### Common Issues

1. **"Private key not found"**
   - Check the file path is correct
   - Ensure the file has proper permissions (600)
   - Verify environment variable is set

2. **"Failed to get installation token"**
   - Verify App ID and Installation ID are correct
   - Check the app is still installed
   - Ensure the private key matches the app

3. **"Repository not accessible"**
   - Verify the app has access to the repository
   - Check repository permissions in app settings
   - Ensure installation is active

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

This will show detailed information about GitHub API calls and authentication.

## API Rate Limits

GitHub Apps have higher rate limits than personal access tokens:
- **Authenticated requests**: 5,000 per hour per installation
- **Unauthenticated requests**: 60 per hour

The Terry-Form MCP server handles rate limiting automatically.

## Revoking Access

To revoke access:
1. Go to Settings → Applications → Installed GitHub Apps
2. Find Terry-Form MCP
3. Click "Configure" → "Suspend" or "Uninstall"

## Support

For issues or questions:
- Create an issue at: https://github.com/aj-geddes/terry-form-mcp/issues
- Check the logs for detailed error messages
- Verify all environment variables are correctly set