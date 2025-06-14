# Terry-Form MCP Frontend

A web-based testing interface for Terry-Form MCP that runs on localhost:7575.

## Features

- **Tool Browser**: View and execute all available MCP tools
- **Workspace Explorer**: Browse files and directories in the workspace
- **Quick Actions**: One-click Terraform operations (init, validate, fmt, plan)
- **Live Results**: See execution results with syntax highlighting
- **Server Status**: Monitor connection to the MCP server

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (optional):
```bash
export MCP_SERVER_URL=http://localhost:8080  # Default
export FRONTEND_PORT=7575                    # Default
```

3. Run the frontend:
```bash
python app.py
```

4. Open http://localhost:7575 in your browser

## Usage

### Testing Tools
1. Select a tool from the left panel
2. Fill in the required parameters
3. Click "Execute Tool"
4. View results in the main panel

### Quick Actions
Use the quick action buttons for common Terraform operations:
- **Terraform Init**: Initialize a Terraform working directory
- **Terraform Validate**: Check configuration syntax
- **Terraform Format Check**: Verify code formatting
- **Terraform Plan**: Generate execution plan

### Workspace Browser
- View all files and directories in the MCP workspace
- Click "Refresh Workspace" to update the list
- Useful for verifying Terraform operations

## Connecting to MCP

The frontend expects Terry-Form MCP to be running and accessible. 

For Kubernetes deployment:
```bash
kubectl port-forward -n terry-form-system service/terry-form-mcp 8080:8000
```

For local Docker:
```bash
docker run -p 8080:8000 terry-form-mcp:latest
```

## Architecture

The frontend is a lightweight Aiohttp server that:
- Serves a single-page application with Alpine.js
- Proxies MCP protocol calls to the backend
- Provides a REST API for the web interface
- Uses Tailwind CSS for styling
- Includes Prism.js for syntax highlighting

## API Endpoints

- `GET /` - Main web interface
- `GET /api/health` - Check MCP server connection
- `GET /api/mcp/tools` - List available tools
- `POST /api/mcp/call` - Execute MCP tool
- `GET /api/workspace` - List workspace contents
- `POST /api/terraform/{action}` - Quick Terraform actions