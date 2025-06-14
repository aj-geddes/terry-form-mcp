terraform {
  required_version = ">= 1.0"
}

# Test Docker availability and build readiness
data "external" "docker_check" {
  program = ["sh", "-c", "echo '{\"docker_available\": \"'$(docker --version > /dev/null 2>&1 && echo true || echo false)'\", \"build_files_ready\": \"'$(ls /mnt/workspace/terry-form-mcp/Dockerfile_enhanced_lsp /mnt/workspace/terry-form-mcp/server_enhanced_with_lsp.py > /dev/null 2>&1 && echo true || echo false)'\", \"current_images\": \"'$(docker images | grep terry-form-mcp | wc -l)'\"}'"]
}

output "docker_readiness" {
  value = data.external.docker_check.result
}
