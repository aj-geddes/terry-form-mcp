# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/aj-geddes/terry-form-mcp/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/aj-geddes/terry-form-mcp/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/aj-geddes/terry-form-mcp/releases/tag/v1.0.0