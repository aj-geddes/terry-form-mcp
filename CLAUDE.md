# CLAUDE.md

> **AI Skill**: Load `.claude/skills/terry-form-mcp-expert/SKILL.md` at the start of each session.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Terry-Form MCP is a production-ready Model Context Protocol (MCP) server that provides AI-powered Terraform execution within Docker containers. It exposes 25 MCP tools for Terraform operations, LSP-based intelligence, GitHub integration, and Terraform Cloud connectivity. Version 3.1.0. Requires Python >= 3.10.

## Build & Run Commands

```bash
# Build Docker image
scripts/build.sh              # Linux/macOS
scripts\build.bat             # Windows
docker build -t terry-form-mcp .

# Run verification suite (8 checks: Docker, image size, Terraform, terraform-ls, Python, files, tools, startup)
scripts/verify.sh

# Run the server directly (requires dependencies)
pip install -r requirements.txt
python3 src/server_enhanced_with_lsp.py

# Run core module standalone
python3 src/terry-form-mcp.py < tests/fixtures/test.json

# Integration test via Docker
docker run -i --rm -v "$(pwd):/mnt/workspace" terry-form-mcp:latest python3 terry-form-mcp.py < test.json

# Code quality
black .                       # Format (88 char line limit)
flake8 .                      # Lint
mypy src/*.py                 # Type check
```

## Architecture

### Entry Point & Server

`src/server_enhanced_with_lsp.py` is the single entry point — a FastMCP async server that registers all 25 tools via `@mcp.tool()` decorators. It consolidates what were previously 3 separate server variants.

### Module Responsibilities

- **`src/terry-form-mcp.py`** — Core Terraform subprocess execution. Handles `init`, `validate`, `fmt`, `plan` (never `apply`/`destroy`). Manages workspace isolation at `/mnt/workspace`.
- **`src/terraform_lsp_client.py`** — Async LSP client wrapping `terraform-ls`. Provides hover info, completions, diagnostics, and formatting. First call may take ~1-2s for LSP initialization.
- **`src/mcp_request_validator.py`** — Input sanitization and security validation. Prevents path traversal, enforces JSON schema, applies rate limiting (20 req/min Terraform, 30 req/min GitHub, 100 req/min default).
- **`src/github_repo_handler.py`** — Clone repos and extract Terraform files from GitHub.
- **`src/github_app_auth.py`** — GitHub App OAuth with JWT/PyJWT authentication.

### Tool Categories (25 total)

| Category | Prefix | Count |
|---|---|---|
| Core Terraform | `terry_*` | 4 |
| LSP Intelligence | `terraform_*` | 5 |
| Diagnostics | `terry_lsp_*`, `terry_file_*`, `terry_workspace_*`, `terry_analyze` | 6 |
| Security & Recommendations | `terry_security_scan`, `terry_recommendations` | 2 |
| GitHub Integration | `github_*` | 4 |
| Terraform Cloud | `tf_cloud_*` | 4 |

### Container Architecture

The Dockerfile builds on `hashicorp/terraform:1.12` (Alpine-based, ~150MB). It includes `terraform-ls` v0.38.5 for LSP support. Runs as non-root user `terraform` (UID 1001). All Terraform operations are workspace-isolated to `/mnt/workspace`.

## Key Constraints

- **No destructive Terraform operations** — `apply` and `destroy` are intentionally blocked. Only `init`, `validate`, `fmt`, and `plan` are allowed.
- **Workspace isolation** — All file operations are restricted to `/mnt/workspace`. Path traversal is actively prevented.
- **Forced environment variables** — `TF_IN_AUTOMATION=true`, `TF_INPUT=false`, `CHECKPOINT_DISABLE=true` are always set.
- **Async throughout** — The server uses `asyncio` with `FastMCP`. All tool handlers are async.

## Commit Convention

```
feat: add feature description
fix: resolve issue
docs: update documentation
test: add tests
```

Present tense, imperative mood, 72-char first line limit.
