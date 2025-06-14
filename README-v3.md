# Terry-Form MCP v3.0.0

A comprehensive Terraform infrastructure development platform with MCP protocol support, GitHub integration, module intelligence, and Terraform Cloud connectivity.

## 🚀 What's New in v3.0.0

### Major Features

- **🔄 Kubernetes-Native Deployment**: Full Helm chart and enterprise-ready Kubernetes integration
- **🤖 GitHub App Integration**: Automated PR validation and review for Terraform configurations
- **🧠 Module Intelligence**: Deep provider documentation integration with dependency impact analysis
- **☁️ Terraform Cloud Integration**: Seamless connection with HashiCorp's Terraform Cloud ecosystem

### Architecture Enhancements

- **Microservice Architecture**: Modular components for scalable deployment
- **Enterprise Security**: Enhanced RBAC, network policies, and container security
- **Multi-tenancy Support**: Namespace-based isolation and resource quotas
- **Advanced Monitoring**: Prometheus metrics, Grafana dashboards, and health probes

## 📋 Features

### Core Capabilities (from v2.0.0)
- ✅ **Terraform Operations**: init, validate, fmt, plan with security restrictions
- ✅ **Language Server Integration**: terraform-ls for intelligent code analysis
- ✅ **Docker Isolation**: Secure containerized execution environment
- ✅ **MCP Protocol**: Model Control Protocol for AI assistant integration

### New in v3.0.0

#### Kubernetes Deployment
- 📦 **Helm Charts**: Production-ready charts with comprehensive configuration
- 🏗️ **Scalability**: Horizontal pod autoscaling and load balancing
- 🔒 **Security**: Pod security policies, network policies, and RBAC
- 📊 **Monitoring**: Built-in Prometheus metrics and health checks

#### GitHub App Integration
- 🔍 **PR Validation**: Automatic Terraform validation on pull requests
- 💬 **Intelligent Comments**: Detailed feedback with inline annotations
- ✅ **Check Runs**: GitHub Checks API integration with status reporting
- 🔄 **Webhook Processing**: Real-time event handling for repository changes

#### Module Intelligence
- 📈 **Impact Analysis**: Assess provider update impact across modules
- 🔍 **Dependency Tracking**: Map module dependencies and version constraints
- ⚠️ **Breaking Change Detection**: Identify compatibility issues before updates
- 📋 **Upgrade Recommendations**: Automated suggestions for safe upgrades

#### Terraform Cloud Integration
- 🌐 **Workspace Management**: Create, update, and manage TFC workspaces
- 🚀 **Remote Runs**: Queue and monitor plan/apply operations
- 📊 **State Management**: Access and analyze remote state versions
- 💰 **Cost Estimation**: Retrieve cost estimates and budget tracking
- 🛡️ **Policy Integration**: Policy check management and override capabilities

## 🛠️ Installation

### Prerequisites

- Kubernetes cluster (1.24+)
- Helm 3.8+
- kubectl configured for your cluster

### Quick Start with Helm

```bash
# Add the Terry-Form MCP Helm repository
helm repo add terry-form-mcp https://aj-geddes.github.io/terry-form-mcp

# Install with default configuration
helm install terry-form-mcp terry-form-mcp/terry-form-mcp

# Install with custom values
helm install terry-form-mcp terry-form-mcp/terry-form-mcp -f values.yaml
```

### Configuration

#### Basic Configuration

```yaml
# values.yaml
terryFormMcp:
  replicaCount: 2
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi

# Enable GitHub App integration
github:
  enabled: true
  appId: "123456"
  privateKeySecretName: "github-app-private-key"
  webhookSecretName: "github-webhook-secret"

# Enable Terraform Cloud integration
terraformCloud:
  enabled: true
  authentication:
    tokenSecretName: "tfc-api-token"
    organizationName: "my-org"

# Enable Module Intelligence
moduleIntelligence:
  enabled: true
```

#### GitHub App Setup

1. Create a GitHub App with the provided manifest:
   ```bash
   curl -X POST https://github.com/settings/apps/new \
     -d @internal/github/app.yaml
   ```

2. Create Kubernetes secrets:
   ```bash
   kubectl create secret generic github-app-private-key \
     --from-file=private-key=path/to/private-key.pem
   
   kubectl create secret generic github-webhook-secret \
     --from-literal=webhook-secret=your-webhook-secret
   ```

#### Terraform Cloud Setup

1. Generate an API token in Terraform Cloud
2. Create Kubernetes secret:
   ```bash
   kubectl create secret generic tfc-api-token \
     --from-literal=token=your-tfc-token
   ```

## 🔧 Usage

### MCP Tools

Terry-Form MCP v3.0.0 provides comprehensive MCP tools for:

#### Terraform Operations
- `terry` - Execute Terraform commands (init, validate, fmt, plan)
- `terry_environment_check` - Verify Terraform environment
- `terry_workspace_setup` - Create workspace structure

#### LSP Intelligence
- `terraform_validate_lsp` - File validation with diagnostics
- `terraform_hover` - Documentation at cursor position
- `terraform_complete` - Code completion suggestions
- `terraform_format_lsp` - Code formatting

#### Terraform Cloud Operations
- `tfc_workspace_management` - Create, update, delete workspaces
- `tfc_run_operations` - Queue and manage runs
- `tfc_state_operations` - Access and manage state
- `tfc_variable_operations` - Manage workspace variables
- `tfc_policy_check` - Policy validation and overrides
- `tfc_cost_estimation` - Cost analysis and tracking

#### Module Intelligence
- `analyze_provider_impact` - Analyze provider update impact
- `get_upgrade_recommendations` - Get upgrade suggestions

### GitHub Integration

Once installed, the GitHub App will:

1. **Validate Pull Requests**: Automatically run Terraform validation on PRs
2. **Provide Feedback**: Add detailed comments with validation results
3. **Create Check Runs**: Update GitHub Checks with validation status
4. **Generate Reports**: Provide comprehensive analysis of changes

### Terraform Cloud Integration

Manage your Terraform Cloud workspaces directly through MCP:

```python
# Example: Create a workspace
await mcp.call_tool("tfc_workspace_management", {
    "action": "create",
    "workspace_name": "my-new-workspace",
    "execution_mode": "remote",
    "auto_apply": false
})

# Example: Queue a plan
await mcp.call_tool("tfc_run_operations", {
    "action": "create",
    "workspace_name": "my-workspace",
    "message": "Plan from Terry-Form MCP"
})
```

## 🏗️ Architecture

Terry-Form MCP v3.0.0 uses a modular architecture:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub App    │    │  Terraform Cloud │    │ Module Analysis │
│   Integration   │    │   Integration    │    │     Engine      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────┐
                    │  Terry-Form MCP     │
                    │   Core Server       │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ Terraform LSP │  │
                    │  │   Client      │  │
                    │  └───────────────┘  │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │  Terraform    │  │
                    │  │   Executor    │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

## 🔒 Security

### Container Security
- Non-root user execution
- Read-only root filesystem
- Security context enforcement
- Capability dropping

### Kubernetes Security
- Pod Security Standards enforcement
- Network policies for traffic isolation
- RBAC with least privilege access
- Secret management for sensitive data

### Operation Security
- No destructive operations (apply/destroy disabled)
- Workspace isolation
- Path validation and sanitization
- Rate limiting and timeout controls

## 📊 Monitoring

### Health Checks
- `/health` - General health status
- `/ready` - Readiness for traffic
- `/metrics` - Prometheus metrics

### Metrics
- Operation counts and durations
- Component health status
- Resource utilization
- Error rates and types

## 🚀 Development

### Building

```bash
# Build the container
docker build -f Dockerfile-v3 -t terry-form-mcp:v3.0.0 .

# Build microservice images
docker build -f Dockerfile-v3 --target terry-form-core -t terry-form-core:v3.0.0 .
docker build -f Dockerfile-v3 --target terry-form-github -t terry-form-github:v3.0.0 .
```

### Testing

```bash
# Install development dependencies
pip install -r requirements-v3.txt

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=internal --cov-report=html
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📚 Documentation

- [Architecture Guide](docs/architecture/)
- [Deployment Guide](docs/guides/deployment.md)
- [GitHub App Setup](docs/guides/github-app.md)
- [Terraform Cloud Integration](docs/guides/terraform-cloud.md)
- [Module Intelligence](docs/guides/module-intelligence.md)
- [API Reference](docs/api/)

## 🆕 Upgrade from v2.0.0

Terry-Form MCP v3.0.0 maintains backward compatibility with v2.0.0 MCP tools. To upgrade:

1. Update your Helm chart to v3.0.0
2. Configure new features as needed
3. Update your container image references

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/aj-geddes/terry-form-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aj-geddes/terry-form-mcp/discussions)
- **Documentation**: [Project Documentation](https://aj-geddes.github.io/terry-form-mcp/)

## 🎯 Roadmap

### Future Enhancements
- **Multi-cloud Provider Support**: Extend beyond Terraform to other IaC tools
- **Advanced Policy Engine**: Custom policy creation and enforcement
- **CI/CD Integration**: Native GitLab, Azure DevOps, and Jenkins integration
- **Advanced Analytics**: Drift detection and compliance reporting
- **AI-Powered Suggestions**: ML-driven optimization recommendations