#!/usr/bin/env python3
"""
Test direct tool call to understand the protocol
"""
import requests
import json
import time

# Step 1: Get fresh session
print("1. Getting new session...")
resp = requests.get("http://localhost:8080/mcp/", headers={"Accept": "text/event-stream"})
session_id = resp.headers.get("mcp-session-id")
print(f"   Session ID: {session_id}")

# Step 2: Initialize
print("\n2. Initializing...")
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Session-ID": session_id
}

init_payload = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "0.1.0",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    },
    "id": 1
}

resp = requests.post("http://localhost:8080/mcp/sse", json=init_payload, headers=headers)
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text[:200]}")

# Step 3: Try different method names for tools
methods_to_try = [
    ("tools/list", None),
    ("tools/list", {}),
    ("mcp/list_tools", None),
    ("list_tools", None),
    ("tool.list", None),
]

print("\n3. Trying different method names...")
for method, params in methods_to_try:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": int(time.time() * 1000)
    }
    if params is not None:
        payload["params"] = params
        
    resp = requests.post("http://localhost:8080/mcp/sse", json=payload, headers=headers)
    print(f"\n   Method: {method}")
    print(f"   Status: {resp.status_code}")
    
    # Parse SSE response
    for line in resp.text.strip().split('\n'):
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if "result" in data:
                print(f"   SUCCESS! Result keys: {list(data['result'].keys())}")
                if "tools" in data["result"]:
                    print(f"   Found {len(data['result']['tools'])} tools")
                    for tool in data["result"]["tools"][:3]:
                        print(f"     - {tool['name']}")
                break
            elif "error" in data:
                print(f"   Error: {data['error']['message']}")

# Step 4: If we found tools, try calling one
print("\n4. Trying to call workspace_list tool...")
call_methods = [
    ("tools/call", {"name": "workspace_list", "arguments": {}}),
    ("mcp/call_tool", {"name": "workspace_list", "arguments": {}}),
    ("call_tool", {"name": "workspace_list", "arguments": {}}),
    ("workspace_list", {}),
]

for method, params in call_methods:
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": int(time.time() * 1000)
    }
    if params is not None:
        payload["params"] = params
        
    resp = requests.post("http://localhost:8080/mcp/sse", json=payload, headers=headers)
    print(f"\n   Method: {method}")
    
    # Parse SSE response
    for line in resp.text.strip().split('\n'):
        if line.startswith('data: '):
            data = json.loads(line[6:])
            if "result" in data:
                print(f"   SUCCESS! Got result")
                print(f"   Result: {json.dumps(data['result'], indent=2)[:200]}")
                break
            elif "error" in data:
                print(f"   Error: {data['error']['message']}")