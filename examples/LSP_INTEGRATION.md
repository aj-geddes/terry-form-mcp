# Terry-Form MCP with LSP Integration

## LSP Integration Overview

This enhanced version of Terry-Form MCP includes **terraform-ls** Language Server Protocol integration, providing intelligent Terraform development capabilities alongside the existing execution features.

### New LSP-Powered Tools

#### `terraform_validate_lsp`
Advanced validation using terraform-ls Language Server
```json
{
  "tool": "terraform_validate_lsp",
  "arguments": {
    "file_path": "main.tf",
    "workspace_path": "infrastructure/aws"
  }
}
```

#### `terraform_hover`
Get documentation and information for Terraform elements
```json
{
  "tool": "terraform_hover", 
  "arguments": {
    "file_path": "main.tf",
    "line": 15,
    "character": 20,
    "workspace_path": "infrastructure/aws"
  }
}
```

#### `terraform_complete`
Intelligent code completion suggestions
```json
{
  "tool": "terraform_complete",
  "arguments": {
    "file_path": "variables.tf",
    "line": 10,
    "character": 5,
    "workspace_path": "infrastructure/aws"
  }
}
```

#### `terraform_format_lsp`
Format Terraform files using LSP
```json
{
  "tool": "terraform_format_lsp",
  "arguments": {
    "file_path": "main.tf",
    "workspace_path": "infrastructure/aws"
  }
}
```

#### `terraform_lsp_status`
Check terraform-ls server status
```json
{
  "tool": "terraform_lsp_status",
  "arguments": {}
}
```

## Claude Desktop Integration

### Configuration
Add this to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "terry-form-lsp": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "C:\\Users\\YourUsername\\terraform-projects:/mnt/workspace",
        "terry-form-mcp-lsp"
      ]
    }
  }
}
```

### Usage Examples with Claude

#### Intelligent Code Review
```
"I'm working on my Terraform configuration in infrastructure/aws/main.tf. Can you:
1. Validate the file using LSP for detailed diagnostics
2. Show me documentation for the aws_instance resource on line 25
3. Suggest completions for the security_groups parameter
4. Format the file properly"
```

#### Interactive Development
```
"I'm at line 15, character 10 in my variables.tf file. What Terraform 
resources or attributes can I use here? Also validate the current file."
```

#### Advanced Validation
```
"Compare the validation results between the traditional terraform validate 
and the LSP-based validation for my main.tf file. Show me any additional
insights the LSP provides."
```

## Building and Running

### Build LSP-Enabled Image
```bash
# Build the enhanced image with terraform-ls
./build_lsp.sh
```

### Run with LSP Support
```bash
# Start MCP server with LSP capabilities
docker run -it --rm \
  -v "$(pwd):/mnt/workspace" \
  terry-form-mcp-lsp
```

### Test LSP Integration
```bash
# Run comprehensive test suite
docker run -i --rm \
  -v "$(pwd):/mnt/workspace" \
  terry-form-mcp-lsp \
  python3 test_lsp_integration.py
```

## Architecture

### LSP Client Implementation
- **JSON-RPC Communication**: Handles LSP protocol with terraform-ls
- **Asynchronous Operations**: Non-blocking LSP requests
- **Workspace Management**: Automatic workspace detection and initialization
- **Error Handling**: Graceful handling of LSP errors and timeouts

### MCP Tool Integration
- **Dual Capabilities**: Both execution (terry) and intelligence (LSP) tools
- **Unified Interface**: Consistent MCP tool patterns
- **Path Resolution**: Automatic workspace and file path resolution
- **Resource Management**: Proper LSP client lifecycle management

## Troubleshooting LSP Integration

### Common Issues

1. **terraform-ls not found**
   ```bash
   # Verify terraform-ls installation
   docker run --rm terry-form-mcp-lsp terraform-ls version
   ```

2. **LSP initialization timeout**
   ```bash
   # Check workspace has valid Terraform files
   # Ensure proper file permissions
   ```

3. **Workspace detection issues**
   ```bash
   # Verify workspace_path parameter
   # Check file_path is relative to workspace
   ```

### Debug Mode
```bash
# Run with debug logging
docker run -i --rm \
  -e TF_LOG=DEBUG \
  -v "$(pwd):/mnt/workspace" \
  terry-form-mcp-lsp
```

## Performance Considerations

### LSP Startup Time
- First LSP tool call initializes terraform-ls (2-3 seconds)
- Subsequent calls reuse the same LSP instance
- Workspace initialization happens once per workspace

### Resource Usage
- terraform-ls process runs in background
- Memory usage: ~50-100MB additional
- CPU usage: Minimal for typical operations

### Optimization Tips
- Group multiple LSP operations for same workspace
- Use terraform_lsp_status to verify initialization
- Consider workspace_path parameter for performance

## Migration from Original Version

### Backward Compatibility
- All original `terry` tool functionality preserved
- Existing configurations work unchanged
- Docker image includes both versions

### New Capabilities
- Intelligent code completion
- Real-time validation with diagnostics
- Hover documentation
- LSP-based formatting
- Workspace-aware operations

### Upgrade Path
1. Build new `terry-form-mcp-lsp` image
2. Update Claude Desktop configuration
3. Test with both execution and LSP tools
4. Gradually adopt LSP features

## Contributing to LSP Integration

### Development Setup
```bash
# Clone repository
git clone https://github.com/aj-geddes/terry-form-mcp.git
cd terry-form-mcp

# Install development dependencies
pip install fastmcp asyncio

# Build and test
./build_lsp.sh
```

### Testing New Features
```bash
# Run specific LSP tests
python3 test_lsp_integration.py

# Test with custom Terraform files
docker run -i --rm \
  -v "/path/to/test/terraform:/mnt/workspace" \
  terry-form-mcp-lsp \
  python3 test_lsp_integration.py
```

### LSP Protocol Extensions
- Add new LSP capabilities in `terraform_lsp_client.py`
- Extend MCP tools in `server_with_lsp.py`
- Update tests in `test_lsp_integration.py`
- Document new features in examples

## Future Enhancements

### Planned Features
- **Go-to-definition**: Navigate to resource definitions
- **Find references**: Locate all resource usage
- **Rename refactoring**: Safe variable/resource renaming
- **Workspace symbols**: Global symbol search
- **Diagnostic streaming**: Real-time error reporting

### Advanced Integration
- **Multi-workspace support**: Handle multiple Terraform projects
- **Provider schema caching**: Faster completion and validation
- **Custom LSP extensions**: Terry-Form specific enhancements
- **Performance optimization**: Connection pooling and caching

## Support and Resources

### Documentation
- [terraform-ls Documentation](https://github.com/hashicorp/terraform-ls)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)

### Community
- Submit issues for LSP-specific problems
- Contribute LSP enhancements via pull requests
- Share Claude Desktop usage patterns

---

**Note**: This LSP integration provides development-time intelligence features. Use the original `terry` tool for Terraform execution operations (init, plan, apply).
