"""
Test configuration and fixtures for Terry-Form MCP v3.0.0
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path

# Test configuration
TEST_WORKSPACE = "/tmp/test-workspace"
TEST_TIMEOUT = 30

@pytest.fixture(scope="session")
def test_workspace():
    """Create a temporary workspace for tests"""
    workspace = Path(TEST_WORKSPACE)
    workspace.mkdir(exist_ok=True)
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)

@pytest.fixture
def terraform_config():
    """Sample Terraform configuration for testing"""
    return '''
terraform {
  required_version = ">= 1.0"
}

resource "null_resource" "test" {
  provisioner "local-exec" {
    command = "echo 'Test resource'"
  }
}

variable "test_var" {
  type        = string
  description = "Test variable"
  default     = "test_value"
}

output "test_output" {
  value = "test_output_value"
}
'''

@pytest.fixture
def invalid_terraform_config():
    """Invalid Terraform configuration for error testing"""
    return '''
resource "invalid_resource" "test" {
  invalid_argument = 
}
'''

@pytest.fixture
def github_webhook_payload():
    """Sample GitHub webhook payload"""
    return {
        "action": "opened",
        "pull_request": {
            "number": 1,
            "head": {
                "ref": "feature-branch",
                "sha": "abc123"
            },
            "base": {
                "ref": "main"
            }
        },
        "repository": {
            "full_name": "test-org/test-repo",
            "clone_url": "https://github.com/test-org/test-repo.git"
        }
    }

@pytest.fixture
def terraform_cloud_config():
    """Terraform Cloud test configuration"""
    return {
        "organization": "test-org",
        "workspace": "test-workspace",
        "api_token": "test-token"
    }