#!/usr/bin/env python3
"""
Terry-Form MCP Combined Server
Runs MCP on port 8000 and health checks on port 8001
"""
import os
import sys
import asyncio
import logging
import subprocess
import threading
from pathlib import Path
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Health check server
async def health(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "version": "v3.0.0-http",
        "service": "terry-form-mcp"
    })

async def ready(request):
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
    
    return web.json_response({
        "status": "ready" if terraform_ready else "not_ready",
        "terraform": terraform_ready,
        "version": "v3.0.0-http"
    })

def run_health_server():
    """Run health check server on port 8001"""
    app = web.Application()
    app.router.add_get('/health', health)
    app.router.add_get('/ready', ready)
    
    # Run in thread's event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    
    site = web.TCPSite(runner, '0.0.0.0', 8001)
    loop.run_until_complete(site.start())
    
    logger.info("Health check server running on port 8001")
    
    # Keep running
    loop.run_forever()

def run_frontend_server():
    """Run frontend server on port 7575"""
    try:
        # Set environment variables for frontend
        os.environ["MCP_SERVER_URL"] = "http://localhost:8000"
        os.environ["FRONTEND_PORT"] = "7575"
        
        # Add frontend directory to path
        frontend_dir = Path(__file__).parent / "frontend"
        if frontend_dir.exists():
            sys.path.insert(0, str(frontend_dir))
            
            # Import and run frontend
            import app
            app.main()
        else:
            logger.warning("Frontend directory not found, skipping frontend server")
    except Exception as e:
        logger.error(f"Frontend server error: {e}")

def main():
    """Main entry point"""
    try:
        logger.info("Starting Terry-Form MCP Combined Server")
        
        # Start health server in background thread
        health_thread = threading.Thread(target=run_health_server, daemon=True)
        health_thread.start()
        
        # Start frontend server in background thread
        frontend_thread = threading.Thread(target=run_frontend_server, daemon=True)
        frontend_thread.start()
        
        # Give threads time to start
        import time
        time.sleep(2)
        
        # Import and run MCP server (this blocks)
        from server_http_fixed import main as mcp_main
        mcp_main()
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()