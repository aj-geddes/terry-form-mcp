#!/usr/bin/env python3
"""
Test MCP session flow
"""
import requests
import json

# Step 1: Get a session ID
print("1. Getting session ID...")
resp = requests.get("http://localhost:8080/mcp/", headers={"Accept": "text/event-stream"})
session_id = resp.headers.get("mcp-session-id")
print(f"   Got session ID: {session_id}")
print(f"   Response: {resp.status_code} - {resp.text[:100]}")

# Step 2: Try to use the session ID
print("\n2. Using session ID to list tools...")
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Cookie": f"mcp-session-id={session_id}"
}

payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
}

resp = requests.post("http://localhost:8080/mcp/sse", json=payload, headers=headers)
print(f"   Response: {resp.status_code}")
print(f"   Headers: {dict(resp.headers)}")
print(f"   Body: {resp.text[:200]}")

# Step 3: Try with the new session ID if provided
if "mcp-session-id" in resp.headers:
    new_session = resp.headers["mcp-session-id"]
    print(f"\n3. Got new session ID: {new_session}")
    
    headers["Cookie"] = f"mcp-session-id={new_session}"
    resp = requests.post("http://localhost:8080/mcp/sse", json=payload, headers=headers)
    print(f"   Response: {resp.status_code}")
    print(f"   Body: {resp.text[:200]}")