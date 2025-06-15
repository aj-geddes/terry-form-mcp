# Terry-Form MCP Kubernetes Deployment

## Security Notice

**IMPORTANT**: Never commit actual API keys, passwords, or other sensitive credentials to version control.

## Deploying with Secrets

### Using Vault/OpenBao

1. Store your secrets in Vault/OpenBao:
   ```bash
   vault kv put secret/terry-form/ai-service credentials=@ai-service-creds.json
   vault kv put secret/terry-form/azure-auth credentials=@azure-creds.json
   vault kv put secret/terry-form/github-auth credentials=@github-creds.json
   ```

2. Deploy using the Vault-enabled Helm chart:
   ```bash
   helm install terry-form-mcp ./helm/terry-form-mcp \
     --namespace terry-form-system \
     --create-namespace \
     --values values-vault.yaml
   ```

### Manual Testing Deployment

1. Copy `test-deployment-example.yaml` to a secure location
2. Replace all placeholder values with your actual credentials
3. Deploy: `kubectl apply -f test-deployment.yaml`
4. **Delete the file after deployment**

## Secret Format

Terry-Form MCP expects secrets in the following format:

### AI Service (Anthropic)
```json
{
  "provider": "anthropic",
  "api_key": "YOUR_ANTHROPIC_API_KEY",
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 8192,
  "temperature": 0
}
```

### Azure Authentication
```json
{
  "type": "service_principal",
  "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### GitHub Authentication
```json
{
  "type": "pat",
  "token": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "username": "your-github-username"
}
```

## Best Practices

1. Use a proper secret management solution (Vault, Sealed Secrets, etc.)
2. Rotate credentials regularly
3. Use least-privilege access for all service accounts
4. Enable audit logging for secret access
5. Never log or output credentials in your applications