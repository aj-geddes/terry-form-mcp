# GitHub App Setup Guide

This guide explains how to set up GitHub App integration with Terry to read Terraform configurations from your GitHub repositories.

## Overview

Terry's GitHub App integration provides secure, fine-grained access to your repositories without using personal access tokens. Each Terry installation can have its own GitHub App, ensuring complete control over permissions and access.

## Features

With GitHub App integration, Terry can:
- 📖 **Read Terraform files** from private repositories
- 🔍 **Search repositories** for specific Terraform resources
- 📂 **List and browse** repository contents
- 🔒 **Access only what you permit** with fine-grained permissions

## Setup Process

### Step 1: Access GitHub App Setup

1. Ensure Terry is running with the Web UI enabled
2. Navigate to http://localhost:3000 (or your Terry URL)
3. Click on "Configure GitHub App" or go directly to http://localhost:3000/github-app

### Step 2: Create Your GitHub App

1. Click the "Create GitHub App" button
2. You'll be redirected to GitHub with a pre-filled manifest
3. Review the permissions:
   - **Contents**: Read (to access repository files)
   - **Metadata**: Read (basic repository information)
   - **Pull requests**: Read (optional, for PR-based workflows)
   - **Issues**: Read (optional, for issue-based terraform plans)
4. Choose a unique name for your app (e.g., "Terry-YourOrg")
5. Click "Create GitHub App"

### Step 3: Configure Terry

After creating the app, you'll need to configure Terry with the app credentials:

1. From your new GitHub App page, note down:
   - **App ID** (shown at the top of the page)
   - **Client ID** (in the "About" section)
   
2. Generate and download a **Private Key**:
   - Scroll to "Private keys" section
   - Click "Generate a private key"
   - Save the downloaded `.pem` file securely

3. Return to Terry's configuration page: http://localhost:3000/github-app/configure

4. Enter:
   - **App ID**: The numeric ID from GitHub
   - **Private Key**: Paste the entire contents of the `.pem` file

5. Click "Save Configuration"

### Step 4: Install the App

1. Go to your GitHub App's page on GitHub
2. Click "Install App" in the left sidebar
3. Choose the account/organization to install to
4. Select repositories:
   - "All repositories" for full access
   - "Selected repositories" to limit access
5. Click "Install"

## Using GitHub Integration

Once configured, you can use these new MCP tools:

### List Accessible Repositories
```
Tool: listGitHubRepos
Returns all repositories the GitHub App can access
```

### Read a File
```
Tool: readGitHubFile
Parameters:
- owner: "myorg"
- repo: "infrastructure"
- path: "modules/vpc/main.tf"
- ref: "main" (optional)
```

### List Files in a Directory
```
Tool: listGitHubFiles
Parameters:
- owner: "myorg"
- repo: "infrastructure"
- path: "modules" (optional)
- pattern: "*.tf" (optional)
```

### Search Repository
```
Tool: searchGitHubRepo
Parameters:
- owner: "myorg"
- repo: "infrastructure"
- query: "resource aws_instance"
- extension: "tf" (optional)
```

## Configuration Options

### Environment Variables (Enterprise)

For production deployments, use environment variables instead of file-based configuration:

```bash
export GITHUB_APP_ID="123456"
export GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----"
export GITHUB_APP_INSTALLATION_ID="789012"  # Optional, for single-installation apps
```

### Configuration File

Terry stores GitHub App configuration in `~/.terry-mcp/github-app.json` with restricted permissions (0600).

## Security Considerations

1. **Private Key Security**
   - Keep your private key secure
   - Never commit it to version control
   - Use environment variables in production
   - Rotate keys periodically

2. **Repository Access**
   - Only install on repositories containing Terraform code
   - Use "Selected repositories" for minimal access
   - Review permissions regularly

3. **Installation Management**
   - Each installation has its own ID
   - Terry can work with multiple installations
   - Remove unused installations

## Troubleshooting

### "GitHub App not configured"
- Ensure you've completed the configuration step
- Check if the configuration file exists: `~/.terry-mcp/github-app.json`
- Verify environment variables if using that method

### "Invalid GitHub App credentials"
- Verify the App ID is correct
- Ensure the private key is properly formatted (including headers)
- Check if the key has expired

### "Repository not found"
- Verify the GitHub App is installed on the repository
- Check repository permissions
- Ensure correct owner/repo names

### Rate Limits
GitHub Apps have generous rate limits:
- 5,000 requests per hour for installations
- Separate from personal rate limits

## Managing Your GitHub App

### View Installations
Visit http://localhost:3000/github-app/installations to see all active installations.

### View Accessible Repositories
Visit http://localhost:3000/github-app/repos to see all repositories Terry can access.

### Reconfigure
To update credentials or reconfigure, visit http://localhost:3000/github-app/configure

### Revoke Access
1. Go to GitHub Settings > Applications > Installed GitHub Apps
2. Find your Terry app
3. Click "Configure" 
4. Click "Uninstall" or adjust repository access

## Best Practices

1. **Least Privilege**: Only grant access to repositories with Terraform code
2. **Regular Audits**: Review installations and permissions periodically
3. **Separate Apps**: Consider separate apps for dev/prod environments
4. **Monitor Usage**: Check GitHub App insights for usage patterns
5. **Key Rotation**: Rotate private keys every 90 days

## Example Workflows

### Reading Module Documentation
```
User: "Show me the VPC module in our infrastructure repo"
Terry: *Uses readGitHubFile to fetch modules/vpc/README.md*
```

### Searching for Resources
```
User: "Find all S3 buckets in our terraform code"
Terry: *Uses searchGitHubRepo with query "resource aws_s3_bucket"*
```

### Reviewing Configuration
```
User: "List all terraform files in the production folder"
Terry: *Uses listGitHubFiles with path "production" and pattern "*.tf"*
```

This completes the GitHub App setup. Terry can now securely access your Terraform repositories!