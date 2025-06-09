# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup with comprehensive documentation

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

[Unreleased]: https://github.com/aj-geddes/terry-form-mcp/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/aj-geddes/terry-form-mcp/releases/tag/v1.0.0