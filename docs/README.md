# Terry Documentation

Welcome to the Terry (Terraform Registry MCP Server) documentation!

## 📚 Documentation Overview

### For Users
- **[User Guide](./USER_GUIDE.md)** - Step-by-step guide for running Terry locally with Docker Desktop
- Perfect for individual developers who want Terraform assistance in their IDE

### For Developers
- **[Development Guide](./DEVELOPMENT.md)** - Architecture, patterns, and contribution guidelines
- Everything you need to understand and extend Terry

### For DevOps/Platform Teams
- **[Enterprise Deployment Guide](./ENTERPRISE_DEPLOYMENT.md)** - Production Kubernetes deployment
- Comprehensive guide for deploying Terry at scale with full features

### GitHub Integration
- **[GitHub App Setup Guide](./GITHUB_APP_SETUP.md)** - Configure GitHub App for repository access
- Enable Terry to read Terraform configurations from your GitHub repositories

### Platform Integrations
- **[OpenWebUI Integration Guide](./OPENWEBUI_INTEGRATION.md)** - Add Terry to OpenWebUI as a function tool
- Complete guide for administrators to integrate Terry with OpenWebUI using mcpo

## 🚀 Quick Start

### Local Mode (Individual Use)
```bash
# Using Docker
docker run -d --name terry -p 3000:3000 terraform-mcp-server:latest

# Using npm/npx
npx terraform-mcp-server
```

### Enterprise Mode (Team Use)
```bash
# Using Helm
helm install terry ./charts/terry \
  --namespace terry \
  --create-namespace \
  --set tfcToken=your-token \
  --set mode=enterprise
```

## 🔄 Mode Comparison

| Feature | Local Mode | Enterprise Mode |
|---------|------------|-----------------|
| **Terraform Registry** | ✅ Full Access | ✅ Full Access |
| **Terraform Cloud** | ❌ Not Available | ✅ With TFC Token |
| **Web UI** | ✅ Status Only | ✅ Full Dashboard |
| **MCP Bridge** | ❌ Not Available | ✅ Coming Soon |
| **Authentication** | None Required | TFC Token |
| **Deployment** | Docker/NPM | Kubernetes/Helm |
| **Scaling** | Single Instance | Auto-scaling |
| **Best For** | Individual Devs | Teams/Organizations |

## 📋 Feature Matrix

### Available Tools

#### Registry Tools (Both Modes)
- `providerDetails` - Get provider information
- `resourceUsage` - Get resource examples
- `moduleSearch` - Search for modules
- `listDataSources` - List data sources
- `resourceArgumentDetails` - Get resource arguments
- `functionDetails` - Get function details
- `providerGuides` - Access provider guides
- `policySearch` - Search policies

#### Terraform Cloud Tools (Enterprise Only)
- `listOrganizations` - List TFC organizations
- `listWorkspaces` - List workspaces
- `workspaceDetails` - Get workspace info
- `lockWorkspace` / `unlockWorkspace` - Workspace locking
- `listRuns` / `runDetails` - Run management
- `createRun` / `applyRun` / `cancelRun` - Run operations
- `privateModuleSearch` - Search private modules

## 🏗️ Architecture

```
Terry MCP Server
├── Mode Detection (Local/Enterprise)
├── MCP Protocol Handler (stdio)
├── Tool System
│   ├── Registry Tools
│   └── TFC Tools (Enterprise)
├── Resource System (URI-based)
├── Web UI (Express)
└── Future: MCP Bridge (Enterprise)
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MODE` | Server mode (`local`/`enterprise`) | `local` | No |
| `TFC_TOKEN` | Terraform Cloud API token | - | Enterprise only |
| `WEB_UI_PORT` | Web UI port | `3000` | No |
| `LOG_LEVEL` | Logging level | `info` | No |

## 📊 Monitoring

### Health Endpoints
- `/health` - Basic health check
- `/api/status` - Detailed status with mode info

### Logs
- Structured JSON logging
- Configurable log levels
- Error tracking and debugging

## 🔒 Security

- No credentials stored in local mode
- TFC tokens secured via K8s secrets in enterprise
- Input validation on all tools
- Rate limiting available

## 🤝 Integration

### Supported Clients
- Cursor IDE
- Claude Desktop
- Any MCP-compatible client

### API Compatibility
- Terraform Registry API v1/v2
- Terraform Cloud API v2
- MCP Protocol 1.0

## 📈 Roadmap

- [x] Local and Enterprise modes
- [x] Web UI dashboard
- [x] Kubernetes deployment
- [x] Helm chart
- [ ] MCP Bridge for LLM integration
- [ ] Metrics and telemetry
- [ ] Multi-cluster support
- [ ] Enhanced caching

## 🆘 Getting Help

1. Check the relevant guide for your use case
2. View logs (Docker/Kubernetes)
3. Check the web UI status page
4. Report issues on GitHub

## 📝 License

See [LICENSE](../LICENSE) file in the root directory.