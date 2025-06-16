# Kubernetes Deployment for Terry MCP Server (Enterprise Mode)

This directory contains Kubernetes manifests for deploying Terry in Enterprise mode.

## Prerequisites

- Kubernetes cluster (1.19+)
- kubectl configured
- Docker image of Terry built and pushed to a registry

## Quick Start

1. **Update the secret with your TFC token:**
   ```bash
   kubectl create secret generic terry-secrets \
     --from-literal=tfc-token=YOUR_ACTUAL_TFC_TOKEN
   ```

2. **Apply the manifests:**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Check deployment status:**
   ```bash
   kubectl get pods -l app=terry-mcp-server
   kubectl get svc terry-mcp-server
   ```

## Components

- **Deployment**: Runs 2 replicas of Terry in enterprise mode
- **Service**: Exposes Terry on port 80 (web UI) and 9090 (MCP)
- **ConfigMap**: Contains environment configuration
- **Secret**: Stores sensitive data (TFC token)
- **Ingress**: Exposes Terry to external traffic

## Configuration

Edit `configmap.yaml` to adjust:
- `LOG_LEVEL`: Logging verbosity
- `RATE_LIMIT_*`: Rate limiting settings
- `REQUEST_TIMEOUT_MS`: API request timeout

## Accessing the Web UI

### Using NodePort (for testing):
```bash
kubectl get svc terry-mcp-server-nodeport
# Access at http://<node-ip>:30000
```

### Using Ingress (production):
1. Update `ingress.yaml` with your domain
2. Ensure you have an ingress controller installed
3. Access at http://terry.example.com

## MCP Bridge Integration

For LLM integration, deploy an MCP bridge alongside Terry:

```yaml
# Example MCP bridge deployment (coming soon)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-bridge
spec:
  # ... MCP bridge configuration
```

## Monitoring

Terry exposes health endpoints:
- `/health` - Basic health check
- `/api/status` - Detailed status including mode and features

## Troubleshooting

1. **Check logs:**
   ```bash
   kubectl logs -l app=terry-mcp-server
   ```

2. **Verify TFC token:**
   ```bash
   kubectl describe secret terry-secrets
   ```

3. **Test connectivity:**
   ```bash
   kubectl exec -it deploy/terry-mcp-server -- curl http://localhost:3000/health
   ```