# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.1.0] - 2026-03-03

### Changed
- **Dependencies**: Full rewrite of `requirements.txt` with updated versions
  - `fastmcp` 0.x -> 3.0+, `aiohttp` 3.8 -> 3.13+, `PyJWT` 2.8 -> 2.11+
  - `cryptography` 41 -> 46+, `jsonschema` 4.19 -> 4.26+ (requires Python >= 3.10)
  - `asyncio-lru` renamed to `async-lru` (PyPI package rename)
  - Removed unused `openai` and `anthropic` dependencies
- **Docker**: Pinned `hashicorp/terraform:1.12`, upgraded `terraform-ls` 0.33.2 -> 0.38.5
- **Dockerfile**: Now installs full requirements.txt instead of just fastmcp
- **Dockerfile_github_enhanced**: Removed references to deleted files (`server_mcp_only.py`, `server_web_only.py`, `internal/`)
- **Imports**: Replaced fragile `importlib.util.spec_from_file_location` hacks with standard `import`/`from` statements
- **Shutdown**: Replaced duplicated `atexit`/`signal`/`KeyboardInterrupt` cleanup with FastMCP 3.0 `lifespan` context manager
- **Decorator**: Consolidated `validate_request` sync/async wrappers (~135 lines) into shared `_pre_validate`/`_post_process` helpers (~55 lines)

### Fixed
- **LSP client None reference**: `_lsp_client.initialization_error` was accessed after setting `_lsp_client = None`, always returning "Unknown error"
- **Bare except clauses**: Changed `except:` to `except Exception:` in `terry_workspace_list`
- **Logging**: Replaced `print()` calls with `logger.info()`/`logger.error()` in GitHub integration setup
- **Redundant import**: Removed `import re` inside loop body (already imported at module level)
- **Blocking I/O in async**: Replaced synchronous `open()` calls in LSP client with `asyncio.to_thread(Path.read_text)`
- **Unbounded wait**: Added 5-second timeout to `process.wait()` in LSP shutdown, with `kill()` fallback

### Security
- **Webhook verification**: Changed `verify_webhook` to return `False` (not `True`) when no webhook secret is configured
- **API version constant**: Extracted hardcoded `"2022-11-28"` into `GITHUB_API_VERSION` module-level constant
- **Compiled regex**: Pre-compiled all Terraform file analysis regex patterns at module level for performance and safety

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

[Unreleased]: https://github.com/aj-geddes/terry-form-mcp/compare/v3.1.0...HEAD
[3.1.0]: https://github.com/aj-geddes/terry-form-mcp/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/aj-geddes/terry-form-mcp/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/aj-geddes/terry-form-mcp/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/aj-geddes/terry-form-mcp/releases/tag/v1.0.0