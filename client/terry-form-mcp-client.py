#!/usr/bin/env python3
"""
Terry-Form MCP Client for stdio transport
This client connects to Terry-Form MCP running in Kubernetes
"""
import sys
import json
import subprocess
import threading
import queue
import time
import requests
from typing import Dict, Any

class TerryFormMCPClient:
    def __init__(self, namespace="terry-form-system", service="terry-form-mcp", 
                 local_port=8080, remote_port=8000):
        self.namespace = namespace
        self.service = service
        self.local_port = local_port
        self.remote_port = remote_port
        self.base_url = f"http://localhost:{local_port}"
        self.port_forward_process = None
        
    def start_port_forward(self):
        """Start kubectl port-forward in background"""
        cmd = [
            "kubectl", "port-forward",
            "-n", self.namespace,
            f"service/{self.service}",
            f"{self.local_port}:{self.remote_port}"
        ]
        
        self.port_forward_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for port forward to be ready
        time.sleep(3)
        
        # Test connection
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                raise Exception("Health check failed")
        except Exception as e:
            self.stop_port_forward()
            raise Exception(f"Failed to connect to Terry-Form MCP: {e}")
    
    def stop_port_forward(self):
        """Stop kubectl port-forward"""
        if self.port_forward_process:
            self.port_forward_process.terminate()
            self.port_forward_process.wait()
    
    def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send MCP request and get response"""
        try:
            response = requests.post(
                f"{self.base_url}/mcp",
                json=request,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": request.get("id")
            }
    
    def run_stdio_transport(self):
        """Run stdio transport for MCP"""
        try:
            # Start port forward
            self.start_port_forward()
            
            # Send initialization
            init_response = {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "Terry-Form MCP",
                        "version": "3.0.0"
                    }
                },
                "id": 0
            }
            print(json.dumps(init_response), flush=True)
            
            # Main loop - read from stdin, forward to HTTP, write to stdout
            for line in sys.stdin:
                try:
                    request = json.loads(line.strip())
                    
                    # Handle special methods locally
                    if request.get("method") == "initialize":
                        response = {
                            "jsonrpc": "2.0",
                            "result": {
                                "protocolVersion": "0.1.0",
                                "capabilities": {
                                    "tools": {
                                        "listChanged": True
                                    }
                                },
                                "serverInfo": {
                                    "name": "Terry-Form MCP",
                                    "version": "3.0.0"
                                }
                            },
                            "id": request.get("id")
                        }
                    else:
                        # Forward to HTTP endpoint
                        response = self.send_request(request)
                    
                    # Send response
                    print(json.dumps(response), flush=True)
                    
                except json.JSONDecodeError:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        },
                        "id": None
                    }
                    print(json.dumps(error_response), flush=True)
                except Exception as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        },
                        "id": None
                    }
                    print(json.dumps(error_response), flush=True)
        
        finally:
            self.stop_port_forward()

def main():
    """Main entry point"""
    # Check if kubectl is available
    try:
        subprocess.run(["kubectl", "version", "--client"], 
                      capture_output=True, check=True)
    except:
        print(json.dumps({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "kubectl not found. Please install kubectl."
            },
            "id": None
        }), flush=True)
        sys.exit(1)
    
    # Create and run client
    client = TerryFormMCPClient()
    client.run_stdio_transport()

if __name__ == "__main__":
    main()