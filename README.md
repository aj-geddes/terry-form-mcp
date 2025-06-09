# Terry-Form MCP

A Model Control Protocol (MCP) server that enables AI assistants to execute Terraform commands locally through a secure, containerized environment using HashiCorp's official Terraform Docker image.

## What is Terry-Form?

Terry-Form MCP is a bridge between AI language models and Terraform infrastructure management. It provides a safe, controlled way for AI assistants like Claude to:

- Execute Terraform commands (`init`, `validate`, `fmt`, `plan`)
- Run operations in isolated Docker containers
- Work with Terraform configurations in your local workspace
- Pass variables dynamically to Terraform operations
- Return structured JSON results for AI processing

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Assistant  │────│  Terry-Form MCP │────│ Terraform Docker│
│     (Claude)    │    │     Server      │    │   Container     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              │
                       ┌─────────────────┐
                       │  Local Terraform│
                       │  Configurations │
                       └─────────────────┘
```

### Components

- **server.py**: FastMCP-based server that exposes the `terry` tool
- **terry-form-mcp.py**: Core Terraform execution logic and subprocess handling
- **Dockerfile**: HashiCorp Terraform image with Python and FastMCP integration
- **Docker Container**: Isolated execution environment with Terraform pre-installed

## Features

### Supported Terraform Actions
- `init` - Initialize Terraform working directory
- `validate` - Validate Terraform configuration syntax
- `fmt` - Check Terraform code formatting
- `plan` - Generate and show execution plan (with variable support)

### Security Features
- **Containerized Execution**: All Terraform commands run in isolated Docker containers
- **Workspace Isolation**: Operations restricted to `/mnt/workspace` mount point
- **No State Modification**: Only read-only operations (plan, validate, fmt)
- **Variable Injection**: Safe parameter passing for dynamic configurations

### AI Integration
- **Structured Output**: JSON-formatted results for AI processing
- **Error Handling**: Detailed error messages and return codes
- **Batch Operations**: Execute multiple Terraform actions in sequence
- **FastMCP Integration**: Standard MCP protocol for AI assistant compatibility

## Quick Start

### Prerequisites

- Docker installed and running
- Python 3.8+ (for development/testing)
- Access to Terraform configurations in your workspace

### 1. Build the Docker Image

```bash
docker build -t terry-form-mcp .
```

### 2. Run as MCP Server

```bash
docker run -it --rm \
  -v "$(pwd)":/mnt/workspace \
  terry-form-mcp
```

### 3. Test with Sample Data

Create a test configuration:
```bash
echo '{
  "actions": ["init", "validate", "plan"],
  "path": "my-terraform-project",
  "vars": {
    "environment": "dev",
    "region": "us-west-2"
  }
}' | docker run -i --rm \
  -v "$(pwd)":/mnt/workspace \
  terry-form-mcp python3 terry-form-mcp.py
```

## Configuration

### MCP Tool Configuration

When integrating with AI assistants, configure the `terry` tool:

```json
{
  "name": "terry",
  "description": "Runs terraform actions in /mnt/workspace/<path> using provided variables.",
  "parameters": {
    "path": {
      "type": "string",
      "description": "Relative path to Terraform configuration from workspace root"
    },
    "actions": {
      "type": "array",
      "items": {"type": "string"},
      "default": ["plan"],
      "description": "Terraform actions to execute: init, validate, fmt, plan"
    },
    "vars": {
      "type": "object",
      "description": "Key-value pairs for Terraform variables (only used with plan)"
    }
  }
}
```

### Claude Desktop MCP Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/workspace:/mnt/workspace",
        "terry-form-mcp"
      ]
    }
  }
}
```

## Usage Examples

### Basic Terraform Validation

```python
# Through MCP tool call
terry(
    path="infrastructure/aws",
    actions=["init", "validate"]
)
```

### Infrastructure Planning with Variables

```python
# Through MCP tool call
terry(
    path="environments/production",
    actions=["plan"],
    vars={
        "instance_count": "3",
        "environment": "prod",
        "region": "us-east-1"
    }
)
```

### Multi-Action Workflow

```python
# Through MCP tool call
terry(
    path="modules/vpc",
    actions=["fmt", "validate", "plan"],
    vars={
        "vpc_cidr": "10.0.0.0/16",
        "availability_zones": "3"
    }
)
```

## Output Format

Terry-Form returns structured JSON responses:

```json
{
  "terry-results": [
    {
      "success": true,
      "action": "plan",
      "stdout": "Terraform will perform the following actions...",
      "stderr": "",
      "returncode": 0
    }
  ]
}
```

### Response Fields

- `success`: Boolean indicating command success
- `action`: The Terraform action that was executed
- `stdout`: Standard output from Terraform command
- `stderr`: Standard error output (if any)
- `returncode`: Process exit code
- `error`: Error message (if exception occurred)

## Development

### Local Development Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install fastmcp
   ```
3. Run the server locally:
   ```bash
   python3 server.py
   ```

### Testing

Test the core functionality:
```bash
python3 terry-form-mcp.py < test.json
```

Test with Docker:
```bash
docker build -t terry-form-mcp-test .
docker run -i --rm \
  -v "$(pwd):/mnt/workspace" \
  terry-form-mcp-test \
  python3 terry-form-mcp.py < test.json
```

### Project Structure

```
terry-form-mcp/
├── server.py              # FastMCP server implementation
├── terry-form-mcp.py      # Core Terraform execution logic
├── Dockerfile             # Container build configuration
├── test.json              # Sample test input
├── README.md              # This documentation
├── LICENSE                # MIT License
└── .gitignore             # Git ignore patterns
```

## Security Considerations

### Safe Operations Only
- **No Apply/Destroy**: Only read-only operations are supported
- **No State Access**: Cannot modify Terraform state files
- **Container Isolation**: All execution happens in ephemeral containers

### Best Practices
- Always validate configurations before planning
- Use specific variable values rather than sensitive defaults
- Monitor container resource usage in production
- Regularly update the HashiCorp Terraform base image

## Limitations

- **Read-Only Operations**: Cannot execute `apply` or `destroy` commands
- **No State Management**: Cannot access or modify Terraform state
- **Local Execution Only**: Designed for local development workflows
- **Variable Types**: Only string variables are supported via command line

## Troubleshooting

### Common Issues

1. **Path Not Found**
   ```
   Error: Resolved path does not exist: /mnt/workspace/my-project
   ```
   - Ensure the path exists relative to your workspace root
   - Check Docker volume mount configuration

2. **Terraform Init Required**
   ```
   Error: Terraform configuration error
   ```
   - Run `init` action before `validate` or `plan`
   - Ensure provider configurations are correct

3. **Docker Permission Issues**
   ```
   Error: Permission denied
   ```
   - Check Docker volume mount permissions
   - Ensure workspace directory is accessible

### Debug Mode

Enable verbose output by modifying the Docker run command:
```bash
docker run -it --rm \
  -v "$(pwd)":/mnt/workspace \
  -e TF_LOG=DEBUG \
  terry-form-mcp
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Development Guidelines

- Follow Python PEP 8 style guidelines
- Add docstrings for all functions
- Include error handling for edge cases
- Update documentation for new features

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Changelog

### v1.0.0
- Initial release with basic Terraform operations
- FastMCP integration
- Docker containerization
- Support for init, validate, fmt, and plan actions

## Support

For issues, questions, or contributions:
- Create an issue in the GitHub repository
- Follow the contributing guidelines
- Check existing issues for similar problems

---

**Note**: This tool is designed for development and testing workflows. For production Terraform operations, use proper CI/CD pipelines with appropriate security controls and state management.