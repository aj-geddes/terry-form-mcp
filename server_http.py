#!/usr/bin/env python3
"""
Terry-Form MCP Server with HTTP Transport
Uses FastMCP's streamable-http transport for Kubernetes deployment
"""
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the existing server
from server_enhanced_with_lsp import mcp, terraform_lsp_client
import atexit
import asyncio
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for HTTP server"""
    try:
        
        # Set up cleanup handlers
        def cleanup():
            logger.info("Cleaning up LSP client...")
            if terraform_lsp_client._lsp_client:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(terraform_lsp_client._lsp_client.shutdown())
                loop.close()
        
        atexit.register(cleanup)
        signal.signal(signal.SIGTERM, lambda s, f: cleanup())
        
        # Get configuration from environment
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        
        logger.info(f"Starting Terry-Form MCP HTTP Server on {host}:{port}")
        
        # Start MCP server with streamable-http transport
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port
        )
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        # Cleanup on Ctrl+C
        if terraform_lsp_client._lsp_client:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(terraform_lsp_client._lsp_client.shutdown())
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()