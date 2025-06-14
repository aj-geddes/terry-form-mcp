# Terry-Form MCP Authentication Setup

Terry-Form MCP supports GitHub and Azure authentication through Kubernetes secrets. This enables automated git operations and cloud resource management.

## GitHub Authentication

### Option 1: Personal Access Token (PAT)

Create a secret with your GitHub Personal Access Token:

```bash
kubectl create secret generic github-auth \
  --namespace=terry-form-system \
  --from-literal=credentials='{
    "type": "pat",
    "token": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", 
    "username": "your-github-username"
  }'
```

### Option 2: GitHub App

Create a secret with your GitHub App credentials:

```bash
kubectl create secret generic github-auth \
  --namespace=terry-form-system \
  --from-literal=credentials='{
    "type": "github_app",
    "app_id": "123456",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
    "installation_id": "12345678"
  }'
```

Then enable GitHub authentication in your Helm values:

```yaml
terryform:
  auth:
    github:
      enabled: true
      secretName: "github-auth"
```

## Azure Authentication

### Option 1: Service Principal

Create a secret with Azure Service Principal credentials:

```bash
kubectl create secret generic azure-auth \
  --namespace=terry-form-system \
  --from-literal=credentials='{
    "type": "service_principal",
    "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "client_secret": "your-client-secret",
    "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }'
```

### Option 2: User Token

Create a secret with Azure user token:

```bash
kubectl create secret generic azure-auth \
  --namespace=terry-form-system \
  --from-literal=credentials='{
    "type": "user_token",
    "access_token": "your-access-token",
    "refresh_token": "your-refresh-token",
    "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }'
```

Then enable Azure authentication in your Helm values:

```yaml
terryform:
  auth:
    azure:
      enabled: true
      secretName: "azure-auth"
```

## Required Permissions

### GitHub PAT Permissions
- `repo` - Full control of private repositories
- `workflow` - Update GitHub Action workflows  
- `write:packages` - Upload packages to GitHub Package Registry

### GitHub App Permissions
- Repository permissions:
  - Contents: Read and write
  - Metadata: Read
  - Pull requests: Read and write
  - Issues: Read and write

### Azure Service Principal Permissions
- `Contributor` role on the subscription or resource group
- `User Access Administrator` role if managing RBAC

## Installation with Authentication

Deploy Terry-Form MCP with authentication enabled:

```bash
# Create secrets first
kubectl create secret generic github-auth --namespace=terry-form-system --from-literal=credentials='...'
kubectl create secret generic azure-auth --namespace=terry-form-system --from-literal=credentials='...'

# Deploy with authentication enabled
helm install terry-form-mcp ./deploy/kubernetes/helm/terry-form-mcp \
  --namespace terry-form-system \
  --create-namespace \
  --set terryform.auth.github.enabled=true \
  --set terryform.auth.azure.enabled=true \
  --values values-minikube.yaml
```

## Verifying Authentication

Once deployed, you can check authentication status through the MCP interface:

1. Access the frontend at http://localhost:7575
2. Use the `auth_status` tool to verify credentials are loaded
3. Try cloning a private repository to test GitHub authentication
4. Use Azure-related tools to test Azure authentication

## Security Notes

- Secrets are mounted as read-only volumes in `/var/run/secrets/`
- All credentials are stored as JSON objects in Kubernetes secrets
- Git credentials are automatically configured on container startup
- Authentication status can be monitored through the MCP tools

## Troubleshooting

### GitHub Authentication Issues
```bash
# Check if secret exists
kubectl get secret github-auth -n terry-form-system

# Check secret contents (be careful with sensitive data)
kubectl get secret github-auth -n terry-form-system -o jsonpath='{.data.credentials}' | base64 -d

# Check pod logs for authentication errors
kubectl logs -n terry-form-system deployment/terry-form-mcp
```

### Azure Authentication Issues
```bash
# Test Azure CLI authentication inside the pod
kubectl exec -n terry-form-system deployment/terry-form-mcp -- az account show

# Check Azure secret
kubectl get secret azure-auth -n terry-form-system -o jsonpath='{.data.credentials}' | base64 -d
```