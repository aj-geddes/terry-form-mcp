# terry-form-mcp-expert Skill

## Skill Metadata
- **Version**: 1.0.0
- **Last Updated**: 2026-03-04
- **Project**: Terry-Form MCP
- **Skill Path**: .claude/skills/terry-form-mcp-expert/SKILL.md

## Purpose & Invocation

This skill makes the AI assistant an expert in everything about the Terry-Form MCP project. It should be loaded at the start of every session by referencing this file.

Trigger phrases (any of these should cause the AI to load this skill):
- "start a session on terry-form-mcp"
- "load project context"
- "you are the terry-form-mcp expert"
- "what do you know about this project"

## Session Start Protocol

When this skill is invoked, the AI assistant MUST:

1. Read this file completely before responding to any task
2. State which version of the skill was loaded and the last-updated date
3. Summarize the project in 2-3 sentences to confirm context is loaded
4. Ask the developer what they are working on today
5. Check git status and git log --oneline -10 to understand current state
6. Flag any known issues from the Gotchas section relevant to today's work

## Project Overview

Terry-Form MCP is a production-ready Model Context Protocol (MCP) server that provides AI-powered Terraform execution within Docker containers. It exposes 25 MCP tools for Terraform operations (init, validate, fmt, plan), LSP-based code intelligence via terraform-ls, GitHub App integration, and Terraform Cloud connectivity. The server communicates via MCP stdio transport — there is no HTTP server, no web dashboard, and no exposed ports.

The project serves infrastructure teams that want to safely automate Terraform workflows through AI assistants like Claude Desktop. Security is the core design principle: destructive operations (apply, destroy) are permanently blocked, all file access is isolated to `/mnt/workspace`, inputs are sanitized against injection, and the container runs as a non-root user (UID 1001). Version 3.1.0 requires Python >= 3.10.

The documentation site at https://aj-geddes.github.io/terry-form-mcp is a Jekyll-based GitHub Pages site with a dark-first glassmorphism design, covering 10 guides, 6 tutorials, API reference for all 25 tools, and architecture documentation.

## Architecture

```
AI Assistant (Claude Desktop / CI)
        |
        | MCP stdio (stdin/stdout JSON-RPC)
        v
+------- Docker Container (hashicorp/terraform:1.12, Alpine) -------+
|                                                                     |
|  server_enhanced_with_lsp.py  (FastMCP 3.0+ async entry point)     |
|       |          |           |            |           |             |
|  terry-form-  terraform_  mcp_request_  github_    github_         |
|  mcp.py       lsp_client  validator.py  app_auth   repo_handler   |
|  (Terraform   .py         (Security)    .py        .py            |
|   executor)   (LSP)                     (Auth)     (Git ops)      |
|       |          |                                                  |
|  Terraform    terraform-ls                                          |
|  1.12 CLI     0.38.5                                               |
|       |                                                             |
|  /mnt/workspace (volume mount, all ops isolated here)              |
+---------------------------------------------------------------------+
```

### Data Flow
1. AI assistant sends MCP tool request via stdio (JSON-RPC)
2. FastMCP server routes to the appropriate `@mcp.tool()` handler
3. `mcp_request_validator.py` validates input (path traversal, action whitelist, rate limits)
4. Handler executes operation (Terraform subprocess, LSP request, GitHub API, TF Cloud API)
5. Result returned as MCP response via stdio

### Key Design Decisions
- **Single entry point**: `src/server_enhanced_with_lsp.py` registers all 25 tools. Earlier versions had 3 separate servers — they were consolidated in v3.0.0.
- **Async throughout**: All tool handlers are async using `asyncio` with FastMCP. The LSP client uses async subprocess communication.
- **Lazy LSP initialization**: The terraform-ls process starts on first use (1-2s cold start), not at server boot.
- **Pre-compiled regex**: All Terraform analysis patterns are compiled at module load to prevent regex DoS.

### Anti-patterns (Do NOT)
- Never add HTTP endpoints, web dashboards, or port exposure — MCP uses stdio only
- Never implement `apply` or `destroy` — this is a design constraint, not a bug
- Never use `shell=True` in subprocess calls — command injection risk
- Never access files outside `/mnt/workspace` — path traversal is actively prevented
- Never use blocking I/O in tool handlers — everything must be async

## Tech Stack Reference

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| Runtime | Python | >= 3.10 | Required for `asyncio` features and `jsonschema` |
| MCP Framework | FastMCP | >= 3.0.0 | Async tool registration via `@mcp.tool()` decorators |
| IaC | Terraform | 1.12 | Pinned in Dockerfile base image |
| LSP | terraform-ls | 0.38.5 | HashiCorp Language Server for code intelligence |
| HTTP Client | aiohttp | >= 3.13.0 | Async HTTP for GitHub/TF Cloud APIs |
| Auth | PyJWT + cryptography | 2.11+ / 46+ | GitHub App JWT authentication (RS256) |
| Validation | jsonschema | >= 4.26.0 | Input schema enforcement |
| Container | Docker (Alpine) | hashicorp/terraform:1.12 | ~150MB image, non-root user |
| Linting | ruff | >= 0.9.0 | Fast Python linter |
| Security Lint | bandit | >= 1.8.0 | Python security scanner |
| Formatting | black | >= 24.0.0 | 88-char line limit |
| Type Checking | mypy | >= 1.13.0 | Static type analysis |
| Testing | pytest + pytest-asyncio | 9.0+ / 0.25+ | Async test support |
| Docs Site | Jekyll + GitHub Pages | Ruby 3.1 | Dark-first glassmorphism design |

## Directory Map

```
terry-form-mcp/
├── .claude/                          # Claude Code project config
│   ├── CLAUDE.md                     # KAD system activation
│   └── skills/                       # Project-scoped AI skills
├── .github/
│   └── workflows/
│       └── docs-builder.yaml         # Jekyll → GitHub Pages deployment
├── docs/                             # Jekyll documentation site
│   ├── _config.yml                   # Jekyll configuration
│   ├── _data/project.yml             # Single source of truth for versions
│   ├── _includes/                    # 8 reusable HTML partials
│   ├── _layouts/                     # 6 page layouts (default, home, guide, tutorial, api, page)
│   ├── _api/                         # API reference collection
│   ├── _architecture/                # Architecture docs collection
│   ├── _guides/                      # 10 guides collection
│   ├── _tutorials/                   # 6 tutorials collection
│   ├── assets/css/style.scss         # Dark-first design system
│   ├── assets/js/main.js             # Theme toggle, TOC, code copy, mobile nav
│   ├── Gemfile                       # Ruby dependencies
│   └── index.md                      # Homepage
├── examples/                         # Example Terraform configurations
├── src/                              # Application source
│   ├── server_enhanced_with_lsp.py   # Main entry point — FastMCP server (1905 lines)
│   ├── terry-form-mcp.py            # Core Terraform subprocess execution (426 lines)
│   ├── terraform_lsp_client.py      # Async LSP client for terraform-ls (487 lines)
│   ├── mcp_request_validator.py     # Input validation & security (258 lines)
│   ├── github_app_auth.py           # GitHub App JWT/OAuth authentication (214 lines)
│   ├── github_repo_handler.py       # GitHub repo clone/extract operations (359 lines)
│   └── frontend/                    # HAT stack web UI
├── tests/                            # All test files
│   ├── conftest.py
│   ├── test_*.py
│   └── fixtures/                    # Test data (test.json, sample projects)
├── scripts/                          # Build & utility scripts
│   ├── build.sh / build.bat
│   ├── verify.sh
│   └── export_tools_json.py
├── k8s/                              # Kubernetes manifests
├── Dockerfile                        # Production container definition
├── requirements.txt                  # Python dependencies
├── CLAUDE.md                         # Project instructions for AI assistants
├── CHANGELOG.md                      # Version history
├── CONTRIBUTING.md                   # Contribution guidelines
├── QUICKSTART.md                     # Quick start guide
├── README.md                         # Project documentation
└── LICENSE                           # MIT License
```

## Development Workflows

### Getting Started
```bash
# Clone the repository
git clone https://github.com/aj-geddes/terry-form-mcp.git
cd terry-form-mcp

# Option A: Docker (recommended)
scripts/build.sh                      # Build the Docker image
scripts/verify.sh                     # Run 8-check verification suite

# Option B: Local development
pip install -r requirements.txt       # Install Python dependencies
python3 src/server_enhanced_with_lsp.py  # Run the MCP server directly
```

### Running the App
```bash
# Production: Docker with workspace mount
docker run -i --rm -v "$(pwd)/workspace:/mnt/workspace" terry-form-mcp:latest

# Development: Direct Python execution
python3 src/server_enhanced_with_lsp.py

# Core module standalone test
python3 src/terry-form-mcp.py < tests/fixtures/test.json

# Integration test via Docker
docker run -i --rm -v "$(pwd):/mnt/workspace" terry-form-mcp:latest python3 terry-form-mcp.py < test.json
```

### Running Tests
```bash
# All tests
pytest

# Single test file
pytest test_server.py

# Async tests with verbose output
pytest -v --timeout=30

# With coverage (if configured)
pytest --cov=. --cov-report=term-missing
```

### Linting & Formatting
```bash
black .                               # Format (88 char line limit)
ruff check .                          # Fast linting
flake8 .                              # Additional linting
mypy src/*.py                         # Type checking
bandit -r src/ -x ./docs              # Security scan
```

### Building
```bash
# Docker image
scripts/build.sh                      # Linux/macOS
scripts\build.bat                     # Windows
docker build -t terry-form-mcp .      # Manual

# Documentation site
cd docs
bundle install
bundle exec jekyll build              # Build to _site/
bundle exec jekyll serve              # Local dev server at localhost:4000
```

## CI/CD Reference

### Pipelines

| Pipeline | Trigger | Stages | Deploys To |
|----------|---------|--------|------------|
| docs-builder.yaml | Push to `main` (docs/** paths), PRs, manual | Ruby setup → Jekyll build → Upload artifact → Deploy | GitHub Pages (aj-geddes.github.io/terry-form-mcp) |

### Required Secrets / Env Vars

| Variable | Where Set | Purpose |
|----------|-----------|---------|
| `GITHUB_APP_ID` | Container env | GitHub App ID for repo integration (optional) |
| `GITHUB_APP_INSTALLATION_ID` | Container env | GitHub App installation ID (optional) |
| `GITHUB_APP_PRIVATE_KEY` | Container env | GitHub App PEM private key (optional) |
| `TF_CLOUD_TOKEN` | Container env | Terraform Cloud API token (optional) |
| `LOG_LEVEL` | Container env | Logging level: INFO (default) or DEBUG |
| `TERRY_FORM_API_KEY` | Container env | Optional API key for authentication |
| `TF_IN_AUTOMATION` | Forced to `true` | Suppresses interactive Terraform prompts |
| `TF_INPUT` | Forced to `false` | Prevents Terraform input requests |
| `CHECKPOINT_DISABLE` | Forced to `true` | Disables Terraform update checks |

### Deployment Procedure

**Documentation Site:**
1. Merge changes to `main` branch (must touch `docs/**` or workflow)
2. GitHub Actions automatically: installs Ruby 3.1 → bundles gems → builds Jekyll → deploys to Pages
3. Concurrency group `"pages"` ensures only one deployment at a time
4. Verify at https://aj-geddes.github.io/terry-form-mcp

**Docker Image (Manual):**
1. Make code changes and test locally
2. Run `scripts/build.sh` to build image
3. Run `scripts/verify.sh` to validate (8 checks must pass)
4. Push to registry if applicable (no automated Docker CI currently)

### Rollback Procedure

**Documentation:**
- `git revert <commit>` and push to `main` — Pages auto-redeploys

**Docker Image:**
- Rebuild from a previous commit: `git checkout <tag> && scripts/build.sh`
- No container registry automation — images are built locally or in user CI

## Security Standards

- **Auth pattern**: Optional API key via `TERRY_FORM_API_KEY` env var; GitHub App OAuth (JWT RS256) for repo operations; role-based permissions (admin, user, readonly)
- **Secret management**: Environment variables passed to Docker container at runtime; GitHub App private keys via env var or file path; no secrets stored in code or images
- **Security scanning**: `bandit` for Python security linting; built-in `terry_security_scan` tool (CKV-style checks); `ruff` for code quality
- **Known constraints**: `apply` and `destroy` are permanently blocked — this is by design and must never be changed; all file operations restricted to `/mnt/workspace`; `shell=False` enforced on all subprocess calls

### Security Checklist (apply before every PR)
- [ ] No secrets in code, logs, or Docker image layers
- [ ] Input validation on all external data (paths, actions, variables)
- [ ] Path traversal prevention verified (all paths resolve within `/mnt/workspace`)
- [ ] No new subprocess calls with `shell=True`
- [ ] No new Terraform actions added to the allowed list without security review
- [ ] Dependencies checked for CVEs (`pip audit` or `bandit`)
- [ ] Rate limiting applied to any new tool
- [ ] Non-root container execution preserved
- [ ] Dangerous character pattern (`[$\`\\\"';|&><(){}]`) applied to user inputs

## Testing Standards

- **Framework**: pytest with pytest-asyncio for async handlers
- **Coverage gate**: No enforced threshold currently
- **Test layout**: Test files in `tests/` directory, fixtures in `tests/fixtures/`
- **How to run all tests**: `pytest`
- **How to run one test**: `pytest tests/test_file.py::test_function -v`
- **Integration testing**: `docker run -i --rm -v "$(pwd):/mnt/workspace" terry-form-mcp:latest python3 terry-form-mcp.py < test.json`
- **Known state**: Test files are excluded from version control in `.gitignore` (`test_*.py`); the verify.sh script serves as the primary validation mechanism (8 checks)

## Git & PR Conventions

- **Branching strategy**: Trunk-based development on `main`; feature branches for PRs (e.g., `claude/feature-name-<id>`)
- **Commit format**: Conventional Commits — `feat:`, `fix:`, `docs:`, `test:`, `refactor:`. Present tense, imperative mood, 72-char first line limit
- **PR requirements**: Review required; CI checks must pass; merge to `main`
- **Release process**: Update version in code → update CHANGELOG.md → create release PR → tag release → build Docker → create GitHub release

## Observability

- **Logging**: Python `logging` module; format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`; level controlled by `LOG_LEVEL` env var (default: INFO); logs to stderr (stdout reserved for MCP stdio)
- **Metrics**: Rate limiter tracks request counts per tool category; no external metrics pipeline
- **Tracing**: No distributed tracing; tool invocations logged with user/role context
- **Alerting**: No automated alerting; operational monitoring via Docker healthcheck (`python3 -c "import server_enhanced_with_lsp"` every 30s)

## All 25 MCP Tools Reference

| # | Tool | Category | Description |
|---|------|----------|-------------|
| 1 | `terry` | Core Terraform | Execute Terraform operations (init, validate, fmt, plan, show, graph, providers, version) |
| 2 | `terraform_validate_lsp` | LSP Intelligence | Validate Terraform files via LSP diagnostics |
| 3 | `terraform_hover` | LSP Intelligence | Get documentation at cursor position |
| 4 | `terraform_complete` | LSP Intelligence | Get code completion suggestions |
| 5 | `terraform_format_lsp` | LSP Intelligence | Format Terraform files via LSP |
| 6 | `terraform_lsp_status` | LSP Intelligence | Check LSP server status |
| 7 | `terry_workspace_list` | Diagnostics | List all available workspaces with metadata |
| 8 | `terry_workspace_info` | Diagnostics | Analyze workspace structure and LSP readiness |
| 9 | `terry_workspace_setup` | Diagnostics | Create properly structured Terraform workspace |
| 10 | `terry_version` | Diagnostics | Get Terraform and provider version information |
| 11 | `terry_environment_check` | Diagnostics | Check container environment, tools, and config |
| 12 | `terry_lsp_debug` | Diagnostics | Debug terraform-ls functionality |
| 13 | `terry_file_check` | File Operations | Check Terraform file syntax and readiness |
| 14 | `terry_analyze` | Security & Recs | Analyze Terraform config for best practices |
| 15 | `terry_security_scan` | Security & Recs | Run security scan for vulnerabilities (CKV checks) |
| 16 | `terry_recommendations` | Security & Recs | Get recommendations by focus area |
| 17 | `tf_cloud_list_workspaces` | Terraform Cloud | List TF Cloud workspaces |
| 18 | `tf_cloud_get_workspace` | Terraform Cloud | Get detailed workspace info |
| 19 | `tf_cloud_list_runs` | Terraform Cloud | List workspace runs with status |
| 20 | `tf_cloud_get_state_outputs` | Terraform Cloud | Get state outputs from workspace |
| 21 | `github_clone_repo` | GitHub Integration | Clone or update GitHub repository |
| 22 | `github_list_terraform_files` | GitHub Integration | List Terraform files in repository |
| 23 | `github_get_terraform_config` | GitHub Integration | Analyze Terraform configuration |
| 24 | `github_prepare_workspace` | GitHub Integration | Prepare workspace from GitHub repo |
| 25 | `terry_lsp_init` | LSP Init | Manually initialize LSP client for workspace |

## Known Issues, Debt & Gotchas

- [GOTCHA] **Mermaid diagrams in docs need quoted labels** — Node labels starting with `/` trigger trapezoid parsing (`[/mnt/workspace]` fails), and double quotes inside brackets fail (`[module "vpc"]`). Use `["/mnt/workspace"]` and `["module vpc"]` instead. The `mermaid.html` include uses `mermaid.render()` API to avoid HTML entity encoding issues with arrows.

- [GOTCHA] **Liquid templates don't work in YAML front matter** — `{{ site.data.project.version }}` in a Jekyll front matter `description:` field renders literally, not as the substituted value. Hardcode values in front matter; use Liquid only in body content.

- [GOTCHA] **LSP cold start latency** — First call to any `terraform_*` LSP tool takes 1-2 seconds while terraform-ls initializes. Subsequent calls are fast. The `terry_lsp_init` tool exists for explicit pre-warming.

- [GOTCHA] **test.json must use MCP JSON-RPC format** — Integration testing via `python3 src/terry-form-mcp.py < tests/fixtures/test.json` expects the raw module format, not MCP protocol. Use `docker run -i` for MCP stdio testing.

- [GOTCHA] **docs/_site/ is committed** — The Jekyll build output is tracked in git. Changes to source files require rebuilding (`bundle exec jekyll build`) and committing both source and `_site/`. The GitHub Actions workflow also builds from source.

- [GOTCHA] **docs/vendor/bundle/ must NOT be committed** — Local `bundle install` creates this directory. It is not in `.gitignore` so care must be taken to avoid staging it.

- [DEBT] **No automated Docker CI** — Docker image builds are manual (`scripts/build.sh`). There is no workflow to build, test, and push images to a registry on release.

- [DEBT] **Test files excluded from VCS** — `.gitignore` excludes `test_*.py`, so there are no committed test files. The 8-check `verify.sh` script is the primary validation, but unit tests should be committed.

- [DEBT] **CONTRIBUTING.md references Python 3.8+** — The actual requirement is Python 3.10+ (per `requirements.txt` and `CLAUDE.md`). The contributing guide is outdated.

- [DEBT] **No pre-commit hooks** — No `.pre-commit-config.yaml` or equivalent. Linting/formatting depends on developer discipline.

- [FRAGILE] **Rate limiter is in-memory** — Request counts are stored in deques in the server process. Restarting the container resets all counters. This is fine for single-instance stdio but would break in a multi-instance scenario.

- [FRAGILE] **GitHub App token caching** — Installation tokens are cached with a 5-minute TTL check. If the server process restarts, cached tokens are lost and re-authentication is needed (adds latency).

- [FRAGILE] **docs/_data/project.yml is the version source of truth for docs** — Version numbers in the docs site come from this file. If the server version changes, this file must be updated manually to keep docs accurate.

## Skill Maintenance

This skill is a living document. The AI assistant MUST update it when:

- A new dependency is added or removed
- A pipeline changes
- A new environment is introduced
- A gotcha is discovered or resolved
- An architectural decision is made
- A security control is added or changed
- A new MCP tool is added or removed
- The project version changes

Update format: Add a dated entry to the changelog below and update the relevant section.

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-03-04 | Initial skill creation via deep codebase reconnaissance | AI |
