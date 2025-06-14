# Terry-Form MCP Client Configuration

This directory contains the client configuration and tools to connect Claude Desktop to Terry-Form MCP running in Kubernetes.

## Files

- `claude_desktop_config_stdio.json` - Claude Desktop configuration for macOS/Linux
- `claude_desktop_config_windows.json` - Claude Desktop configuration for Windows with WSL
- `terry-form-mcp-client.py` - Python client that bridges stdio transport to HTTP
- `mcp_client_wrapper.sh` - Shell script for manual port forwarding
- `test_connection.py` - Test script to verify connectivity
- `SETUP.md` - Detailed setup instructions

## Quick Setup

1. **Deploy Terry-Form MCP to Kubernetes** (if not already done):
```bash
helm install terry-form-mcp ../deploy/kubernetes/helm/terry-form-mcp \
  --namespace terry-form-system \
  --create-namespace \
  --values ../deploy/kubernetes/helm/values-minikube.yaml
```

2. **Test the connection**:
```bash
python3 test_connection.py
```

3. **Configure Claude Desktop**:

For macOS/Linux:
```bash
cp claude_desktop_config_stdio.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

For Windows:
```bash
cp claude_desktop_config_windows.json /mnt/c/Users/$USER/AppData/Roaming/Claude/claude_desktop_config.json
```

4. **Update the path** in the config file to point to your terry-form-mcp-client.py location

5. **Restart Claude Desktop**

## Current Status

✅ Kubernetes deployment working with minimal server
✅ Health checks passing
✅ Client infrastructure ready
❌ Full MCP server with FastMCP needs dependency fixes

## Next Steps

To use Terry-Form MCP with Claude Desktop:

1. Fix the pydantic dependency issues in the main server
2. Build and deploy the full v3.0.0 image with MCP endpoints
3. Use the client configuration provided here

The client is ready and will work once the full Terry-Form MCP server is running with proper MCP endpoints.