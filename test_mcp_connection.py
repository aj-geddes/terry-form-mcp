#!/usr/bin/env python3
"""
Test MCP connection and list tools
"""
import asyncio
import sys
sys.path.append('frontend')

from mcp_client import MCPClient

async def test_connection():
    print("Testing MCP Connection...")
    print("-" * 40)
    
    client = MCPClient("http://localhost:8080")
    
    # Initialize
    print("1. Initializing MCP session...")
    initialized = await client.initialize()
    print(f"   Initialized: {initialized}")
    print(f"   Session ID: {client.session_id}")
    
    if not initialized:
        print("   Failed to initialize!")
        return
    
    # List tools
    print("\n2. Listing tools...")
    result = await client.list_tools()
    
    if "result" in result:
        tools = result["result"].get("tools", [])
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool.get('description', 'No description')[:60]}...")
    else:
        print(f"   Error: {result}")
    
    # Test workspace_list
    print("\n3. Testing workspace_list tool...")
    result = await client.call_tool("workspace_list", {})
    
    if "result" in result:
        print("   Success! Response received")
    else:
        print(f"   Error: {result}")

if __name__ == "__main__":
    asyncio.run(test_connection())