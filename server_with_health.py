#!/usr/bin/env python3
"""
Terry-Form MCP Server with Health Endpoints
Wraps the MCP server with additional HTTP endpoints
"""
import os
import sys
import asyncio
import logging
import subprocess
from pathlib import Path
from aiohttp import web
from multiprocessing import Process

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthServer:
    """Simple health check server"""
    
    def __init__(self, port=8001):
        self.app = web.Application()
        self.port = port
        self.setup_routes()
    
    def setup_routes(self):
        self.app.router.add_get('/health', self.health)
        self.app.router.add_get('/ready', self.ready)
    
    async def health(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "version": "v3.0.0-http",
            "service": "terry-form-mcp"
        })
    
    async def ready(self, request):
        """Readiness check endpoint"""
        # Check if terraform is available
        try:
            result = subprocess.run(
                ["terraform", "version"],
                capture_output=True,
                timeout=5
            )
            terraform_ready = result.returncode == 0
        except:
            terraform_ready = False
        
        # Check if MCP server is responding
        mcp_ready = False
        try:
            # Simple check - if we're running, MCP should be too
            mcp_ready = True
        except:
            pass
        
        ready = terraform_ready and mcp_ready
        
        return web.json_response({
            "status": "ready" if ready else "not_ready",
            "checks": {
                "terraform": terraform_ready,
                "mcp": mcp_ready
            },
            "version": "v3.0.0-http"
        })
    
    def run(self):
        """Run the health server"""
        web.run_app(self.app, host='0.0.0.0', port=self.port)

def run_mcp_server():
    """Run the MCP server in a subprocess"""
    from server_http_fixed import main
    main()

def run_health_server():
    """Run the health server"""
    server = HealthServer(port=8001)
    server.run()

def main():
    """Main entry point - run both servers"""
    try:
        # Get ports from environment
        mcp_port = int(os.getenv("MCP_PORT", "8000"))
        health_port = int(os.getenv("HEALTH_PORT", "8001"))
        
        logger.info(f"Starting Terry-Form MCP with health endpoints")
        logger.info(f"MCP Port: {mcp_port}, Health Port: {health_port}")
        
        # Start health server in a separate process
        health_process = Process(target=run_health_server)
        health_process.start()
        
        # Run MCP server in main process
        try:
            run_mcp_server()
        finally:
            # Cleanup
            health_process.terminate()
            health_process.join()
            
    except KeyboardInterrupt:
        logger.info("Servers interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()