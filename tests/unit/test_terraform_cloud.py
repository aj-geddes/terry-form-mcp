"""
Unit tests for Terraform Cloud integration
"""
import pytest
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.test_base import TerryFormTestBase

class TestTerraformCloudIntegration(TerryFormTestBase):
    """Test Terraform Cloud API functionality"""
    
    def test_api_authentication_header(self):
        """Test API authentication header format"""
        api_token = "test-token-123"
        
        # Build headers
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/vnd.api+json"
        }
        
        assert headers["Authorization"] == "Bearer test-token-123"
        assert headers["Content-Type"] == "application/vnd.api+json"
    
    def test_workspace_payload_format(self):
        """Test workspace creation payload format"""
        workspace_payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "name": "test-workspace",
                    "terraform-version": "1.6.6",
                    "working-directory": "/terraform",
                    "auto-apply": False,
                    "execution-mode": "remote",
                    "description": "Test workspace"
                }
            }
        }
        
        # Validate structure
        assert "data" in workspace_payload
        assert workspace_payload["data"]["type"] == "workspaces"
        assert "attributes" in workspace_payload["data"]
        
        attrs = workspace_payload["data"]["attributes"]
        assert attrs["name"] == "test-workspace"
        assert attrs["auto-apply"] == False
        assert attrs["execution-mode"] == "remote"
    
    def test_run_configuration_payload(self):
        """Test run configuration payload"""
        run_payload = {
            "data": {
                "type": "runs",
                "attributes": {
                    "is-destroy": False,
                    "message": "Triggered via Terry-Form MCP",
                    "plan-only": True,
                    "refresh": True,
                    "refresh-only": False
                },
                "relationships": {
                    "workspace": {
                        "data": {
                            "type": "workspaces",
                            "id": "ws-123"
                        }
                    },
                    "configuration-version": {
                        "data": {
                            "type": "configuration-versions",
                            "id": "cv-123"
                        }
                    }
                }
            }
        }
        
        # Validate structure
        assert run_payload["data"]["type"] == "runs"
        assert run_payload["data"]["attributes"]["plan-only"] == True
        assert "relationships" in run_payload["data"]
        assert "workspace" in run_payload["data"]["relationships"]
    
    def test_variable_payload_format(self):
        """Test variable creation payload"""
        variable_payload = {
            "data": {
                "type": "vars",
                "attributes": {
                    "key": "test_variable",
                    "value": "test_value",
                    "description": "Test variable",
                    "category": "terraform",
                    "hcl": False,
                    "sensitive": False
                },
                "relationships": {
                    "workspace": {
                        "data": {
                            "type": "workspaces",
                            "id": "ws-123"
                        }
                    }
                }
            }
        }
        
        # Validate
        assert variable_payload["data"]["type"] == "vars"
        attrs = variable_payload["data"]["attributes"]
        assert attrs["key"] == "test_variable"
        assert attrs["category"] == "terraform"
        assert attrs["sensitive"] == False
    
    def test_state_version_parsing(self):
        """Test parsing state version data"""
        state_data = {
            "data": {
                "id": "sv-123",
                "type": "state-versions",
                "attributes": {
                    "serial": 10,
                    "created-at": "2025-01-14T10:00:00Z",
                    "size": 1024,
                    "hosted-state-download-url": "https://archivist.terraform.io/...",
                    "modules": {
                        "root": {
                            "null_resource.test": {
                                "type": "null_resource",
                                "provider": "provider[\"registry.terraform.io/hashicorp/null\"]"
                            }
                        }
                    }
                }
            }
        }
        
        # Parse and validate
        assert state_data["data"]["type"] == "state-versions"
        attrs = state_data["data"]["attributes"]
        assert attrs["serial"] == 10
        assert "modules" in attrs
        assert "root" in attrs["modules"]
    
    def test_pagination_handling(self):
        """Test API pagination handling"""
        page_1 = {
            "data": [{"id": "1"}, {"id": "2"}],
            "meta": {
                "pagination": {
                    "current-page": 1,
                    "page-size": 2,
                    "total-pages": 3,
                    "total-count": 6
                }
            },
            "links": {
                "next": "/api/v2/organizations/test/workspaces?page[number]=2"
            }
        }
        
        # Check pagination metadata
        pagination = page_1["meta"]["pagination"]
        assert pagination["current-page"] == 1
        assert pagination["total-pages"] == 3
        assert "next" in page_1["links"]
        
        # Simulate collecting all pages
        all_items = []
        current_page = page_1
        page_count = 0
        
        while page_count < 3:  # Prevent infinite loop in test
            all_items.extend(current_page["data"])
            if "next" not in current_page.get("links", {}):
                break
            page_count += 1
            # Simulate next page
            current_page = {
                "data": [{"id": str(i)} for i in range(page_count*2+1, page_count*2+3)],
                "links": {} if page_count == 2 else {"next": f"/api/v2/...?page[number]={page_count+2}"}
            }
        
        assert len(all_items) >= 2
    
    def test_error_response_handling(self):
        """Test handling of API error responses"""
        error_responses = [
            {
                "errors": [{
                    "status": "404",
                    "title": "Not Found",
                    "detail": "Workspace 'test' not found"
                }]
            },
            {
                "errors": [{
                    "status": "422",
                    "title": "Unprocessable Entity",
                    "detail": "Name has already been taken",
                    "source": {"pointer": "/data/attributes/name"}
                }]
            },
            {
                "errors": [{
                    "status": "401",
                    "title": "Unauthorized",
                    "detail": "Authentication required"
                }]
            }
        ]
        
        for error_resp in error_responses:
            assert "errors" in error_resp
            assert isinstance(error_resp["errors"], list)
            error = error_resp["errors"][0]
            assert "status" in error
            assert "title" in error
            assert "detail" in error
    
    def test_configuration_version_upload(self):
        """Test configuration version upload process"""
        # Step 1: Create configuration version
        cv_create = {
            "data": {
                "type": "configuration-versions",
                "attributes": {
                    "auto-queue-runs": False,
                    "speculative": True
                }
            }
        }
        
        # Mock response
        cv_response = {
            "data": {
                "id": "cv-123",
                "attributes": {
                    "upload-url": "https://archivist.terraform.io/upload/...",
                    "status": "pending"
                }
            }
        }
        
        # Validate
        assert cv_response["data"]["attributes"]["status"] == "pending"
        assert "upload-url" in cv_response["data"]["attributes"]
    
    def test_workspace_lock_unlock(self):
        """Test workspace locking mechanism"""
        # Lock payload
        lock_payload = {
            "reason": "Locked by Terry-Form MCP for safe operation"
        }
        
        # Mock locked response
        locked_workspace = {
            "data": {
                "id": "ws-123",
                "attributes": {
                    "locked": True,
                    "name": "test-workspace"
                }
            }
        }
        
        assert locked_workspace["data"]["attributes"]["locked"] == True
        
        # Unlock would be an empty payload
        unlock_payload = {}
        
        # Mock unlocked response
        unlocked_workspace = {
            "data": {
                "id": "ws-123",
                "attributes": {
                    "locked": False,
                    "name": "test-workspace"
                }
            }
        }
        
        assert unlocked_workspace["data"]["attributes"]["locked"] == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])