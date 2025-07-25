---
layout: page
title: API Reference
description: Complete API reference for Terry-Form MCP
---

# API Reference

Complete reference documentation for Terry-Form MCP APIs and tools.

## MCP Protocol Tools

<div class="api-section">
{% for api in site.api %}
  {% if api.category == "mcp" or api.category == nil %}
  <div class="api-card">
    <h3><a href="{{ api.url | relative_url }}">{{ api.title }}</a></h3>
    <p>{{ api.description }}</p>
    {% if api.tools %}
    <div class="api-tools">
      {% for tool in api.tools %}
      <span class="tool-badge">{{ tool }}</span>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  {% endif %}
{% endfor %}
</div>

## Quick Reference

### Core Terraform Tools

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `terry` | Execute Terraform operations | Plan, validate, format |
| `terry_workspace_list` | List available workspaces | Discovery |
| `terry_version` | Get Terraform version info | Compatibility check |

### GitHub Integration

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `github_clone_repo` | Clone/update repositories | Repository management |
| `github_list_terraform_files` | List .tf files in repo | Code discovery |
| `github_get_terraform_config` | Analyze Terraform configs | Code analysis |

### Intelligence Tools

| Tool | Description | Primary Use |
|------|-------------|-------------|
| `terry_analyze` | Best practice analysis | Code quality |
| `terry_security_scan` | Security vulnerability scan | Security audit |
| `terry_recommendations` | Get improvement suggestions | Optimization |

## Response Formats

All Terry-Form MCP tools follow consistent response patterns:

### Success Response

```json
{
  "tool-name-results": {
    "success": true,
    "data": {
      // Tool-specific data
    },
    "metadata": {
      "duration": 1.234,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  }
}
```

### Error Response

```json
{
  "error": "Descriptive error message",
  "code": "ERROR_CODE",
  "details": {
    // Additional error context
  }
}
```

## Authentication

### MCP Protocol

MCP protocol handles authentication at the transport level. No additional authentication required for tool calls.

### Web API

For direct HTTP API access:

```bash
curl -H "X-API-Key: your-api-key" \
     https://terry-form.example.com/api/v1/workspaces
```

### GitHub App

Configure GitHub App credentials:

```yaml
GITHUB_APP_ID: "123456"
GITHUB_APP_PRIVATE_KEY: "-----BEGIN RSA PRIVATE KEY-----..."
```

## Rate Limits

| Endpoint Type | Limit | Window |
|--------------|-------|--------|
| General | 100 requests | 1 minute |
| Terraform Operations | 20 requests | 1 minute |
| GitHub Operations | 30 requests | 1 minute |
| Analysis Tools | 10 requests | 1 minute |

## Tool Categories

<div class="tool-categories">
  <div class="category">
    <h3>🔧 Infrastructure Management</h3>
    <ul>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#terry">terry</a> - Core Terraform operations</li>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#terry_workspace_list">Workspace management</a></li>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#terry_version">Version information</a></li>
    </ul>
  </div>
  
  <div class="category">
    <h3>🔗 Integrations</h3>
    <ul>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#github-integration-tools">GitHub Tools</a></li>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#terraform-cloud-tools">Terraform Cloud</a></li>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#lsp-tools">LSP Integration</a></li>
    </ul>
  </div>
  
  <div class="category">
    <h3>📊 Intelligence</h3>
    <ul>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#terry_analyze">Configuration analysis</a></li>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#terry_security_scan">Security scanning</a></li>
      <li><a href="{{ site.baseurl }}/api/mcp-tools#terry_recommendations">Recommendations</a></li>
    </ul>
  </div>
</div>

## Common Patterns

### Sequential Operations

```javascript
// Initialize, validate, and plan
const result = await mcp.call("terry", {
  path: "production",
  actions: ["init", "validate", "plan"],
  vars: { environment: "prod" }
});
```

### Error Handling

```javascript
try {
  const result = await mcp.call("terry", { path: "invalid/path" });
} catch (error) {
  if (error.code === "PATH_TRAVERSAL") {
    console.error("Invalid path specified");
  }
}
```

### Workspace Discovery

```javascript
// List all workspaces
const workspaces = await mcp.call("terry_workspace_list");

// Filter initialized workspaces
const initialized = workspaces.workspaces.filter(w => w.initialized);
```

## API Versioning

Terry-Form MCP follows semantic versioning for its API:

- **v1** - Current stable version
- **v2** - Future version (planned)

Version is included in HTTP API paths:
```
/api/v1/workspaces
/api/v1/operations
```

## SDK Support

### Python SDK

```python
from terry_form_mcp import Client

client = Client(api_key="your-key")
result = client.terry(
    path="production",
    actions=["plan"],
    vars={"environment": "prod"}
)
```

### JavaScript SDK

```javascript
import { TerryFormClient } from '@terry-form/mcp-client';

const client = new TerryFormClient({ apiKey: 'your-key' });
const result = await client.terry({
  path: 'production',
  actions: ['plan'],
  vars: { environment: 'prod' }
});
```

## Need Help?

- 📖 [Getting Started Guide]({{ site.baseurl }}/getting-started)
- 💬 [Community Forum](https://github.com/aj-geddes/terry-form-mcp/discussions)
- 🐛 [Report an Issue](https://github.com/aj-geddes/terry-form-mcp/issues)

<style>
.api-section {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.api-card {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid #e9ecef;
}

.api-tools {
  margin-top: 1rem;
}

.tool-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background: #e3f2fd;
  color: #1565c0;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  margin-right: 0.5rem;
  margin-bottom: 0.5rem;
}

.tool-categories {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.category {
  background: #f0f7ff;
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.category h3 {
  margin-top: 0;
}

.category ul {
  list-style: none;
  padding: 0;
}

.category li {
  margin: 0.5rem 0;
}

@media (prefers-color-scheme: dark) {
  .api-card {
    background: #2a2a2a;
    border-color: #444;
  }
  
  .tool-badge {
    background: #1e3a5f;
    color: #90caf9;
  }
  
  .category {
    background: #1a1a2e;
  }
}
</style>