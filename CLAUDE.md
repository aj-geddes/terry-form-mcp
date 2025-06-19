# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- `npm run build` - Build the TypeScript project (required after changes)
- `npm run watch` - Build in watch mode for development
- `npm start` - Run the built server

### Testing
- `npm run test` - Run unit tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage report
- `npm run test:integration` - Run integration tests
- `npm run test:integration:registry` - Run registry-specific integration tests
- `npm run test:all` - Run all tests and linting

### Code Quality
- `npm run lint` - Check code with ESLint
- `npm run lint:fix` - Auto-fix linting issues
- `npm run fmt` - Format code with Prettier
- `npm run fmt:check` - Check code formatting

### Manual Testing
- `./test.sh` - Run manual test scripts
- `./test-simple.sh` - Run simple test scripts
- `node test-server.js` - Run test server

## Architecture

This is a Model Context Protocol (MCP) server that provides tools for interacting with the Terraform Registry and Terraform Cloud APIs.

### Core Structure
- **Entry Point**: `index.ts` - Main server orchestrator that registers tools, resources, and prompts
- **Transport**: Uses StdioServerTransport for MCP communication
- **Tool System**: Plugin-based architecture where each tool is a self-contained module in `src/tools/`
- **Resource System**: URI-based resource handlers in `src/resources/` (e.g., `terraform:provider:hashicorp/aws`)

### Key Patterns
- **Handler Pattern**: Each tool follows `export async function handleToolName(params: InputType): Promise<ResponseContent>`
- **Zod Validation**: All tool inputs are validated using Zod schemas defined in `index.ts`
- **Error Handling**: Centralized through `src/utils/responseUtils.ts` utility functions
- **Conditional Features**: Terraform Cloud tools only registered when TFC_TOKEN is present

### API Integration
- **Terraform Registry**: Base URL from `TERRAFORM_REGISTRY_URL` env var (default: https://registry.terraform.io)
- **Terraform Cloud**: Requires `TFC_TOKEN`, uses https://app.terraform.io/api/v2
- **Algolia Search**: Used for enhanced module, provider, and policy searches

### Configuration
Environment variables are managed in `config.ts`:
- `MODE` - Server mode: `local` (default) or `enterprise`
- `LOG_LEVEL` - Logging verbosity (error, warn, info, debug)
- `REQUEST_TIMEOUT_MS` - API request timeout
- `RATE_LIMIT_*` - Rate limiting configuration
- `TFC_TOKEN` - Terraform Cloud API token (enables TFC tools in enterprise mode)
- `WEB_UI_PORT` - Port for web UI (default: 3000)
- `GITHUB_APP_ID` - GitHub App ID for repository access
- `GITHUB_APP_PRIVATE_KEY` - GitHub App private key (PEM format)
- `GITHUB_APP_INSTALLATION_ID` - Default GitHub App installation ID

### Local Development Setup
- Node.js version specified in `.nvmrc`
- MCP config locations:
  - `./.cursor/mcp.json` (local Cursor config)
  - `~/Library/Application Support/Claude/claude_desktop_config.json` (Claude Desktop)
- After changes, rebuild and manually restart the server

### Release Process
1. Ensure tests are passing
2. Update version in `config.ts` and `package.json`
3. Update `CHANGELOG.md` with customer-facing changes
4. Commit, tag, and push to GitHub
5. Create GitHub release using `gh`
6. npm and Docker releases handled automatically via GitHub Actions

### OpenWebUI Integration
Terry can be integrated with OpenWebUI using mcpo (MCP-to-OpenAPI proxy):

#### Quick Setup
```bash
# Run Terry through mcpo for OpenWebUI
uvx mcpo --port 8000 --api-key "secure-key" -- npx terraform-mcp-server
```

#### Key Points
- OpenWebUI v0.6+ supports MCP servers via OpenAPI
- mcpo converts Terry's stdio-based tools to REST endpoints
- All Terry tools become available as functions in OpenWebUI
- Requires models with native function calling (e.g., GPT-4o)

#### Admin Setup in OpenWebUI
1. Go to Admin Settings → Tools
2. Add Tool Server URL: `http://mcpo-server:8000`
3. Add authentication header: `X-API-Key: your-key`
4. Enable for users/models that need Terraform assistance

See `docs/OPENWEBUI_INTEGRATION.md` for complete setup guide.