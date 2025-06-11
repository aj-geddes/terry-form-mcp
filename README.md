# Terry-Form-MCP

Terraform MCP (Machine Callable Program) server that enables AI assistants to execute Terraform commands locally through a secure, containerized environment using HashiCorp's official Terraform Docker image.

## Features

- Built on official HashiCorp Terraform image
- Includes terraform-ls v0.33.2 for Language Server Protocol (LSP) integration
- Comprehensive diagnostic and utility tools
- Enhanced LSP client with robust error handling
- Secure containerized execution environment

## Quick Start

### Build the Docker Image

```bash
# Make the build script executable
chmod +x build.consolidated.sh

# Build the Docker image
./build.consolidated.sh
```

### Run the MCP Server

```bash
docker run -it --rm -p 8000:8000 -v "$(pwd):/mnt/workspace" terry-form-mcp:latest
```

## MCP Tools

### Core Terraform Tools

- `terry`: Runs terraform actions in /mnt/workspace/<path> using provided variables
  - Supported actions: init, validate, fmt, plan

### Diagnostic Tools

- `terry_environment_check`: Comprehensive environment check for Terraform and LSP integration
- `terry_lsp_debug`: Debug terraform-ls functionality and LSP client state
- `terry_workspace_info`: Analyze Terraform workspace structure and provide recommendations
- `terry_lsp_init`: Manually initialize LSP client for a specific workspace
- `terry_file_check`: Check Terraform file syntax and readiness for LSP operations
- `terry_workspace_setup`: Create a properly structured Terraform workspace ready for LSP operations

### LSP Tools

- `terraform_validate_lsp`: Validate a Terraform file using terraform-ls Language Server
- `terraform_hover`: Get documentation for Terraform resource at cursor position
- `terraform_complete`: Get completion suggestions for Terraform code at cursor position
- `terraform_format_lsp`: Format a Terraform file using terraform-ls Language Server
- `terraform_lsp_status`: Get the status of the terraform-ls Language Server integration

## Integration with AI Assistants

This MCP server is designed to be used with AI assistants that support the MCP protocol. It allows AI assistants to:

1. Execute Terraform commands (init, validate, fmt, plan)
2. Get intelligent code completion suggestions
3. Validate Terraform configurations
4. Format Terraform code
5. Get documentation for Terraform resources
6. Set up and manage Terraform workspaces

## Security Considerations

- The server runs in a containerized environment for isolation
- Only specific Terraform commands are allowed (no apply or destroy)
- File system access is limited to the mounted workspace directory

## Development

### Project Structure

- `terry-form-mcp.py`: Core Terraform execution logic
- `terraform_lsp_client.py`: LSP client implementation
- `server_enhanced_with_lsp.py`: FastMCP server with LSP integration
- `Dockerfile.consolidated`: Docker image definition
- `build.consolidated.sh`: Build script

### Adding New Features

1. Add new tools to `server_enhanced_with_lsp.py`
2. Update the LSP client in `terraform_lsp_client.py` if needed
3. Rebuild the Docker image with `./build.consolidated.sh`

## License

MIT

## Acknowledgments

- HashiCorp for Terraform and terraform-ls
- Anthropic for the MCP protocol and integration support