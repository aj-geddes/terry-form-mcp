# Terry MCP Server - Developer Documentation

## Architecture Overview

Terry (Terraform Registry MCP Server) is a Model Context Protocol server that provides AI assistants with access to Terraform Registry and Terraform Cloud APIs. The server operates in two distinct modes:

### Dual-Mode Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Terry MCP Server                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐           ┌─────────────────┐         │
│  │   Local Mode    │           │ Enterprise Mode  │         │
│  │                 │           │                  │         │
│  │ • Registry Only │           │ • Registry + TFC │         │
│  │ • No Auth       │           │ • TFC Token Auth │         │
│  │ • Lightweight   │           │ • K8s Ready      │         │
│  │ • Docker/NPX    │           │ • MCP Bridge     │         │
│  └─────────────────┘           └─────────────────┘         │
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │              Core Components                      │       │
│  │                                                   │       │
│  │  • MCP SDK Integration (stdio transport)         │       │
│  │  • Tool System (25+ tools)                       │       │
│  │  • Resource System (URI-based)                   │       │
│  │  • Web UI (Express server)                       │       │
│  │  • Mode Manager                                  │       │
│  └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Code Structure

```
terraform-mcp-server/
├── src/
│   ├── tools/           # Individual tool implementations
│   ├── resources/       # Resource handlers
│   ├── prompts/         # Pre-configured prompts
│   ├── modes/           # Mode configuration and detection
│   ├── ui/              # Web UI server
│   ├── utils/           # Shared utilities
│   └── types/           # TypeScript type definitions
├── k8s/                 # Kubernetes manifests
├── charts/terry/        # Helm chart
├── index.ts             # Main entry point
├── config.ts            # Configuration management
└── Dockerfile           # Container build
```

## Key Design Patterns

### 1. Mode-Based Feature Toggling

```typescript
// src/modes/index.ts
export function getModeConfig(): ModeConfig {
  switch (SERVER_MODE) {
    case MODES.ENTERPRISE:
      return {
        mode: MODES.ENTERPRISE,
        features: {
          terraformCloud: true,
          webUI: true,
          mcpBridge: true
        },
        // ...
      };
    case MODES.LOCAL:
    default:
      return {
        mode: MODES.LOCAL,
        features: {
          terraformCloud: false,
          webUI: true,
          mcpBridge: false
        },
        // ...
      };
  }
}
```

### 2. Conditional Tool Registration

```typescript
// index.ts
if (shouldEnableTerraformCloud() && TFC_TOKEN) {
  server.tool("listOrganizations", schema, handler);
  // ... other TFC tools
}
```

### 3. Handler Pattern

All tools follow a consistent async handler pattern:

```typescript
export async function handleToolName(
  params: ToolInputType
): Promise<ResponseContent> {
  try {
    // Implementation
    return createSuccessResponse(data);
  } catch (error) {
    return handleToolError(error, "Tool context");
  }
}
```

### 4. Resource URI System

Resources use a hierarchical URI pattern:

```
terraform:provider:<namespace>/<name>
terraform:resource:<namespace>/<name>/<resource>
terraform:organizations
terraform:workspace:<org>/<workspace>
```

## Building and Testing

### Local Development

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Run tests
npm run test
npm run test:integration

# Run linting
npm run lint:fix

# Start development
npm run watch  # In one terminal
npm start      # In another terminal
```

### Docker Build

```bash
# Build image
docker build -t terraform-mcp-server:latest .

# Run local mode
docker run -p 3000:3000 -e MODE=local terraform-mcp-server:latest

# Run enterprise mode
docker run -p 3000:3000 \
  -e MODE=enterprise \
  -e TFC_TOKEN=your-token \
  terraform-mcp-server:latest
```

### Testing Modes

```bash
# Test local mode
MODE=local npm start

# Test enterprise mode
MODE=enterprise TFC_TOKEN=your-token npm start

# Check mode via API
curl http://localhost:3000/api/status
```

## Environment Variables

| Variable | Description | Default | Modes |
|----------|-------------|---------|-------|
| `MODE` | Server mode | `local` | Both |
| `TFC_TOKEN` | Terraform Cloud API token | - | Enterprise |
| `WEB_UI_PORT` | Web UI port | `3000` | Both |
| `LOG_LEVEL` | Logging level | `info` | Both |
| `REQUEST_TIMEOUT_MS` | API timeout | `10000` | Both |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `false` | Both |

## Adding New Features

### Adding a New Tool

1. Create tool handler in `src/tools/yourTool.ts`:
```typescript
export async function handleYourTool(params: YourParams): Promise<ResponseContent> {
  // Implementation
}
```

2. Add Zod schema in `index.ts`:
```typescript
const YourToolShape = {
  param1: z.string().describe("Description"),
  // ...
};
```

3. Register the tool:
```typescript
server.tool("yourTool", YourToolShape, async (args) => {
  const result = await handleYourTool(args);
  return {
    ...result,
    content: result.content.map((c) => ({ type: "text", text: c.text }))
  };
});
```

### Mode-Specific Features

Check mode before registering features:

```typescript
if (shouldEnableTerraformCloud()) {
  // Enterprise-only features
}

if (isLocalMode()) {
  // Local-only features
}
```

## Debugging

### Enable Debug Logging

```bash
LOG_LEVEL=debug npm start
```

### Common Issues

1. **Tool Registration**: Ensure Zod schemas match handler expectations
2. **Mode Detection**: Check `SERVER_MODE` environment variable
3. **TFC Tools**: Verify `TFC_TOKEN` is set in enterprise mode
4. **Web UI**: Check port availability (default 3000)

## Performance Considerations

- Tools use concurrent API calls where possible
- Rate limiting can be enabled via environment variables
- Resource handlers implement caching for repeated requests
- Web UI auto-refreshes status every 30 seconds

## Security

- TFC tokens are never logged or exposed
- Environment-based configuration for sensitive data
- Input validation via Zod schemas
- Error messages sanitized to avoid leaking internal details

## Release Process

1. Update version in `package.json` and `config.ts`
2. Update `CHANGELOG.md`
3. Run full test suite: `npm run test:all`
4. Build and test Docker image
5. Tag release: `git tag v0.x.x`
6. Push to GitHub (CI handles npm/Docker publishing)

## Contributing

1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure linting passes: `npm run lint`
4. Update documentation
5. Submit PR with clear description

## Troubleshooting Development

### TypeScript Errors

```bash
# Clean and rebuild
rm -rf dist/
npm run build
```

### Test Failures

```bash
# Run specific test
npm test -- --testNamePattern="your test"

# Debug test
NODE_OPTIONS='--inspect-brk' npm test
```

### MCP Connection Issues

Check stdio transport is working:
```bash
echo '{"method": "initialize"}' | npm start
```