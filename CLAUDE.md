# Development Workflow for Terry-Form MCP

## Fast Kubernetes Development Workflow

When developing and testing Helm charts in Kubernetes:

1. **Use namespace isolation**: Always deploy to a dedicated namespace
2. **Fast cleanup**: Delete the entire namespace instead of individual resources
3. **Auto-create namespace**: Use `--create-namespace` flag with helm install
4. **Quick iteration cycle**:
   ```bash
   # Delete namespace (removes EVERYTHING)
   kubectl delete namespace terry-form-system --wait
   
   # Deploy with auto-create namespace
   helm install terry-form-mcp ./terry-form-mcp \
     --namespace terry-form-system \
     --create-namespace \
     --values values-minikube.yaml
   ```

This is MUCH faster than trying to clean up individual resources!