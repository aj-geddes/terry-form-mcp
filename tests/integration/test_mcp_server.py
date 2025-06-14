"""
Integration tests for MCP server endpoints
"""
import pytest
import requests
import json
import time
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.test_base import TerryFormTestBase

class TestMCPServer(TerryFormTestBase):
    """Test MCP server integration"""
    
    @pytest.fixture
    def mcp_base_url(self):
        """Get MCP server base URL"""
        return "http://localhost:8080"
    
    def test_health_endpoint(self, mcp_base_url):
        """Test health check endpoint"""
        response = requests.get(f"{mcp_base_url}/health", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_ready_endpoint(self, mcp_base_url):
        """Test readiness endpoint"""
        response = requests.get(f"{mcp_base_url}/ready", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
    
    def test_mcp_list_tools(self, mcp_base_url):
        """Test MCP list tools endpoint"""
        # MCP protocol request
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        response = requests.post(
            f"{mcp_base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate MCP response format
        assert "jsonrpc" in data
        assert data["jsonrpc"] == "2.0"
        assert "id" in data
        assert data["id"] == 1
        
        # Check tools are listed
        assert "result" in data
        tools = data["result"].get("tools", [])
        assert isinstance(tools, list)
        
        # Verify expected tools
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "terraform_init",
            "terraform_validate", 
            "terraform_fmt",
            "terraform_plan"
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Tool {expected} not found"
    
    def test_terraform_init_tool(self, mcp_base_url, test_workspace, terraform_config):
        """Test terraform init via MCP"""
        # Create test project
        project_path = self.create_terraform_project(
            test_workspace / "mcp_init_test",
            terraform_config
        )
        
        # MCP tool call
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "terraform_init",
                "arguments": {
                    "path": str(project_path)
                }
            },
            "id": 2
        }
        
        response = requests.post(
            f"{mcp_base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response
        assert "result" in data
        result = data["result"]
        assert result.get("content", [])
        
        # Verify init succeeded
        content = result["content"][0] if result.get("content") else {}
        assert "text" in content
        assert "success" in content["text"].lower() or "initialized" in content["text"].lower()
    
    def test_terraform_validate_tool(self, mcp_base_url, test_workspace, terraform_config):
        """Test terraform validate via MCP"""
        # Create and init project
        project_path = self.create_terraform_project(
            test_workspace / "mcp_validate_test",
            terraform_config
        )
        
        # Init first
        self.run_command("terraform init -input=false", cwd=str(project_path))
        
        # MCP validate call
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "terraform_validate",
                "arguments": {
                    "path": str(project_path)
                }
            },
            "id": 3
        }
        
        response = requests.post(
            f"{mcp_base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
    
    def test_concurrent_mcp_requests(self, mcp_base_url):
        """Test concurrent MCP requests"""
        import concurrent.futures
        
        def make_list_request(request_id):
            request_data = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": request_id
            }
            
            response = requests.post(
                f"{mcp_base_url}/mcp",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            return response.status_code == 200, response.json()
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_list_request, i)
                for i in range(10)
            ]
            
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All should succeed
        for success, data in results:
            assert success
            assert "result" in data
    
    def test_error_handling(self, mcp_base_url):
        """Test MCP error handling"""
        # Invalid method
        request_data = {
            "jsonrpc": "2.0",
            "method": "invalid/method",
            "id": 999
        }
        
        response = requests.post(
            f"{mcp_base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200  # MCP errors are still 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found
    
    def test_terraform_plan_with_vars(self, mcp_base_url, test_workspace, terraform_config):
        """Test terraform plan with variables via MCP"""
        project_path = self.create_terraform_project(
            test_workspace / "mcp_plan_test",
            terraform_config
        )
        
        # Init
        self.run_command("terraform init -input=false", cwd=str(project_path))
        
        # Plan with variables
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "terraform_plan",
                "arguments": {
                    "path": str(project_path),
                    "vars": {
                        "test_var": "custom_value"
                    }
                }
            },
            "id": 4
        }
        
        response = requests.post(
            f"{mcp_base_url}/mcp",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or "error" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])