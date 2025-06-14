"""
Base test utilities for Terry-Form MCP
"""
import os
import json
import subprocess
import time
import requests
from pathlib import Path

class TerryFormTestBase:
    """Base class for Terry-Form tests"""
    
    @staticmethod
    def run_command(cmd, cwd=None, timeout=30):
        """Execute command and return result"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def wait_for_service(url, timeout=60, interval=2):
        """Wait for service to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(interval)
        return False
    
    @staticmethod
    def create_terraform_project(path, config):
        """Create a Terraform project for testing"""
        project_path = Path(path)
        project_path.mkdir(parents=True, exist_ok=True)
        
        main_tf = project_path / "main.tf"
        main_tf.write_text(config)
        
        return project_path
    
    @staticmethod
    def validate_terraform_output(output):
        """Validate Terraform command output"""
        required_fields = ["success", "action"]
        
        if isinstance(output, dict):
            for field in required_fields:
                if field not in output:
                    return False, f"Missing required field: {field}"
            return True, "Valid output"
        
        return False, "Output is not a dictionary"
    
    @staticmethod
    def check_health_endpoint(base_url):
        """Check service health endpoint"""
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
        except:
            return False
        return False
    
    @staticmethod
    def validate_mcp_response(response):
        """Validate MCP protocol response"""
        if not isinstance(response, dict):
            return False, "Response is not a dictionary"
        
        # Check for MCP required fields based on the protocol
        if "error" in response:
            return True, "Error response"
        
        if "result" in response:
            return True, "Success response"
        
        return False, "Invalid MCP response format"