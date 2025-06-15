# Terry-Form MCP AI Service Configuration

Terry-Form MCP includes an intelligent AI assistant powered by either Anthropic Claude or OpenAI GPT models. This enables sophisticated Terraform code analysis, generation, and optimization.

## AI Service Features

### **Code Analysis**
- **Quality Assessment**: Evaluates Terraform code quality (1-10 scale)
- **Security Review**: Identifies potential security vulnerabilities
- **Best Practices**: Suggests Terraform best practices
- **Improvement Recommendations**: Provides actionable optimization tips

### **Code Generation**
- **Infrastructure Creation**: Generate complete Terraform configurations from requirements
- **Multi-Cloud Support**: AWS, Azure, GCP infrastructure generation
- **Best Practices**: Generated code follows industry standards
- **Documentation**: Includes explanations and cost estimates

### **Resource Explanation**
- **Resource Documentation**: Explains purpose and functionality of Terraform resources
- **Configuration Options**: Details key configuration parameters
- **Use Cases**: Provides common usage scenarios
- **Security Notes**: Highlights security considerations

### **Intelligent Suggestions**
- **Performance Optimization**: Suggestions for improving infrastructure performance
- **Cost Optimization**: Recommendations for reducing cloud costs
- **Security Hardening**: Security improvement suggestions
- **Modernization**: Adoption of newer Terraform features

## Configuration

### Anthropic Claude Setup

Create a secret with your Anthropic API key:

```bash
kubectl create secret generic ai-service \
  --namespace=terry-form-system \
  --from-literal=credentials='{
    "provider": "anthropic",
    "api_key": "YOUR_ANTHROPIC_API_KEY_HERE",
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 4000,
    "temperature": 0.1
  }'
```

### OpenAI GPT Setup

Create a secret with your OpenAI API key:

```bash
kubectl create secret generic ai-service \
  --namespace=terry-form-system \
  --from-literal=credentials='{
    "provider": "openai",
    "api_key": "YOUR_OPENAI_API_KEY_HERE",
    "model": "gpt-4",
    "max_tokens": 4000,
    "temperature": 0.1
  }'
```

### Configuration Options

| Parameter | Description | Default (Anthropic) | Default (OpenAI) |
|-----------|-------------|---------------------|------------------|
| `provider` | AI service provider | `anthropic` | `openai` |
| `api_key` | API key for the service | **Required** | **Required** |
| `model` | Model to use | `claude-3-5-sonnet-20241022` | `gpt-4` |
| `max_tokens` | Maximum response tokens | `4000` | `4000` |
| `temperature` | Response creativity (0-1) | `0.1` | `0.1` |

### Available Models

**Anthropic Models:**
- `claude-3-5-sonnet-20241022` (Recommended - Best balance of capability and speed)
- `claude-3-opus-20240229` (Most capable but slower)
- `claude-3-haiku-20240307` (Fastest and most cost-effective)

**OpenAI Models:**
- `gpt-4` (Recommended - Most capable)
- `gpt-4-turbo` (Faster with good capability)
- `gpt-3.5-turbo` (Most cost-effective)

## Deployment with AI

Enable AI service in your Helm deployment:

```bash
# Create AI service secret first
kubectl create secret generic ai-service --namespace=terry-form-system --from-literal=credentials='...'

# Deploy with AI enabled
helm upgrade terry-form-mcp ./deploy/kubernetes/helm/terry-form-mcp \
  --namespace terry-form-system \
  --set terryform.ai.enabled=true \
  --values values-minikube.yaml
```

## Usage Examples

### 1. Analyze Terraform Code

```bash
# Through the frontend or API
{
  "tool": "ai_analyze_terraform",
  "arguments": {
    "code": "resource \"aws_instance\" \"web\" {\n  ami = \"ami-12345\"\n  instance_type = \"t2.micro\"\n}",
    "context": "Web server for development environment"
  }
}
```

### 2. Generate Infrastructure

```bash
{
  "tool": "ai_generate_terraform",
  "arguments": {
    "requirements": "Create a secure web application with load balancer, auto-scaling, and RDS database",
    "provider": "aws"
  }
}
```

### 3. Get Resource Explanations

```bash
{
  "tool": "ai_explain_resources",
  "arguments": {
    "resources_text": "aws_vpc\naws_subnet\naws_internet_gateway"
  }
}
```

### 4. Suggest Improvements

```bash
{
  "tool": "ai_suggest_improvements",
  "arguments": {
    "code": "resource \"aws_instance\" \"web\" {\n  ami = \"ami-12345\"\n  instance_type = \"t2.micro\"\n}",
    "goals": "Improve security and scalability"
  }
}
```

## Frontend Integration

The AI service integrates seamlessly with the Terry-Form frontend at http://localhost:7575:

1. **AI Tools**: All AI tools are available in the tools panel
2. **Code Analysis**: Analyze Terraform files directly from the workspace
3. **Generation**: Generate new infrastructure from natural language requirements
4. **Interactive**: Real-time AI assistance for Terraform development

## Best Practices

### **Prompt Engineering**
- Provide clear, specific requirements for code generation
- Include context about your infrastructure goals
- Specify security and compliance requirements

### **Code Review**
- Always review AI-generated code before deployment
- Validate configurations against your organization's standards
- Test generated code in non-production environments first

### **Cost Management**
- Use appropriate models for your use case (GPT-3.5-turbo for simple tasks, GPT-4 for complex ones)
- Set reasonable `max_tokens` limits
- Monitor API usage through your provider's dashboard

### **Security**
- Never include sensitive data (passwords, keys) in prompts
- Review AI suggestions for security implications
- Ensure generated code follows your security policies

## Monitoring

Check AI service status:

```bash
# Through the API
curl -X POST http://localhost:7575/api/mcp/call \
  -H "Content-Type: application/json" \
  -d '{"tool": "ai_status", "arguments": {}}'
```

## Troubleshooting

### Common Issues

**"AI service not configured"**
```bash
# Check if secret exists
kubectl get secret ai-service -n terry-form-system

# Verify secret format
kubectl get secret ai-service -n terry-form-system -o jsonpath='{.data.credentials}' | base64 -d
```

**API rate limits**
- Reduce `max_tokens` setting
- Implement request throttling in your workflows
- Consider upgrading your API plan

**Model errors**
- Ensure model name is correct and available
- Check API key permissions
- Verify account has access to the specified model

### Logs

Check AI service logs:
```bash
kubectl logs -n terry-form-system deployment/terry-form-mcp | grep -i "ai\|anthropic\|openai"
```

## API Costs

**Anthropic Claude Pricing** (approximate):
- Claude 3.5 Sonnet: $3/1M input tokens, $15/1M output tokens
- Claude 3 Opus: $15/1M input tokens, $75/1M output tokens  
- Claude 3 Haiku: $0.25/1M input tokens, $1.25/1M output tokens

**OpenAI Pricing** (approximate):
- GPT-4: $30/1M input tokens, $60/1M output tokens
- GPT-4 Turbo: $10/1M input tokens, $30/1M output tokens
- GPT-3.5 Turbo: $0.50/1M input tokens, $1.50/1M output tokens

*Note: Prices are subject to change. Check provider websites for current pricing.*