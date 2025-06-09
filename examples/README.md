# Terry-Form MCP Examples

This directory contains practical examples of using Terry-Form MCP with different AI assistants and Terraform configurations.

## Claude Desktop Integration

### Configuration File Example

Add this to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "C:\\Users\\YourUsername\\terraform-projects:/mnt/workspace",
        "terry-form-mcp"
      ]
    }
  }
}
```

### Usage in Claude

Once configured, you can ask Claude to help with Terraform operations:

```
"Please validate my Terraform configuration in the aws-infrastructure folder"

"Can you run a plan on my development environment with environment=dev and region=us-west-2?"

"Check the formatting of all Terraform files in my modules directory"
```

## Command Line Examples

### Basic Validation

```bash
# Validate a Terraform configuration
echo '{
  "actions": ["validate"],
  "path": "infrastructure/aws"
}' | docker run -i --rm \
  -v "$(pwd):/mnt/workspace" \
  terry-form-mcp python3 terry-form-mcp.py
```

### Full Workflow

```bash
# Run complete workflow: init, validate, format check, and plan
echo '{
  "actions": ["init", "validate", "fmt", "plan"],
  "path": "environments/production",
  "vars": {
    "environment": "prod",
    "instance_count": "3",
    "region": "us-east-1"
  }
}' | docker run -i --rm \
  -v "$(pwd):/mnt/workspace" \
  terry-form-mcp python3 terry-form-mcp.py
```

### Planning with Variables

```bash
# Generate execution plan with custom variables
echo '{
  "actions": ["plan"],
  "path": "modules/vpc",
  "vars": {
    "vpc_cidr": "10.0.0.0/16",
    "availability_zones": "2",
    "enable_nat_gateway": "true",
    "environment": "staging"
  }
}' | docker run -i --rm \
  -v "$(pwd):/mnt/workspace" \
  terry-form-mcp python3 terry-form-mcp.py
```

## Sample Terraform Project Structure

```
terraform-projects/
├── environments/
│   ├── development/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars.example
│   ├── staging/
│   └── production/
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/
│   └── storage/
└── shared/
    ├── providers.tf
    └── versions.tf
```

## AI Assistant Prompts

### For Infrastructure Review

```
"I have a new Terraform configuration in my aws-vpc module. Can you:
1. Check if it's properly formatted
2. Validate the syntax
3. Generate a plan to see what resources would be created
4. Review the plan for any potential issues"
```

### For Development Workflow

```
"I'm working on environment configurations. Please:
1. Validate the development environment config
2. Run a plan with development variables
3. Compare it with the staging environment plan
4. Suggest any improvements"
```

### For Module Development

```
"I'm creating a new Terraform module. Can you:
1. Validate all the .tf files in the modules/database directory
2. Check the formatting
3. Run a test plan with sample variables to ensure it works"
```

## Environment-Specific Examples

### Development Environment

```json
{
  "actions": ["init", "validate", "plan"],
  "path": "environments/development",
  "vars": {
    "environment": "dev",
    "instance_type": "t3.micro",
    "min_capacity": "1",
    "max_capacity": "2",
    "enable_monitoring": "false"
  }
}
```

### Production Environment

```json
{
  "actions": ["validate", "plan"],
  "path": "environments/production",
  "vars": {
    "environment": "prod",
    "instance_type": "c5.large",
    "min_capacity": "3",
    "max_capacity": "10",
    "enable_monitoring": "true",
    "backup_retention": "30"
  }
}
```

## Batch Processing Script

Create a script to test multiple environments:

```bash
#!/bin/bash
# test-all-environments.sh

environments=("development" "staging" "production")

for env in "${environments[@]}"; do
    echo "Testing $env environment..."
    echo "{
        \"actions\": [\"validate\", \"plan\"],
        \"path\": \"environments/$env\",
        \"vars\": {
            \"environment\": \"$env\"
        }
    }" | docker run -i --rm \
        -v "$(pwd):/mnt/workspace" \
        terry-form-mcp python3 terry-form-mcp.py
    echo "---"
done
```

## Error Handling Examples

### Common Error Patterns

1. **Path not found**:
   ```json
   {
     "success": false,
     "action": "validate",
     "error": "Resolved path does not exist: /mnt/workspace/nonexistent"
   }
   ```

2. **Terraform not initialized**:
   ```json
   {
     "success": false,
     "action": "validate", 
     "stderr": "Error: Could not load plugin",
     "returncode": 1
   }
   ```

3. **Invalid configuration**:
   ```json
   {
     "success": false,
     "action": "validate",
     "stderr": "Error: Invalid resource name",
     "returncode": 1
   }
   ```

## Best Practices

1. **Always run init first** for new configurations
2. **Validate before planning** to catch syntax errors early
3. **Use meaningful variable names** for clarity
4. **Test with development values** before production
5. **Review plans carefully** before any actual infrastructure changes

## Integration with CI/CD

While Terry-Form MCP is designed for local development, you can use it in CI/CD for validation:

```yaml
# GitHub Actions example
- name: Validate Terraform
  run: |
    echo '{
      "actions": ["init", "validate", "fmt"],
      "path": "infrastructure"
    }' | docker run -i --rm \
      -v "${{ github.workspace }}:/mnt/workspace" \
      terry-form-mcp python3 terry-form-mcp.py
```

Remember: Terry-Form MCP is for validation and planning only. Use proper Terraform workflows for applying changes to infrastructure.