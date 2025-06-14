#!/usr/bin/env python3
"""
Quick test of the fixed LSP client
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, '/mnt/workspace/terry-form-mcp')

from terraform_lsp_client_fixed import TerraformLSPClient

async def test_lsp_client():
    """Test the LSP client initialization"""
    print("🔍 Testing LSP Client Initialization...")
    
    # Test workspace
    workspace = "/mnt/workspace/lsp-test"
    
    # Ensure workspace exists with a Terraform file
    os.makedirs(workspace, exist_ok=True)
    
    # Create a simple test file
    test_file = os.path.join(workspace, "test.tf")
    with open(test_file, 'w') as f:
        f.write('''terraform {
  required_version = ">= 1.0"
}

resource "azurerm_resource_group" "example" {
  name     = "test-rg"
  location = "East US"
}
''')
    
    # Initialize LSP client
    client = TerraformLSPClient()
    
    try:
        print(f"📁 Starting LSP for workspace: {workspace}")
        success = await client.start_terraform_ls(workspace)
        
        if success:
            print("✅ LSP Client initialized successfully!")
            print(f"🔧 Capabilities: {list(client.capabilities.keys())}")
            
            # Test document validation
            print("\n📝 Testing document validation...")
            result = await client.validate_document(test_file)
            print(f"Validation result: {result}")
            
            # Test hover at a specific position
            print("\n🎯 Testing hover info...")
            hover_result = await client.get_hover_info(test_file, 4, 10)  # Line 4, character 10
            print(f"Hover result: {hover_result}")
            
        else:
            print("❌ LSP Client initialization failed!")
            if client.initialization_error:
                print(f"Error: {client.initialization_error}")
        
        await client.shutdown()
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        await client.shutdown()

if __name__ == "__main__":
    asyncio.run(test_lsp_client())
