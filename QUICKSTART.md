# Terry-Form MCP - Quick Start Guide

## ✅ Status: Production Ready

This project uses a **single, enhanced MCP server** with complete LSP integration.

## 🚀 Quick Start (3 Steps)

### 1. Build the Docker Image

```bash
./build.sh
```

### 2. Run the Server

```bash
docker run -it --rm \
  -v "$(pwd)":/mnt/workspace \
  terry-form-mcp:latest
```

### 3. Configure Your MCP Client

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "terry": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/terraform:/mnt/workspace",
        "terry-form-mcp:latest"
      ]
    }
  }
}
```

## 📦 What's Included

### Single Server: `server_enhanced_with_lsp.py`

**25 MCP Tools Available:**

#### Core Terraform (4 tools)
- `terry` - Execute Terraform commands
- `terry_version` - Get Terraform version info
- `terry_environment_check` - Environment diagnostics
- `terry_workspace_list` - List all workspaces

#### LSP Intelligence (5 tools)
- `terraform_validate_lsp` - Validate files with detailed diagnostics
- `terraform_hover` - Get hover documentation
- `terraform_complete` - Code completion suggestions
- `terraform_format_lsp` - Format Terraform files
- `terraform_lsp_status` - LSP server status

#### Diagnostic Tools (6 tools)
- `terry_lsp_debug` - LSP debugging info
- `terry_workspace_info` - Workspace analysis
- `terry_lsp_init` - Manual LSP initialization
- `terry_file_check` - File validation
- `terry_workspace_setup` - Create new workspace
- `terry_analyze` - Best practices analysis

#### Intelligence Tools (2 tools)
- `terry_security_scan` - Security vulnerability scanning
- `terry_recommendations` - Improvement recommendations

#### GitHub Integration (4 tools)
- `github_clone_repo` - Clone GitHub repositories
- `github_list_terraform_files` - List Terraform files in repo
- `github_get_terraform_config` - Analyze repo configuration
- `github_prepare_workspace` - Prepare workspace from GitHub

#### Terraform Cloud (4 tools)
- `tf_cloud_list_workspaces` - List TF Cloud workspaces
- `tf_cloud_get_workspace` - Get workspace details
- `tf_cloud_list_runs` - List workspace runs
- `tf_cloud_get_state_outputs` - Get state outputs

## 🔒 Security Features

- ✅ Rate limiting (100 req/min default, 20 req/min for Terraform)
- ✅ Request validation and sanitization
- ✅ Path traversal protection
- ✅ Command injection prevention
- ✅ Optional API key authentication
- ✅ Audit logging

## 📋 Example Usage

### Basic Terraform Workflow

```javascript
// 1. Create a workspace
terry_workspace_setup(path="my-project", project_name="aws-infra")

// 2. Initialize Terraform
terry(path="my-project", actions=["init"])

// 3. Validate configuration
terraform_validate_lsp(file_path="my-project/main.tf")

// 4. Plan infrastructure
terry(path="my-project", actions=["plan"])
```

### GitHub Integration Workflow

```javascript
// 1. Clone a repository
github_clone_repo(owner="myorg", repo="terraform-modules")

// 2. Prepare workspace from repo
github_prepare_workspace(
  owner="myorg",
  repo="terraform-modules",
  config_path="aws/vpc"
)

// 3. Run Terraform
terry(path="github-repos/myorg/terraform-modules/aws/vpc", actions=["init", "validate", "plan"])
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional: GitHub App authentication
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."

# Optional: Terraform Cloud integration
TF_CLOUD_TOKEN="your-token"

# Optional: API key authentication
TERRY_FORM_API_KEY="your-secret-key"
```

### Optional GitHub Setup

See `docs/GITHUB_APP_SETUP.md` for detailed GitHub App configuration.

## 🐳 Docker Image Details

**Base Image:** `hashicorp/terraform:latest` (Terraform v1.12+)

**Included:**
- Terraform CLI
- terraform-ls v0.33.2 (Language Server)
- Python 3.12+
- FastMCP 2.12.4
- All security and validation components

**Size:** ~150MB

## ✨ What Changed

This version consolidates from 3 server variants to a single, production-ready server:

**REMOVED:**
- `server_mcp_only.py` (had missing dependencies)
- `server_web_only.py` (unused)
- `internal/` modules (empty stubs)

**IMPROVED:**
- Single server with all features
- Fixed Dockerfile to include all required files
- Updated documentation to reflect actual architecture
- Verified all 25 tools work correctly

## 📚 Documentation

- Full Documentation: `README.md`
- API Reference: `docs/api.md`
- Security Guide: `docs/_guides/security.md`
- GitHub Pages: https://aj-geddes.github.io/terry-form-mcp/

## 🆘 Troubleshooting

### Docker Image Not Built
```bash
./build.sh
```

### Server Won't Start
Check Docker is running:
```bash
docker info
```

### Tools Not Working
Verify all 25 tools are loaded:
```bash
docker run --rm terry-form-mcp:latest python3 -c "
from server_enhanced_with_lsp import mcp
print(f'Loaded {len(mcp._tools)} tools')
"
```

## 🎯 Next Steps

1. **Test with your Terraform configs**: Mount your Terraform directory and try it out
2. **Configure GitHub integration**: Set up GitHub App for repository operations
3. **Explore LSP features**: Use code completion and validation tools
4. **Set up monitoring**: Review audit logs for security tracking

---

**Project Status:** ✅ Production Ready - Single Server Architecture

Last Updated: October 2025
