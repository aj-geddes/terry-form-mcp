"""
MCP Client helper for the frontend
Handles session management and SSE communication
"""
import json
import uuid
import asyncio
from typing import Dict, Any, Optional
import aiohttp
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session_id = None
        self.initialized = False
        
    async def initialize(self) -> bool:
        """Initialize MCP session"""
        try:
            # Create a new session
            self.session_id = str(uuid.uuid4())
            
            # Send initialize request
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Session-ID": self.session_id
            }
            
            payload = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "Terry-Form Web Frontend",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/mcp/sse",
                    json=payload,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        # Read SSE response
                        result = await self._read_sse_response(resp)
                        if result and "result" in result:
                            self.initialized = True
                            return True
                            
            return False
        except Exception as e:
            logger.error(f"Failed to initialize MCP: {e}")
            return False
    
    async def _read_sse_response(self, response) -> Optional[Dict[str, Any]]:
        """Read SSE formatted response"""
        try:
            text = await response.text()
            # SSE format: data: {json}\n\n
            for line in text.strip().split('\n'):
                if line.startswith('data: '):
                    json_str = line[6:]  # Remove 'data: ' prefix
                    return json.loads(json_str)
            return None
        except Exception as e:
            logger.error(f"Failed to parse SSE response: {e}")
            return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": int(asyncio.get_event_loop().time() * 1000)
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/mcp/sse",
                    json=payload,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        result = await self._read_sse_response(resp)
                        return result or {"error": "No response data"}
                    else:
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        # Try without initialization first
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": int(asyncio.get_event_loop().time() * 1000)
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/mcp/sse",
                    json=payload,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        result = await self._read_sse_response(resp)
                        return result or {"error": "No response data"}
                    else:
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"error": str(e)}