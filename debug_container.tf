terraform {
  required_version = ">= 1.0"
}

# Debug the built container to understand the issues
data "external" "container_debug" {
  program = ["sh", "-c", "echo '{\"container_ls\": \"'$(docker run --rm terry-form-mcp-lsp-enhanced:latest ls -la /app/ 2>/dev/null | tr '\\n' ' ' || echo 'failed')'\", \"terraform_path\": \"'$(docker run --rm terry-form-mcp-lsp-enhanced:latest which terraform 2>/dev/null || echo 'not found')'\", \"terraform_ls_path\": \"'$(docker run --rm terry-form-mcp-lsp-enhanced:latest which terraform-ls 2>/dev/null || echo 'not found')'\", \"python_version\": \"'$(docker run --rm terry-form-mcp-lsp-enhanced:latest python3 --version 2>/dev/null || echo 'not found')'\"}'"]
}

output "container_debug" {
  value = data.external.container_debug.result
}
