# Terry Helm Chart

This Helm chart deploys Terry (Terraform Registry MCP Server) in Enterprise Mode on Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.x
- Terraform Cloud API token (for TFC features)

## Installation

### Quick Install

```bash
helm install terry ./charts/terry \
  --namespace terry \
  --create-namespace \
  --set tfcToken=your-terraform-cloud-token
```

### Custom Values Install

1. Create your values file:
```yaml
# my-values.yaml
tfcToken: "your-terraform-cloud-token"
ingress:
  enabled: true
  hosts:
    - host: terry.mycompany.com
      paths:
        - path: /
          pathType: Prefix
```

2. Install with custom values:
```bash
helm install terry ./charts/terry \
  --namespace terry \
  --create-namespace \
  --values my-values.yaml
```

## Configuration

Key configuration options:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mode` | Server mode (local/enterprise) | `enterprise` |
| `tfcToken` | Terraform Cloud API token | `""` |
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Image repository | `terraform-mcp-server` |
| `image.tag` | Image tag | `latest` |
| `service.type` | Service type | `ClusterIP` |
| `ingress.enabled` | Enable ingress | `false` |
| `resources.requests.memory` | Memory request | `256Mi` |
| `resources.requests.cpu` | CPU request | `250m` |

## Upgrading

```bash
helm upgrade terry ./charts/terry \
  --namespace terry \
  --values my-values.yaml
```

## Uninstalling

```bash
helm uninstall terry --namespace terry
```

## Examples

### With Ingress and TLS

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: terry.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: terry-tls
      hosts:
        - terry.example.com
```

### With Autoscaling

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
```

### Production Resources

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```