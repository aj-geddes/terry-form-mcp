# Contributing to Terry-Form MCP

We welcome contributions to the Terry-Form MCP project! This guide will help you get started.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find that the issue has already been reported. When you create a bug report, please include:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** of configurations or commands
- **Describe the behavior you observed** and what behavior you expected
- **Include logs and error messages**
- **Specify your environment** (Docker version, OS, etc.)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the coding standards below
3. **Add tests** for any new functionality
4. **Update documentation** if needed
5. **Ensure tests pass** and code follows style guidelines
6. **Submit a pull request** with a clear description

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.8 or higher
- Git

### Local Development

1. Clone your fork:
   ```bash
   git clone https://github.com/your-username/terry-form-mcp.git
   cd terry-form-mcp
   ```

2. Install development dependencies:
   ```bash
   pip install fastmcp pytest black flake8
   ```

3. Build the Docker image:
   ```bash
   docker build -t terry-form-mcp-dev .
   ```

4. Run tests:
   ```bash
   python -m pytest tests/
   ```

### Testing

#### Unit Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=terry-form-mcp
```

#### Integration Tests
```bash
# Test Docker integration
docker build -t terry-form-mcp-test .
echo '{"actions":["validate"],"path":"test-fixtures/basic"}' | \
  docker run -i --rm -v "$(pwd):/mnt/workspace" terry-form-mcp-test python3 terry-form-mcp.py
```

#### Manual Testing
```bash
# Test FastMCP server
python3 server.py

# Test core functionality
python3 terry-form-mcp.py < test.json
```

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Maximum line length: 88 characters (Black default)

### Code Formatting

Before submitting, run:
```bash
# Format code
black .

# Check linting
flake8 .

# Type checking (if using mypy)
mypy *.py
```

### Documentation Standards

- Use clear, descriptive function and variable names
- Add docstrings for all public functions and classes
- Update README.md for user-facing changes
- Update CHANGELOG.md following Keep a Changelog format

### Commit Message Guidelines

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests when applicable

Examples:
```
feat: add support for terraform apply command
fix: resolve path validation issue on Windows
docs: update configuration examples
test: add integration tests for variable injection
```

## Project Structure

```
terry-form-mcp/
├── server.py              # FastMCP server implementation
├── terry-form-mcp.py      # Core Terraform execution logic
├── Dockerfile             # Container build configuration
├── test.json              # Sample test input
├── tests/                 # Test suite
│   ├── test_server.py     # Server tests
│   ├── test_core.py       # Core logic tests
│   └── fixtures/          # Test fixtures
├── docs/                  # Additional documentation
├── examples/              # Usage examples
├── README.md              # Main documentation
├── CHANGELOG.md           # Version history
├── CONTRIBUTING.md        # This file
├── LICENSE                # MIT License
└── .gitignore             # Git ignore patterns
```

## Security Considerations

When contributing to Terry-Form MCP, please consider:

### Security Best Practices
- **No sensitive data** in code or tests
- **Validate all inputs** from external sources
- **Use secure defaults** for configurations
- **Document security implications** of changes

### Container Security
- Keep base image updated
- Minimize attack surface
- Use non-root users when possible
- Validate mounted paths

### Terraform Security
- Never implement `apply` or `destroy` operations
- Validate workspace paths thoroughly
- Sanitize variable inputs
- Prevent state file access

## Release Process

1. **Update version** in relevant files
2. **Update CHANGELOG.md** with new version
3. **Create release PR** with version bump
4. **Tag release** after merge
5. **Build and push** Docker images
6. **Create GitHub release** with changelog

## Questions and Support

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Security**: Email security issues privately to maintainers

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- README.md contributors section
- GitHub releases notes

Thank you for contributing to Terry-Form MCP!