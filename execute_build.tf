terraform {
  required_version = ">= 1.0"
}

# Execute enhanced Docker build
data "external" "build_enhanced_lsp" {
  program = ["bash", "/mnt/workspace/terry-form-mcp/build_enhanced_lsp.sh"]
}

output "build_result" {
  value = data.external.build_enhanced_lsp.result
}
