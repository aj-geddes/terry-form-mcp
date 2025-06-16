# Terry Enterprise Deployment Guide

## Overview

This guide covers deploying Terry (Terraform Registry MCP Server) in Enterprise Mode for production Kubernetes environments. Enterprise Mode provides full Terraform Cloud integration, enhanced monitoring, and is designed for team-wide deployments.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐     ┌─────────────────┐    ┌──────────────┐  │
│  │   Ingress       │────▶│  Terry Service  │───▶│ Terry Pods   │  │
│  │  Controller     │     │   (ClusterIP)   │    │ (Replicas: 2)│  │
│  └─────────────────┘     └─────────────────┘    └──────────────┘  │
│                                                          │          │
│  ┌─────────────────┐     ┌─────────────────┐          │          │
│  │   ConfigMap     │     │     Secret      │◀─────────┘          │
│  │  (terry-config) │     │ (terry-secrets) │                      │
│  └─────────────────┘     └─────────────────┘                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Future: MCP Bridge                         │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │  │
│  │  │ MCP Bridge  │───▶│ Message Bus │◀───│ LLM Service │     │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘     │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.x installed
- kubectl configured with cluster access
- Terraform Cloud API token
- Ingress controller (nginx recommended)
- Container registry access

## Deployment Options

### Option 1: Helm Chart (Recommended)

#### 1. Prepare Values File

Create `terry-values.yaml`:

```yaml
# Mode configuration
mode: enterprise

# Terraform Cloud token (required for enterprise mode)
tfcToken: "your-terraform-cloud-api-token"

# Image configuration
image:
  repository: terraform-mcp-server
  tag: "0.13.0"
  pullPolicy: IfNotPresent

# Resource allocation
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

# Scaling configuration
replicaCount: 2
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# Service configuration
service:
  type: ClusterIP
  port: 80
  mcpPort: 9090

# Ingress configuration
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: terry.company.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: terry-tls
      hosts:
        - terry.company.com

# Configuration
config:
  logLevel: info
  requestTimeoutMs: 10000
  rateLimitEnabled: true
  rateLimitRequests: 60
  rateLimitWindowMs: 60000
```

#### 2. Deploy with Helm

```bash
# Add repository (if published)
helm repo add terry https://your-helm-repo.com
helm repo update

# Or install from local chart
helm install terry ./charts/terry \
  --namespace terry \
  --create-namespace \
  --values terry-values.yaml

# Verify deployment
helm status terry -n terry
kubectl get pods -n terry
```

#### 3. Upgrade Deployment

```bash
# Update values and upgrade
helm upgrade terry ./charts/terry \
  --namespace terry \
  --values terry-values.yaml

# Rollback if needed
helm rollback terry 1 -n terry
```

### Option 2: Direct Kubernetes Manifests

#### 1. Create Namespace

```bash
kubectl create namespace terry
```

#### 2. Create Secret

```bash
# Create secret with your TFC token
kubectl create secret generic terry-secrets \
  --namespace terry \
  --from-literal=tfc-token='your-terraform-cloud-api-token'
```

#### 3. Apply Manifests

```bash
# Apply all manifests
kubectl apply -f k8s/ -n terry

# Or individually
kubectl apply -f k8s/configmap.yaml -n terry
kubectl apply -f k8s/deployment.yaml -n terry
kubectl apply -f k8s/service.yaml -n terry
kubectl apply -f k8s/ingress.yaml -n terry
```

## Production Configuration

### High Availability

```yaml
# Ensure multiple replicas
spec:
  replicas: 3
  
# Pod disruption budget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: terry-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: terry-mcp-server
```

### Resource Management

```yaml
# Production resources
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

### Security Hardening

```yaml
# Security context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  capabilities:
    drop:
      - ALL
  readOnlyRootFilesystem: true
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: terry-network-policy
spec:
  podSelector:
    matchLabels:
      app: terry-mcp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS for external APIs
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 53   # DNS
```

## Monitoring and Observability

### Prometheus Metrics

Add annotations for Prometheus scraping:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "3000"
    prometheus.io/path: "/metrics"
```

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
```

### Logging

Configure structured logging:

```bash
# View logs
kubectl logs -n terry -l app=terry-mcp-server

# Stream logs
kubectl logs -n terry -l app=terry-mcp-server -f

# Export to logging system
kubectl logs -n terry -l app=terry-mcp-server --timestamps=true
```

## Integration with LLM Services

### MCP Bridge Setup (Future)

```yaml
# Deploy MCP Bridge alongside Terry
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-bridge
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: mcp-bridge
        image: mcp-bridge:latest
        env:
        - name: TERRY_ENDPOINT
          value: "http://terry-mcp-server:9090"
        - name: LLM_ENDPOINT
          value: "http://llm-service:8080"
```

### Service Mesh Integration

For Istio:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: terry-mcp-server
  labels:
    app: terry-mcp-server
    service: terry-mcp-server
spec:
  ports:
  - port: 80
    name: http-web
  - port: 9090
    name: grpc-mcp
```

## Backup and Disaster Recovery

### Configuration Backup

```bash
# Backup configuration
kubectl get configmap terry-config -n terry -o yaml > terry-config-backup.yaml
kubectl get secret terry-secrets -n terry -o yaml > terry-secrets-backup.yaml

# Backup Helm values
helm get values terry -n terry > terry-values-backup.yaml
```

### Restore Procedure

```bash
# Restore from backup
kubectl apply -f terry-config-backup.yaml
kubectl apply -f terry-secrets-backup.yaml

# Or with Helm
helm install terry ./charts/terry \
  --namespace terry \
  --values terry-values-backup.yaml
```

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod -n terry -l app=terry-mcp-server

# Common causes:
# - Missing TFC_TOKEN secret
# - Insufficient resources
# - Image pull errors
```

#### Connection Issues

```bash
# Test service connectivity
kubectl run test-pod --rm -i --tty --image=busybox -- /bin/sh
wget -O- http://terry-mcp-server.terry.svc.cluster.local/health

# Check ingress
kubectl describe ingress terry-mcp-server -n terry
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n terry

# Scale if needed
kubectl scale deployment terry-mcp-server -n terry --replicas=5
```

### Debug Mode

Enable debug logging:

```yaml
config:
  logLevel: debug
```

### Exec into Pod

```bash
kubectl exec -it -n terry deploy/terry-mcp-server -- /bin/sh
```

## Maintenance

### Rolling Updates

```bash
# Update image
kubectl set image deployment/terry-mcp-server \
  terry=terraform-mcp-server:0.14.0 \
  -n terry

# Monitor rollout
kubectl rollout status deployment/terry-mcp-server -n terry
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment terry-mcp-server -n terry --replicas=5

# HPA status
kubectl get hpa -n terry
```

### Certificate Renewal

If using cert-manager:
```bash
# Check certificate status
kubectl get certificate -n terry

# Force renewal if needed
kubectl delete certificate terry-tls -n terry
```

## Security Best Practices

1. **Token Management**
   - Use Kubernetes secrets for TFC_TOKEN
   - Rotate tokens regularly
   - Consider using external secret managers

2. **Network Security**
   - Implement network policies
   - Use TLS for all external communication
   - Restrict egress to required endpoints

3. **RBAC**
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: terry-role
     namespace: terry
   rules:
   - apiGroups: [""]
     resources: ["secrets", "configmaps"]
     verbs: ["get", "list"]
   ```

4. **Image Security**
   - Scan images for vulnerabilities
   - Use specific tags, not `latest`
   - Sign images with cosign

## Compliance and Auditing

### Audit Logging

```yaml
# Add audit annotations
metadata:
  annotations:
    audit.company.com/classification: "internal"
    audit.company.com/data-type: "terraform-metadata"
```

### Compliance Checks

```bash
# Run compliance scan
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml

# Check results
kubectl logs job/kube-bench
```

## Cost Optimization

1. **Right-size Resources**
   - Monitor actual usage with `kubectl top`
   - Adjust requests/limits accordingly

2. **Use Spot Instances**
   ```yaml
   nodeSelector:
     node.kubernetes.io/lifecycle: spot
   tolerations:
   - key: "spot"
     operator: "Equal"
     value: "true"
     effect: "NoSchedule"
   ```

3. **Implement HPA**
   - Scale down during low usage
   - Set appropriate min/max replicas

## Support and Maintenance

### Health Monitoring

- Dashboard URL: http://terry.company.com
- Health endpoint: http://terry.company.com/health
- Status API: http://terry.company.com/api/status

### Log Analysis

```bash
# Error analysis
kubectl logs -n terry -l app=terry-mcp-server | grep ERROR

# Request patterns
kubectl logs -n terry -l app=terry-mcp-server | grep "tool:"
```

### Performance Metrics

Monitor key metrics:
- Response time (p50, p95, p99)
- Error rate
- Pod resource usage
- API rate limits

This completes the enterprise deployment guide for Terry MCP Server.