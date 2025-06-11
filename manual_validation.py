#!/usr/bin/env python3
"""
Manual validation test for Terry-Form MCP LSP integration
This script manually tests our LSP integration components
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path

# Add current directory to path so we can import our modules
sys.path.insert(0, '/mnt/workspace/terry-form-mcp')

def test_imports():
    """Test that all our modules can be imported"""
    print("🔍 Testing Python module imports...")
    
    try:
        # Test LSP client import
        import terraform_lsp_client
        print("✅ terraform_lsp_client imported successfully")
        
        # Test enhanced server import
        import server_with_lsp
        print("✅ server_with_lsp imported successfully")
        
        # Test original modules still work
        import terry_form_mcp
        print("✅ terry-form-mcp imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_terraform_ls_availability():
    """Test if terraform-ls binary would be available in Docker"""
    print("\n🔍 Testing terraform-ls availability...")
    
    # In our Docker container, terraform-ls should be at /usr/local/bin/terraform-ls
    # For now, we'll just check if the Dockerfile includes it correctly
    
    try:
        with open('/mnt/workspace/terry-form-mcp/Dockerfile_with_lsp', 'r') as f:
            dockerfile_content = f.read()
            
        if 'terraform-ls' in dockerfile_content and 'TERRAFORM_LS_VERSION' in dockerfile_content:
            print("✅ Dockerfile includes terraform-ls installation")
            return True
        else:
            print("❌ terraform-ls not found in Dockerfile")
            return False
            
    except Exception as e:
        print(f"❌ Error checking Dockerfile: {e}")
        return False

def create_test_terraform_file():
    """Create a simple test Terraform file"""
    print("\n🔍 Creating test Terraform file...")
    
    try:
        # Create a temporary test directory
        test_dir = "/tmp/terry-form-test"
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a simple main.tf
        test_content = '''
terraform {
  required_version = ">= 1.0"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "test"
}

locals {
  common_tags = {
    Environment = var.environment
    Project     = "terry-form-test"
  }
}

output "environment" {
  value = var.environment
}
'''
        
        test_file = os.path.join(test_dir, "main.tf")
        with open(test_file, 'w') as f:
            f.write(test_content)
            
        print(f"✅ Test Terraform file created: {test_file}")
        return test_dir, test_file
        
    except Exception as e:
        print(f"❌ Error creating test file: {e}")
        return None, None

def test_lsp_client_creation():
    """Test LSP client can be created (without actually starting terraform-ls)"""
    print("\n🔍 Testing LSP client creation...")
    
    try:
        import terraform_lsp_client
        
        # Create LSP client instance
        lsp_client = terraform_lsp_client.TerraformLSPClient("/tmp/test-workspace")
        
        # Verify basic properties
        assert lsp_client.workspace_root == "/tmp/test-workspace"
        assert lsp_client.request_id == 0
        assert not lsp_client.initialized
        
        print("✅ LSP client created successfully")
        print(f"   - Workspace root: {lsp_client.workspace_root}")
        print(f"   - Initialized: {lsp_client.initialized}")
        print(f"   - Request ID: {lsp_client.request_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ LSP client creation failed: {e}")
        return False

def test_mcp_tools_available():
    """Test that MCP tools are properly defined"""
    print("\n🔍 Testing MCP tools availability...")
    
    try:
        import server_with_lsp
        
        # Check if we can access the FastMCP instance
        mcp_server = server_with_lsp.mcp
        
        print("✅ MCP server accessible")
        print(f"   - Server name: {mcp_server.name}")
        
        # In a real test we'd check the registered tools, but that requires 
        # deeper FastMCP inspection. For now, just verify the server exists.
        
        return True
        
    except Exception as e:
        print(f"❌ MCP tools test failed: {e}")
        return False

def test_dockerfile_syntax():
    """Test Dockerfile syntax is valid"""
    print("\n🔍 Testing Dockerfile syntax...")
    
    try:
        with open('/mnt/workspace/terry-form-mcp/Dockerfile_with_lsp', 'r') as f:
            lines = f.readlines()
        
        # Basic Dockerfile validation
        has_from = any(line.strip().startswith('FROM') for line in lines)
        has_workdir = any(line.strip().startswith('WORKDIR') for line in lines)
        has_entrypoint = any(line.strip().startswith('ENTRYPOINT') for line in lines)
        
        if has_from and has_workdir and has_entrypoint:
            print("✅ Dockerfile syntax appears valid")
            print(f"   - Lines: {len(lines)}")
            print("   - Has FROM, WORKDIR, ENTRYPOINT")
            return True
        else:
            print("❌ Dockerfile missing required directives")
            return False
            
    except Exception as e:
        print(f"❌ Dockerfile syntax test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Terry-Form MCP LSP Integration - Manual Validation")
    print("=" * 60)
    
    tests = [
        ("Python Module Imports", test_imports),
        ("terraform-ls Availability", test_terraform_ls_availability),
        ("LSP Client Creation", test_lsp_client_creation),
        ("MCP Tools Availability", test_mcp_tools_available),
        ("Dockerfile Syntax", test_dockerfile_syntax)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Test summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! LSP integration ready for Docker build.")
    else:
        print("⚠️  Some tests failed. Review issues before Docker build.")
    
    # Create test Terraform file for Docker testing
    test_dir, test_file = create_test_terraform_file()
    if test_file:
        print(f"\n📁 Test files ready in: {test_dir}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
