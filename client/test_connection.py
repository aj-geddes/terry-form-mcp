#!/usr/bin/env python3
"""
Test connection to Terry-Form MCP
"""
import requests
import json
import subprocess
import time
import sys

def test_connection():
    """Test connection to Terry-Form MCP"""
    print("Terry-Form MCP Connection Test")
    print("=" * 40)
    
    # Check kubectl
    print("\n1. Checking kubectl...")
    try:
        result = subprocess.run(["kubectl", "version", "--client"], 
                               capture_output=True, text=True)
        print("✓ kubectl is installed")
    except:
        print("✗ kubectl not found!")
        return False
    
    # Check namespace
    print("\n2. Checking namespace...")
    result = subprocess.run(
        ["kubectl", "get", "namespace", "terry-form-system"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✓ Namespace terry-form-system exists")
    else:
        print("✗ Namespace not found!")
        return False
    
    # Check pods
    print("\n3. Checking pods...")
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "terry-form-system", 
         "-l", "app.kubernetes.io/name=terry-form-mcp", "-o", "json"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        pods = json.loads(result.stdout)
        ready_pods = [p for p in pods.get("items", []) 
                     if all(c["status"] for c in p["status"].get("conditions", []) 
                           if c["type"] == "Ready")]
        if ready_pods:
            print(f"✓ Found {len(ready_pods)} ready pod(s)")
        else:
            print("✗ No ready pods found!")
            return False
    else:
        print("✗ Failed to get pods!")
        return False
    
    # Test port forward
    print("\n4. Testing port forward...")
    pf = subprocess.Popen(
        ["kubectl", "port-forward", "-n", "terry-form-system",
         "service/terry-form-mcp", "8080:8000"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    
    time.sleep(3)
    
    try:
        # Test health endpoint
        print("\n5. Testing health endpoint...")
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed: {data}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
        
        # Test MCP endpoint
        print("\n6. Testing MCP endpoint...")
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        response = requests.post(
            "http://localhost:8080/mcp",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                tools = data["result"].get("tools", [])
                print(f"✓ MCP endpoint working, found {len(tools)} tools:")
                for tool in tools[:5]:  # Show first 5 tools
                    print(f"  - {tool['name']}")
                if len(tools) > 5:
                    print(f"  ... and {len(tools)-5} more")
            else:
                print("✗ Invalid MCP response")
                return False
        else:
            print(f"✗ MCP request failed: {response.status_code}")
            return False
            
    finally:
        pf.terminate()
        pf.wait()
    
    print("\n" + "=" * 40)
    print("✓ All tests passed! Terry-Form MCP is ready.")
    print("\nYou can now configure Claude Desktop with:")
    print("  claude_desktop_config_stdio.json")
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)