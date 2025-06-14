#!/usr/bin/env python3
"""
Minimal Terry-Form MCP Server for testing deployment
"""
import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "version": "v3.0.0-minimal"}).encode())
        elif self.path == '/ready':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ready", "version": "v3.0.0-minimal"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress normal HTTP logs
        pass

def run_health_server(port=8000):
    """Run health check server"""
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Health server listening on port {port}")
    server.serve_forever()

def main():
    """Main entry point"""
    logger.info("Starting Terry-Form MCP v3.0.0 Minimal Server")
    
    # Start health check server in background
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Main loop - just keep running
    logger.info("Server is ready and running")
    try:
        while True:
            import time
            time.sleep(60)  # Sleep for a minute
    except KeyboardInterrupt:
        logger.info("Server shutting down")

if __name__ == "__main__":
    main()