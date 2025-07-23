#!/usr/bin/env python3
"""
Terry-Form Web Dashboard Server - HTTP Endpoints Only
This server provides only the web dashboard and health endpoints.
For use in multi-process deployments where MCP and HTTP are separated.
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from pathlib import Path
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

class WebDashboardServer:
    """Web dashboard and health check server"""

    def __init__(self, host: str = '0.0.0.0', port: int = 8001):
        self.app = web.Application()
        self.host = host
        self.port = port
        self.setup_routes()
        self.setup_static_files()

    def setup_routes(self):
        """Setup API routes"""
        # Health and status endpoints
        self.app.router.add_get('/health', self.health)
        self.app.router.add_get('/ready', self.ready)
        self.app.router.add_get('/metrics', self.metrics)

        # Service status endpoints
        self.app.router.add_get('/api/status', self.api_status)
        self.app.router.add_get('/api/ai/status', self.ai_status)
        self.app.router.add_get('/api/auth/status', self.auth_status)
        self.app.router.add_get('/api/github/status', self.github_status)
        self.app.router.add_get('/api/terraform/version', self.terraform_version)

        # Dashboard API endpoints
        self.app.router.add_get('/api/info', self.api_info)
        self.app.router.add_get('/api/tools', self.api_tools)

    def setup_static_files(self):
        """Setup static file serving for dashboard"""
        static_path = Path(__file__).parent / 'static'
        if static_path.exists():
            self.app.router.add_static('/', static_path, name='static')
            # Serve index.html as default
            self.app.router.add_get('/', self.serve_dashboard)
        else:
            logger.warning(f"Static directory not found at {static_path}")

    async def serve_dashboard(self, request):
        """Serve the main dashboard page"""
        static_path = Path(__file__).parent / 'static' / 'index.html'
        if static_path.exists():
            return web.FileResponse(static_path)
        else:
            return web.Response(text="Dashboard not found", status=404)

    async def health(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "version": "v3.0.0",
            "service": "terry-form-web",
            "component": "dashboard"
        })

    async def ready(self, request):
        """Readiness check endpoint"""
        # Check if terraform is available
        try:
            # Security: Use shell=False for subprocess
            result = subprocess.run(
                ["terraform", "version"],
                capture_output=True,
                timeout=5,
                shell=False  # Security hardening
            )
            terraform_ready = result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to check terraform: {e}")
            terraform_ready = False

        # Check if terraform-ls is available
        try:
            result = subprocess.run(
                ["terraform-ls", "version"],
                capture_output=True,
                timeout=5,
                shell=False  # Security hardening
            )
            lsp_ready = result.returncode == 0
        except Exception:
            lsp_ready = False

        is_ready = terraform_ready

        return web.json_response({
            "status": "ready" if is_ready else "not_ready",
            "checks": {
                "terraform": terraform_ready,
                "terraform_ls": lsp_ready
            },
            "version": "v3.0.0"
        })

    async def metrics(self, request):
        """Prometheus-compatible metrics endpoint"""
        metrics = [
            '# HELP terry_form_web_up Web dashboard status',
            '# TYPE terry_form_web_up gauge',
            'terry_form_web_up 1',
            '',
            '# HELP terry_form_version_info Version information',
            '# TYPE terry_form_version_info gauge',
            'terry_form_version_info{version="3.0.0",service="web"} 1'
        ]

        return web.Response(
            text='\n'.join(metrics),
            content_type='text/plain; version=0.0.4'
        )

    async def api_status(self, request):
        """Overall API status"""
        return web.json_response({
            "status": "operational",
            "version": "v3.0.0",
            "services": {
                "web_dashboard": "running",
                "health_checks": "operational"
            },
            "endpoints": {
                "health": "/health",
                "ready": "/ready",
                "metrics": "/metrics",
                "dashboard": "/"
            }
        })

    async def ai_status(self, request):
        """AI service status endpoint"""
        try:
            from ai_service import ai_service
            return web.json_response(ai_service.get_ai_status())
        except Exception as e:
            return web.json_response({
                "error": str(e),
                "configured": False,
                "service": "ai"
            })

    async def auth_status(self, request):
        """Auth service status endpoint"""
        try:
            from auth_manager import auth_manager
            return web.json_response(auth_manager.get_auth_status())
        except Exception as e:
            return web.json_response({
                "error": str(e),
                "configured": False,
                "service": "auth"
            })

    async def github_status(self, request):
        """GitHub App status endpoint"""
        try:
            github_configured = bool(os.environ.get('GITHUB_APP_ID'))
            return web.json_response({
                "configured": github_configured,
                "app_id": os.environ.get('GITHUB_APP_ID', 'not_set'),
                "installation_configured": bool(os.environ.get('GITHUB_APP_INSTALLATION_ID')),
                "private_key_configured": bool(
                    os.environ.get('GITHUB_APP_PRIVATE_KEY') or
                    os.environ.get('GITHUB_APP_PRIVATE_KEY_PATH')
                )
            })
        except Exception as e:
            return web.json_response({
                "error": str(e),
                "configured": False,
                "service": "github"
            })

    async def terraform_version(self, request):
        """Get Terraform version information"""
        try:
            # Security: Use shell=False
            result = subprocess.run(
                ["terraform", "version", "-json"],
                capture_output=True,
                text=True,
                timeout=5,
                shell=False
            )

            if result.returncode == 0:
                version_data = json.loads(result.stdout)
                return web.json_response({
                    "installed": True,
                    "version": version_data.get("terraform_version", "unknown"),
                    "platform": version_data.get("platform", "unknown"),
                    "provider_selections": version_data.get("provider_selections", {})
                })
            else:
                return web.json_response({
                    "installed": True,
                    "error": "Failed to get version details"
                })
        except json.JSONDecodeError:
            # Fallback to simple version check
            try:
                result = subprocess.run(
                    ["terraform", "version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=False
                )

                if result.returncode == 0:
                    # Parse first line for version
                    version_line = result.stdout.strip().split('\n')[0]
                    return web.json_response({
                        "installed": True,
                        "version_string": version_line
                    })
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Failed to get terraform version: {e}")

        return web.json_response({
            "installed": False,
            "error": "Terraform not found or error occurred"
        })

    async def api_info(self, request):
        """API information endpoint"""
        return web.json_response({
            "name": "Terry-Form MCP Web Dashboard",
            "version": "v3.0.0",
            "description": "Web dashboard for Terry-Form MCP Server",
            "features": [
                "Health monitoring",
                "Service status tracking",
                "Terraform version information",
                "Integration status display"
            ],
            "github_url": "https://github.com/yourusername/terry-form-mcp"
        })

    async def api_tools(self, request):
        """List available MCP tools"""
        # This would normally query the MCP server, but since we're separate,
        # we'll return a static list of known tools
        tools = [
            {
                "name": "terry",
                "description": "Execute Terraform commands",
                "category": "terraform"
            },
            {
                "name": "terry_validate",
                "description": "Validate Terraform files",
                "category": "terraform"
            },
            {
                "name": "terry_format",
                "description": "Format Terraform files",
                "category": "terraform"
            },
            {
                "name": "terry_workspace_info",
                "description": "Get workspace information",
                "category": "workspace"
            }
        ]

        # Add GitHub tools if configured
        if os.environ.get('GITHUB_APP_ID'):
            tools.extend([
                {
                    "name": "github_clone_repo",
                    "description": "Clone or update GitHub repository",
                    "category": "github"
                },
                {
                    "name": "github_list_terraform_files",
                    "description": "List Terraform files in repository",
                    "category": "github"
                }
            ])

        return web.json_response({
            "tools": tools,
            "total": len(tools),
            "categories": list(set(tool["category"] for tool in tools))
        })

    async def start(self):
        """Start the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Web dashboard server running on http://{self.host}:{self.port}")
        logger.info(f"Dashboard available at http://{self.host}:{self.port}/")
        logger.info(f"Health endpoint: http://{self.host}:{self.port}/health")
        logger.info(f"API status: http://{self.host}:{self.port}/api/status")

        # Keep the server running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour


async def main():
    """Main entry point"""
    # Get configuration from environment
    host = os.environ.get('WEB_HOST', '0.0.0.0')
    port = int(os.environ.get('WEB_PORT', '8001'))

    # Create and start server
    server = WebDashboardServer(host=host, port=port)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
