# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] - 2025-10-05

### 🎯 Major Release - Production Ready

This release represents a complete refactoring and cleanup of the Terry-Form MCP codebase, resulting in a focused, production-ready single-server architecture with comprehensive documentation.

### Added
- **Complete Tool Coverage**: All 25 MCP tools now fully documented
  - Core Terraform Tools (4): terry, terry_version, terry_environment_check, terry_workspace_list
  - LSP Intelligence (5): terraform_validate_lsp, terraform_hover, terraform_complete, terraform_format_lsp, terraform_lsp_status
  - Diagnostic Tools (6): terry_lsp_debug, terry_workspace_info, terry_lsp_init, terry_file_check, terry_workspace_setup, terry_analyze
  - Intelligence Tools (2): terry_recommendations, terry_security_scan
  - GitHub Integration (4): github_clone_repo, github_list_terraform_files, github_get_terraform_config, github_prepare_workspace
  - Terraform Cloud (4): tf_cloud_list_workspaces, tf_cloud_get_workspace, tf_cloud_list_runs, tf_cloud_get_state_outputs

- **Production Tooling**:
  - `verify.sh` - Comprehensive 8-step verification script
  - `QUICKSTART.md` - Complete quick start guide
  - Enhanced security validation with `mcp_request_validator.py`
  - Rate limiting and authentication framework

### Changed
- **Single Server Architecture**: Consolidated from 3 server variants to one focused server
  - `server_enhanced_with_lsp.py` - Single point of entry with all features
  - Removed `server_mcp_only.py` (had missing dependencies)
  - Removed `server_web_only.py` (unused)

- **Clean Codebase**: Removed all legacy and unused code
  - Removed `terry-form-mcp.py` (old standalone script, not imported)
  - Removed `internal/` directory (empty stub modules)
  - Removed broken `tests/` directory (missing test_base.py)
  - Docker image now copies only 5 required Python files (down from 6)

- **Documentation Overhaul**:
  - README.md: Added documentation for all 13 previously undocumented tools
  - docs/_api/mcp-tools.md: Complete reference for all 25 tools with examples
  - docs/index.md: Updated for v3.0.0 features
  - docs/getting-started.md: Fixed installation instructions (removed nonexistent Docker Hub image, corrected stdio transport)
  - Removed all false claims (Module Intelligence, Web Dashboard, Kubernetes)
  - Clarified Terraform Cloud tools return mock data

### Fixed
- **Dockerfile**:
  - Removed `terry-form-mcp.py` from COPY commands
  - Fixed health check for stdio MCP protocol (was incorrectly checking port 8000)
  - Added all required supporting files (mcp_request_validator.py, github_*.py)

- **Documentation Accuracy**:
  - Removed claims about non-existent features
  - Updated all server file references to correct filename
  - Fixed Docker installation instructions
  - Corrected project structure documentation

### Security
- Enhanced input validation and sanitization
- Path traversal protection
- Command injection prevention
- Rate limiting (100 req/min default, 20 req/min for Terraform operations)
- Optional API key authentication

### Verification
- ✅ Docker build succeeds with cleaned Dockerfile
- ✅ All 25 tools verified present and documented
- ✅ `verify.sh` passes all 8 checks
- ✅ Server starts cleanly with all components (security validator, rate limiter, auth)
- ✅ No unused/legacy code remains

### Breaking Changes
- Removed `server_mcp_only.py` and `server_web_only.py` - use `server_enhanced_with_lsp.py` only
- Removed `internal/` module structure - all code now in root-level modules

## [2.0.0] - 2025-06-11

### Added
- Comprehensive Language Server Protocol (LSP) integration
- Intelligent code completion, documentation, and validation
- 6 new diagnostic tools for environment and workspace analysis
- Enhanced Dockerfile with terraform-ls v0.33.2

### Changed
- Consolidated multiple Dockerfiles into a single Dockerfile
- Consolidated build scripts into build.sh and build.bat
- Improved error handling and workspace management
- Updated documentation with new LSP features and examples

### Fixed
- LSP client initialization and stability improvements
- Enhanced error handling with detailed error messages
- Improved timeout handling for LSP operations

## [1.0.0] - 2025-06-09

### Added
- FastMCP server implementation for Terraform operations
- Docker containerization using HashiCorp Terraform image
- Support for Terraform actions: init, validate, fmt, plan
- Secure workspace isolation and variable injection
- Structured JSON output for AI assistant integration
- Comprehensive documentation and usage examples
- MIT License
- Docker-based testing framework

### Security
- Container isolation for all Terraform operations
- Read-only operations only (no apply/destroy)
- Workspace path validation and restriction
- No Terraform state file access

### Documentation
- Complete README with architecture diagrams
- Configuration examples for Claude Desktop
- Troubleshooting guide and best practices
- Security considerations and limitations

[Unreleased]: https://github.com/aj-geddes/terry-form-mcp/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/aj-geddes/terry-form-mcp/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/aj-geddes/terry-form-mcp/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/aj-geddes/terry-form-mcp/releases/tag/v1.0.0