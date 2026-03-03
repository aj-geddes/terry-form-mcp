---
title: Troubleshooting
description: Solutions for common Docker, MCP, Terraform, LSP, GitHub, and Terraform Cloud issues
order: 9
---

# Troubleshooting Guide

Solutions for common issues with Terry-Form MCP.

## Docker Issues

### Image Won't Build

**Symptom**: `docker build` fails.

**Solutions**:
1. Check Docker is running: `docker info`
2. Ensure sufficient disk space: `docker system df`
3. Build with verbose output: `docker build --progress=plain -t terry-form-mcp .`
4. Clear Docker cache: `docker builder prune`

### Container Exits Immediately

**Symptom**: Container starts and immediately stops.

**Cause**: Terry-Form MCP expects stdin input via MCP protocol.

**Solution**: Always use the `-i` flag:
```bash
docker run -i --rm -v ./workspace:/mnt/workspace terry-form-mcp:latest
```

Do NOT use `-d` (detached mode) — this is a stdio-based server, not an HTTP daemon.

### Permission Denied on Workspace

**Symptom**: Terraform operations fail with permission errors.

**Cause**: Container runs as UID {{ site.data.project.container_uid }}.

**Solutions**:
```bash
# Make workspace accessible
chmod -R 755 /path/to/workspace

# Or match container UID
chown -R {{ site.data.project.container_uid }}:{{ site.data.project.container_uid }} /path/to/workspace
```

### Volume Mount Not Working

**Symptom**: Workspace is empty inside container.

**Solutions**:
- Use absolute paths: `-v /home/user/workspace:/mnt/workspace`
- On Windows, use forward slashes: `-v C:/Users/user/workspace:/mnt/workspace`
- Check Docker Desktop file sharing settings (macOS/Windows)

## MCP Connection Issues

### Client Can't Connect

**Symptom**: AI assistant says it can't reach Terry-Form MCP.

**Checklist**:
1. Verify image exists: `docker images | grep terry-form-mcp`
2. Test manually: `echo '{}' | docker run -i --rm terry-form-mcp:latest python3 -c "print('OK')"`
3. Check MCP client config JSON syntax
4. Restart your AI assistant after config changes

### Tools Not Appearing

**Symptom**: AI assistant doesn't see Terry-Form tools.

**Solutions**:
1. Verify the server starts: `docker run -i --rm terry-form-mcp:latest python3 server_enhanced_with_lsp.py` (should wait for stdin)
2. Check for Python errors in startup
3. Ensure the image is built with the latest code
4. Restart your MCP client

### Timeout Errors

**Symptom**: Tool calls time out.

**Causes and solutions**:
- Large Terraform workspaces: Increase client timeout
- First LSP call: Initial terraform-ls startup takes 1-2 seconds
- Network issues: Check Docker network configuration
- Resource limits: Increase `--memory` and `--cpus` limits

## Terraform Issues

### "Not Initialized"

**Symptom**: `validate` or `plan` fails with "not initialized".

**Solution**: Run `init` first:
```json
{"path": "my-project", "actions": ["init", "validate", "plan"]}
```

### Provider Download Fails

**Symptom**: `init` fails to download providers.

**Causes**:
- No internet access from container
- Provider registry is down
- Network proxy not configured

**Solutions**:
```bash
# Check DNS resolution
docker run --rm terry-form-mcp:latest nslookup registry.terraform.io

# Use a proxy
docker run -i --rm \
  -e HTTP_PROXY=http://proxy:8080 \
  -e HTTPS_PROXY=http://proxy:8080 \
  -v ./workspace:/mnt/workspace \
  terry-form-mcp:latest
```

### "Action Blocked" Error

**Symptom**: Tool returns "action blocked" error.

**Cause**: `apply`, `destroy`, `import`, `taint`, and `untaint` are permanently blocked.

**Solution**: These actions cannot be enabled. Use Terry-Form MCP for planning and validation only. Run `apply`/`destroy` through your standard Terraform workflow.

### Path Traversal Error

**Symptom**: "Path traversal detected" error.

**Cause**: The path parameter tries to access files outside `/mnt/workspace`.

**Solution**: Use relative paths within the workspace:
```json
// Wrong
{"path": "/etc/secrets"}
{"path": "../../../etc/passwd"}

// Correct
{"path": "my-project"}
{"path": "environments/dev"}
```

## LSP Issues

### LSP Not Working

**Symptom**: `terraform_hover`, `terraform_complete`, etc. return errors.

**Diagnostic steps**:
1. Check terraform-ls: `terry_environment_check`
2. Debug LSP: `terry_lsp_debug`
3. Initialize manually: `terry_lsp_init` with workspace path
4. Verify .tf files exist: `terry_file_check`

### Slow LSP Responses

**Cause**: First call initializes terraform-ls (1-2 second startup).

**Solutions**:
- Call `terry_lsp_init` proactively to warm up
- Ensure workspace is initialized (`init`) before using LSP tools
- Reduce workspace size if possible

### No Completions Available

**Causes**:
- Workspace not initialized (no provider schemas downloaded)
- Invalid cursor position (line/character are 0-based)
- File doesn't exist

**Solution**: Run `init` first, then verify with `terry_file_check`.

## GitHub Issues

### "Private Key Not Found"

**Solution**: Check the file is mounted correctly:
```bash
docker run -i --rm \
  -v /path/to/key.pem:/keys/github-app.pem:ro \
  -e GITHUB_APP_PRIVATE_KEY_PATH=/keys/github-app.pem \
  ...
```

### "Failed to Get Installation Token"

**Checklist**:
1. Verify `GITHUB_APP_ID` is correct
2. Verify `GITHUB_APP_INSTALLATION_ID` is correct
3. Check the app is still installed on the target account
4. Ensure the private key matches the app (not rotated)

### "Repository Not Accessible"

**Solution**: Check the GitHub App has access to the repository:
1. Go to GitHub App settings > Install App
2. Verify the repository is in the selected list
3. Check the app has "Contents: Read" permission

## Terraform Cloud Issues

### "Token Not Set"

**Solution**: Set the `TF_CLOUD_TOKEN` environment variable:
```bash
docker run -i --rm \
  -e TF_CLOUD_TOKEN="your-token" \
  ...
```

### "Organization Not Found"

**Solution**: Verify the organization name matches exactly (case-sensitive) and your token has access.

## Debug Logging

Enable verbose logging for any issue:

```bash
docker run -i --rm \
  -e LOG_LEVEL=DEBUG \
  -v ./workspace:/mnt/workspace \
  terry-form-mcp:latest
```

This shows detailed information about:
- Tool invocations and parameters
- Terraform command execution
- LSP client communication
- GitHub API calls
- Rate limit status
