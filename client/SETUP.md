# Terry-Form MCP Client Setup

This guide helps you connect Claude Desktop to Terry-Form MCP running in Kubernetes.

## Prerequisites

1. Terry-Form MCP deployed to Kubernetes
2. kubectl configured and able to access your cluster
3. Python 3.x installed
4. requests package installed (`pip install requests`)

## Quick Start

### 1. Verify Terry-Form MCP is Running

```bash
# Check if Terry-Form MCP is deployed
kubectl get pods -n terry-form-system

# Test health endpoint manually
kubectl port-forward -n terry-form-system service/terry-form-mcp 8080:8000 &
curl http://localhost:8080/health
```

### 2. Install the MCP Client

```bash
# Make the client executable
chmod +x /path/to/terry-form-mcp/client/terry-form-mcp-client.py

# Test the client works
python3 /path/to/terry-form-mcp/client/terry-form-mcp-client.py
# (Press Ctrl+C to exit)
```

### 3. Configure Claude Desktop

#### For macOS/Linux:

1. Copy the configuration to Claude Desktop config directory:
```bash
cp claude_desktop_config_stdio.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. Update the path in the config to match your installation:
```json
{
  "mcpServers": {
    "terry-form-mcp": {
      "command": "python3",
      "args": [
        "/absolute/path/to/terry-form-mcp/client/terry-form-mcp-client.py"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "KUBECONFIG": "${HOME}/.kube/config"
      }
    }
  }
}
```

#### For Windows (WSL):

1. Copy the Windows configuration:
```bash
cp claude_desktop_config_windows.json /mnt/c/Users/YOUR_USERNAME/AppData/Roaming/Claude/claude_desktop_config.json
```

2. Update the path to match your WSL installation.

### 4. Restart Claude Desktop

After updating the configuration, restart Claude Desktop for the changes to take effect.

## Testing the Connection

Once configured, you should see Terry-Form MCP in Claude Desktop's MCP servers list. 

Test it by asking Claude to:
- List available Terraform tools
- Run terraform init on a directory
- Validate Terraform configurations
- Format Terraform files

## Troubleshooting

### Connection Issues

1. Check kubectl connectivity:
```bash
kubectl cluster-info
kubectl get pods -n terry-form-system
```

2. Test port forwarding manually:
```bash
kubectl port-forward -n terry-form-system service/terry-form-mcp 8080:8000
# In another terminal:
curl http://localhost:8080/health
```

3. Check client logs:
```bash
# Run the client manually to see output
python3 /path/to/terry-form-mcp-client.py
```

### Common Errors

- **"kubectl not found"**: Make sure kubectl is installed and in your PATH
- **"Connection refused"**: Terry-Form MCP pod might not be running
- **"Namespace not found"**: Deploy Terry-Form MCP first using Helm

## Advanced Configuration

### Custom Namespace or Port

Edit the client script to use different values:

```python
client = TerryFormMCPClient(
    namespace="custom-namespace",
    service="custom-service",
    local_port=9090,
    remote_port=8000
)
```

### Using with Different Kubernetes Contexts

Set the KUBECONFIG environment variable in the Claude Desktop config:

```json
"env": {
  "KUBECONFIG": "/path/to/custom/kubeconfig",
  "PYTHONUNBUFFERED": "1"
}
```

## Security Considerations

- The client creates a local port forward to access the Kubernetes service
- No credentials are stored; it uses your existing kubectl configuration
- The connection is only accessible from localhost

## Support

For issues or questions:
- Check Terry-Form MCP logs: `kubectl logs -n terry-form-system -l app.kubernetes.io/name=terry-form-mcp`
- Review the test suite for examples: `tests/integration/test_mcp_server.py`