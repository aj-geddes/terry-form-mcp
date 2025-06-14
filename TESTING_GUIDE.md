# Terry-Form MCP v3.0.0 Testing Guide

This guide explains how to test Terry-Form MCP v3.0.0 deployed in Kubernetes with the web-based testing interface.

## Current Deployment Status

✅ **Successfully Deployed Components:**
- Terry-Form MCP HTTP Server (FastMCP with streamable-http transport)
- Health check endpoints on port 8001
- MCP protocol endpoints on port 8000
- Sample Terraform configuration in `/mnt/workspace/test`
- Web-based testing frontend on port 7575

## Quick Start Testing

### 1. Verify Deployment

```bash
# Check pod status
kubectl get pods -n terry-form-system

# Check logs
kubectl logs -n terry-form-system -l app.kubernetes.io/name=terry-form-mcp
```

### 2. Port Forwarding Setup

```bash
# Forward MCP service (if not already running)
kubectl port-forward -n terry-form-system service/terry-form-mcp 8080:8000 &

# Forward health check port (optional)
kubectl port-forward -n terry-form-system pod/<pod-name> 8001:8001 &
```

### 3. Test Health Endpoints

```bash
# Via service (through port-forward)
curl http://localhost:8080/health  # Should return 404 (not on MCP port)

# Direct to health port
curl http://localhost:8001/health
# Response: {"status": "healthy", "version": "v3.0.0-http", "service": "terry-form-mcp"}

curl http://localhost:8001/ready
# Response: {"status": "ready", "terraform": true, "version": "v3.0.0-http"}
```

### 4. Access Web Testing Interface

Open your browser to: **http://localhost:7575**

The interface provides:
- **Tool Browser**: View and execute all MCP tools
- **Workspace Explorer**: Browse files in /mnt/workspace
- **Quick Actions**: One-click Terraform operations
- **Live Results**: Execution results with syntax highlighting

## Available MCP Tools

The following tools are available via the MCP protocol:

1. **terraform_init** - Initialize Terraform working directory
2. **terraform_validate** - Validate Terraform configuration
3. **terraform_fmt** - Check Terraform formatting
4. **terraform_plan** - Create execution plan
5. **terraform_version** - Get Terraform version
6. **workspace_list** - List workspace contents
7. **workspace_info** - Get path information
8. **create_terraform_file** - Create new .tf files

## Testing Terraform Operations

### Using the Web Interface

1. Navigate to http://localhost:7575
2. Select a tool from the left panel
3. Enter parameters (e.g., path: "test")
4. Click "Execute Tool"
5. View results in the main panel

### Using curl (Direct MCP Protocol)

```bash
# List available tools
curl -X POST http://localhost:8080/mcp/sse \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Initialize Terraform in test directory
curl -X POST http://localhost:8080/mcp/sse \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "terraform_init",
      "arguments": {"path": "test"}
    },
    "id": 2
  }'
```

## Test Scenarios

### 1. Basic Terraform Workflow

```bash
# Via web interface Quick Actions:
1. Click "Terraform Init" (uses test directory)
2. Click "Terraform Validate"
3. Click "Terraform Format Check"
4. Click "Terraform Plan"
```

### 2. Create New Terraform Project

Using the web interface:
1. Select "create_terraform_file" tool
2. Set parameters:
   - path: "myproject"
   - filename: "main.tf"
   - content: (paste your Terraform code)
3. Execute
4. Run terraform_init on "myproject"

### 3. Test with Variables

1. Select "terraform_plan" tool
2. Set path: "test"
3. Add variables in JSON format:
   ```json
   {"environment": "production"}
   ```

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Web Browser    │────▶│  Frontend        │────▶│  Terry-Form    │
│  localhost:7575 │     │  (Python/Aiohttp)│     │  MCP Server    │
└─────────────────┘     └──────────────────┘     └────────────────┘
                                                           │
                                                           ▼
                                                  ┌────────────────┐
                                                  │   Kubernetes   │
                                                  │   Deployment   │
                                                  └────────────────┘
```

## Troubleshooting

### Frontend Connection Issues

```bash
# Check if frontend is running
ps aux | grep "frontend/app.py"

# Restart frontend if needed
pkill -f "frontend/app.py"
cd /mnt/c/Users/Munso/terry-form-mcp
python3 frontend/app.py &
```

### MCP Server Issues

```bash
# Check MCP logs
kubectl logs -n terry-form-system -l app.kubernetes.io/name=terry-form-mcp --tail=50

# Check port forwarding
lsof -i :8080

# Restart port forward
pkill -f "kubectl port-forward"
kubectl port-forward -n terry-form-system service/terry-form-mcp 8080:8000 &
```

### Common Errors

1. **"Server: disconnected"** in web interface
   - Ensure port forwarding is active
   - Check if pod is running

2. **Empty tool list**
   - MCP server may still be starting
   - Check logs for errors

3. **Tool execution fails**
   - Verify workspace path exists
   - Check Terraform is available in container

## Next Steps

1. **Use with Claude Desktop**: Configure the MCP client (see client/README.md)
2. **Production Deployment**: Use values-production.yaml with proper secrets
3. **Enable Features**: Configure GitHub App, Terraform Cloud, etc.
4. **Custom Terraform Modules**: Upload your own modules to test

## Support

- Logs: `kubectl logs -n terry-form-system -l app.kubernetes.io/name=terry-form-mcp`
- Events: `kubectl get events -n terry-form-system --sort-by='.lastTimestamp'`
- Pod Details: `kubectl describe pod -n terry-form-system <pod-name>`