# Terry + OpenWebUI Integration Guide

This guide shows OpenWebUI administrators how to integrate Terry (Terraform MCP Server) with OpenWebUI using the MCP-to-OpenAPI proxy (mcpo).

## Overview

Terry can be integrated with OpenWebUI to provide Terraform intelligence directly in your AI conversations. This integration exposes all of Terry's tools as functions that can be called by your AI models.

## Prerequisites

- OpenWebUI v0.6+ (with function calling support)
- Python 3.8+ on the server running mcpo
- Terry MCP Server installed or accessible
- A model that supports native function calling (e.g., GPT-4o)

## Installation Methods

### Method 1: Docker Compose (Recommended for Production)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  terry-mcpo:
    image: ghcr.io/open-webui/mcpo:main
    ports:
      - "8000:8000"
    environment:
      - API_KEY=your-secure-api-key  # Change this!
    command: |
      --host 0.0.0.0
      --port 8000
      --api-key "${API_KEY}"
      --
      npx terraform-mcp-server
    
  terry-mcpo-enterprise:
    image: ghcr.io/open-webui/mcpo:main
    ports:
      - "8001:8000"
    environment:
      - API_KEY=your-secure-api-key  # Change this!
      - MODE=enterprise
      - TFC_TOKEN=${TFC_TOKEN}  # For Terraform Cloud features
      - GITHUB_APP_ID=${GITHUB_APP_ID}  # For GitHub integration
      - GITHUB_APP_PRIVATE_KEY=${GITHUB_APP_PRIVATE_KEY}
    command: |
      --host 0.0.0.0
      --port 8000
      --api-key "${API_KEY}"
      --
      npx terraform-mcp-server
```

### Method 2: Direct Installation

1. **Install mcpo**:
```bash
pip install mcpo
# or using uv (recommended)
pip install uv
```

2. **Run Terry through mcpo**:
```bash
# Local mode
uvx mcpo --port 8000 --api-key "your-secure-key" -- npx terraform-mcp-server

# Enterprise mode with environment variables
MODE=enterprise TFC_TOKEN=your-token uvx mcpo --port 8000 --api-key "your-secure-key" -- npx terraform-mcp-server
```

### Method 3: Custom Docker Image

Create a `Dockerfile` for a combined Terry+mcpo image:

```dockerfile
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y nodejs npm && \
    pip install mcpo && \
    npm install -g terraform-mcp-server

# Set environment variables
ENV MODE=enterprise
ENV API_KEY=change-me-in-production

# Expose port
EXPOSE 8000

# Run mcpo with Terry
CMD ["python", "-m", "mcpo", "--host", "0.0.0.0", "--port", "8000", "--api-key", "${API_KEY}", "--", "terraform-mcp-server"]
```

## Adding to OpenWebUI

### As Admin (Shared Tool Server)

1. **Navigate to Admin Settings**:
   - Go to Admin Panel → Settings → Tools

2. **Add Tool Server**:
   - Click "Add Tool Server"
   - Enter the mcpo URL:
     ```
     http://your-server:8000
     ```

3. **Configure Authentication**:
   - Add API key header:
     ```
     X-API-Key: your-secure-api-key
     ```

4. **Set Permissions**:
   - Choose which users/groups can access Terry tools
   - Enable for specific models that support function calling

### Tool Discovery

Once added, OpenWebUI will automatically discover all Terry tools:

- **Registry Tools** (Always available):
  - `providerDetails` - Get Terraform provider information
  - `resourceUsage` - Get resource usage examples
  - `moduleSearch` - Search for Terraform modules
  - `listDataSources` - List provider data sources
  - `resourceArgumentDetails` - Get detailed resource arguments
  - `functionDetails` - Get provider function details
  - `providerGuides` - Access provider documentation
  - `policySearch` - Search for policies

- **GitHub Tools** (When configured):
  - `listGitHubRepos` - List accessible repositories
  - `readGitHubFile` - Read Terraform files from repos
  - `listGitHubFiles` - Browse repository contents
  - `searchGitHubRepo` - Search in repositories

- **Terraform Cloud Tools** (Enterprise mode with TFC_TOKEN):
  - `listOrganizations` - List TFC organizations
  - `listWorkspaces` - List workspaces
  - `workspaceDetails` - Get workspace information
  - `createRun` / `applyRun` - Manage runs
  - And more...

## Configuration Options

### Environment Variables for Terry

Pass these through mcpo to configure Terry:

```bash
# Mode selection
MODE=enterprise  # or 'local' (default)

# Terraform Cloud (enterprise mode)
TFC_TOKEN=your-terraform-cloud-token

# GitHub App (all modes)
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
GITHUB_APP_INSTALLATION_ID=789012

# Logging
LOG_LEVEL=debug  # info, warn, error

# Rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_MS=60000
```

### mcpo Configuration File

For complex setups, use a config file (`mcpo-config.json`):

```json
{
  "servers": [
    {
      "name": "terry-local",
      "command": "npx terraform-mcp-server",
      "env": {
        "MODE": "local"
      }
    },
    {
      "name": "terry-enterprise",
      "command": "npx terraform-mcp-server",
      "env": {
        "MODE": "enterprise",
        "TFC_TOKEN": "${TFC_TOKEN}"
      }
    }
  ],
  "api_key": "${API_KEY}",
  "port": 8000
}
```

Run with: `uvx mcpo --config mcpo-config.json`

## Verifying the Integration

1. **Check mcpo is running**:
   ```bash
   curl -H "X-API-Key: your-secure-key" http://localhost:8000/health
   ```

2. **View available tools**:
   - Navigate to http://localhost:8000/docs
   - You'll see all Terry tools exposed as REST endpoints

3. **Test in OpenWebUI**:
   - Start a new chat
   - Ask: "What arguments does the AWS S3 bucket resource accept?"
   - The AI should use Terry's tools to fetch the information

## Usage Examples

### Example 1: Provider Information
```
User: "Tell me about the AWS provider for Terraform"
AI: *Uses providerDetails tool to fetch AWS provider information*
```

### Example 2: Module Search
```
User: "Find me a good Terraform module for creating a VPC"
AI: *Uses moduleSearch tool to find popular VPC modules*
```

### Example 3: GitHub Integration
```
User: "Show me the main.tf file in our infrastructure repo"
AI: *Uses readGitHubFile tool to fetch the file content*
```

### Example 4: Terraform Cloud (Enterprise)
```
User: "List all workspaces in our production organization"
AI: *Uses listWorkspaces tool to show TFC workspaces*
```

## Security Considerations

1. **API Key Protection**:
   - Always use strong, unique API keys
   - Rotate keys regularly
   - Never commit keys to version control

2. **Network Security**:
   - Use HTTPS in production
   - Restrict access to mcpo port
   - Consider VPN or private networking

3. **Token Management**:
   - Store TFC_TOKEN and GitHub keys securely
   - Use environment variables or secrets management
   - Limit token permissions to minimum required

## Troubleshooting

### Tools Not Appearing in OpenWebUI

1. **Check mcpo is accessible**:
   ```bash
   curl -H "X-API-Key: your-key" http://mcpo-server:8000/openapi.json
   ```

2. **Verify function calling is enabled**:
   - Go to OpenWebUI Settings
   - Ensure "Enable Function Calling" is ON
   - Select a model that supports functions

### Authentication Errors

- Verify API key is correctly set in both mcpo and OpenWebUI
- Check header format: `X-API-Key: your-key`

### Tool Execution Failures

1. **Check mcpo logs**:
   ```bash
   docker logs terry-mcpo
   ```

2. **Verify Terry configuration**:
   - TFC_TOKEN is set for TFC tools
   - GitHub App is configured for GitHub tools

### Performance Issues

- Increase mcpo workers: `--workers 4`
- Add caching layer between mcpo and Terry
- Use connection pooling for database operations

## Advanced Configuration

### High Availability Setup

Deploy multiple mcpo instances behind a load balancer:

```yaml
version: '3.8'

services:
  terry-mcpo-1:
    image: ghcr.io/open-webui/mcpo:main
    # ... configuration
    
  terry-mcpo-2:
    image: ghcr.io/open-webui/mcpo:main
    # ... configuration
    
  nginx:
    image: nginx:alpine
    ports:
      - "8000:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Monitoring

Add Prometheus metrics:

```bash
# mcpo exposes metrics at /metrics
curl http://localhost:8000/metrics
```

## Best Practices

1. **Separate Environments**:
   - Run separate mcpo instances for dev/staging/prod
   - Use different API keys per environment

2. **Tool Organization**:
   - Group related tools by prefix
   - Document tool usage in OpenWebUI

3. **Rate Limiting**:
   - Configure Terry's rate limiting
   - Add nginx rate limiting in front of mcpo

4. **Logging**:
   - Centralize logs from mcpo and Terry
   - Monitor for errors and slow queries

## Support

- **Terry Issues**: https://github.com/thrashr888/terraform-mcp-server/issues
- **mcpo Issues**: https://github.com/open-webui/mcpo/issues
- **OpenWebUI Discord**: For integration questions

This integration brings the full power of Terry's Terraform intelligence into your OpenWebUI conversations!