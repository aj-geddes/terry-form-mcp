#!/usr/bin/env python3
"""Direct test of AI service with vault paths"""
import json
import asyncio
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Temporarily patch the secrets path for AI service
import ai_service
ai_service.AIServiceManager.secrets_path = Path("/vault/secrets")

# Temporarily patch the secrets path for auth manager
import auth_manager
auth_manager.AuthenticationManager.secrets_path = Path("/vault/secrets")

async def test_ai():
    """Test AI service functionality"""
    print("Testing AI Service with Vault secrets...")
    
    # Initialize services
    ai_svc = ai_service.ai_service
    auth_mgr = auth_manager.auth_manager
    
    # Test AI status
    print("\n1. Testing AI Status:")
    status = ai_svc.get_ai_status()
    print(json.dumps(status, indent=2))
    
    if status.get("configured"):
        # Test Terraform code analysis
        print("\n2. Testing Terraform Code Analysis:")
        test_code = """
resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  
  tags = {
    Name = "test-instance"
  }
}
"""
        try:
            result = await ai_svc.analyze_terraform_code(test_code, "Development web server")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Analysis failed: {e}")
    
    # Test auth status
    print("\n3. Testing Auth Status:")
    auth_status = auth_mgr.get_auth_status()
    print(json.dumps(auth_status, indent=2))

if __name__ == "__main__":
    asyncio.run(test_ai())