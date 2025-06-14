#!/usr/bin/env python3
"""
Test script for Terry-Form MCP with LSP integration

This script tests both the existing Terraform execution capabilities
and the new LSP-based intelligence features.
"""

import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path

def run_mcp_tool_test(tool_call, description):
    """Run an MCP tool test and display results"""
    print(f"\n🧪 Testing: {description}")
    print("=" * 60)
    
    try:
        # Convert tool call to JSON
        test_input = json.dumps(tool_call, indent=2)
        print(f"Input: {test_input}")
        
        # Run the MCP server with test input
        result = subprocess.run(
            ["python3", "server_with_lsp.py"],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Errors: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Test failed: {e}")

def create_test_terraform_files():
    """Create sample Terraform files for testing"""
    test_dir = "/tmp/terraform-test"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create a simple main.tf
    main_tf_content = '''
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-vpc"
    Environment = var.environment
  }
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}
'''
    
    with open(f"{test_dir}/main.tf", "w") as f:
        f.write(main_tf_content)
    
    # Create variables.tf
    variables_tf_content = '''
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "AWS key pair name"
  type        = string
  default     = ""
}
'''
    
    with open(f"{test_dir}/variables.tf", "w") as f:
        f.write(variables_tf_content)
    
    return test_dir

def main():
    print("🚀 Terry-Form MCP with LSP Integration - Test Suite")
    print("=" * 60)
    
    # Create test files
    test_dir = create_test_terraform_files()
    print(f"📁 Created test files in: {test_dir}")
    
    # Test 1: Original terry tool (Terraform execution)
    run_mcp_tool_test(
        {
            "tool": "terry",
            "arguments": {
                "path": "terraform-test",
                "actions": ["validate"],
                "vars": {}
            }
        },
        "Original Terraform validation via terry tool"
    )
    
    # Test 2: LSP Status check
    run_mcp_tool_test(
        {
            "tool": "terraform_lsp_status",
            "arguments": {}
        },
        "terraform-ls LSP server status"
    )
    
    # Test 3: LSP validation
    run_mcp_tool_test(
        {
            "tool": "terraform_validate_lsp",
            "arguments": {
                "file_path": "main.tf",
                "workspace_path": "terraform-test"
            }
        },
        "Terraform validation via LSP"
    )
    
    # Test 4: LSP hover information
    run_mcp_tool_test(
        {
            "tool": "terraform_hover",
            "arguments": {
                "file_path": "main.tf",
                "line": 15,
                "character": 10,
                "workspace_path": "terraform-test"
            }
        },
        "Hover information for aws provider"
    )
    
    # Test 5: LSP completion
    run_mcp_tool_test(
        {
            "tool": "terraform_complete", 
            "arguments": {
                "file_path": "main.tf",
                "line": 20,
                "character": 5,
                "workspace_path": "terraform-test"
            }
        },
        "Code completion suggestions"
    )
    
    # Test 6: LSP formatting
    run_mcp_tool_test(
        {
            "tool": "terraform_format_lsp",
            "arguments": {
                "file_path": "main.tf",
                "workspace_path": "terraform-test"
            }
        },
        "Document formatting via LSP"
    )
    
    print("\n✅ Test suite completed!")
    print(f"🧹 Cleaning up test files in {test_dir}")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
