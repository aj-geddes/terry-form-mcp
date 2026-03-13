---
title: Docker Deployment
description: Build, run, verify, and secure the Terry-Form MCP Docker container
order: 3
---

# Docker Deployment Guide

This guide covers building, running, and securing the Terry-Form MCP Docker container.

## Building the Image

### Using the Build Script

```bash
# Linux/macOS
scripts/build.sh

# Windows
scripts\build.bat
```

### Manual Build

```bash
docker build -t terry-form-mcp .
```

The image is built on `{{ site.data.project.base_image }}` (Alpine-based) and includes:
- Terraform {{ site.data.project.terraform }}
- terraform-ls {{ site.data.project.terraform_ls }}
- Python {{ site.data.project.python }}
- All Python dependencies

## Verifying the Build

Run the verification suite (8 checks):

```bash
scripts/verify.sh
```

This verifies:
1. Docker is available
2. Image size is reasonable
3. Terraform is installed and working
4. terraform-ls is installed and working
5. Python runtime is available
6. Required files are present
7. All {{ site.data.project.tool_count }} MCP tools register correctly
8. Server starts up successfully

## Running the Container

### Basic Usage

```bash
docker run -i --rm \
  -v /path/to/workspace:/mnt/workspace \
  terry-form-mcp:latest
```

| Flag | Purpose |
|------|---------|
| `-i` | Interactive mode (required for MCP stdio) |
| `--rm` | Remove container on exit |
| `-v` | Mount workspace directory |

<div class="alert alert-danger">
<strong>Important</strong><br>
Do NOT use <code>-d</code> (detached mode) or <code>-p</code> (port mapping). Terry-Form MCP uses stdio transport, not HTTP. The container is invoked by your MCP client.
</div>

### With Cloud Credentials

```bash
docker run -i --rm \
  -v /path/to/workspace:/mnt/workspace \
  -e AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY \
  -e AWS_DEFAULT_REGION=us-east-1 \
  terry-form-mcp:latest
```

### With GitHub Integration

```bash
docker run -i --rm \
  -v /path/to/workspace:/mnt/workspace \
  -v /path/to/github-app.pem:/keys/github-app.pem:ro \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  -e GITHUB_APP_PRIVATE_KEY_PATH=/keys/github-app.pem \
  terry-form-mcp:latest
```

## Container Security

### Non-Root Execution

The container runs as the `{{ site.data.project.container_user }}` user (UID {{ site.data.project.container_uid }}), not root. This limits the impact of any potential container escape.

### Security-Hardened Run

```bash
docker run -i --rm \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  --read-only \
  --tmpfs /tmp \
  -v /path/to/workspace:/mnt/workspace:rw \
  terry-form-mcp:latest
```

| Option | Purpose |
|--------|---------|
| `--security-opt=no-new-privileges` | Prevent privilege escalation |
| `--cap-drop=ALL` | Drop all Linux capabilities |
| `--read-only` | Read-only root filesystem |
| `--tmpfs /tmp` | Writable temp only in /tmp |

### Resource Limits

```bash
docker run -i --rm \
  --memory=1g \
  --cpus=2 \
  --pids-limit=100 \
  -v /path/to/workspace:/mnt/workspace \
  terry-form-mcp:latest
```

## Image Details

| Property | Value |
|----------|-------|
| Base image | `{{ site.data.project.base_image }}` |
| OS | Alpine Linux |
| Architecture | amd64, arm64 |
| Size | ~150 MB |
| User | `{{ site.data.project.container_user }}` (UID {{ site.data.project.container_uid }}) |
| Entrypoint | `python3 server_enhanced_with_lsp.py` |
| Workdir | `/app` |

## Windows Support

On Windows, use forward slashes or escaped backslashes for volume mounts:

```powershell
# PowerShell
docker run -i --rm `
  -v "${PWD}/workspace:/mnt/workspace" `
  terry-form-mcp:latest
```

```cmd
REM Command Prompt
docker run -i --rm -v "%cd%\workspace:/mnt/workspace" terry-form-mcp:latest
```

### Windows with WSL 2

If using WSL 2 (recommended), Docker Desktop integrates natively:

```bash
docker run -i --rm \
  -v "$(pwd)/workspace:/mnt/workspace" \
  terry-form-mcp:latest
```

## Troubleshooting

### Image Won't Build

```bash
# Check Docker is running
docker info

# Build with verbose output
docker build --progress=plain -t terry-form-mcp .
```

### Permission Denied on Workspace

The container runs as UID {{ site.data.project.container_uid }}. Ensure your workspace is accessible:

```bash
# Option 1: Make workspace world-readable
chmod -R 755 /path/to/workspace

# Option 2: Match the container UID
chown -R {{ site.data.project.container_uid }}:{{ site.data.project.container_uid }} /path/to/workspace
```

### Container Exits Immediately

Terry-Form MCP expects stdin input (MCP protocol). If run without `-i`, it will exit immediately. Always use the `-i` flag.

### Checking Container Contents

```bash
# List installed tools
docker run --rm terry-form-mcp:latest terraform version
docker run --rm terry-form-mcp:latest terraform-ls -version
docker run --rm terry-form-mcp:latest python3 --version

# Check file structure
docker run --rm terry-form-mcp:latest ls -la /app/
```
