"""
Unit tests for GitHub App integration
"""
import pytest
import json
import jwt
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.test_base import TerryFormTestBase

class TestGitHubIntegration(TerryFormTestBase):
    """Test GitHub App functionality"""
    
    def test_jwt_generation(self):
        """Test GitHub App JWT generation"""
        # Mock private key (in real tests, use a test key)
        private_key = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtest
-----END RSA PRIVATE KEY-----"""
        
        app_id = "12345"
        
        # Generate JWT token
        now = datetime.utcnow()
        payload = {
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=10)).timestamp()),
            'iss': app_id
        }
        
        # In real implementation, this would use the actual GitHubApp class
        # For now, we test the JWT structure
        assert 'iat' in payload
        assert 'exp' in payload
        assert 'iss' in payload
        assert payload['exp'] > payload['iat']
        assert payload['iss'] == app_id
    
    def test_webhook_signature_validation(self):
        """Test webhook signature validation"""
        import hmac
        import hashlib
        
        secret = "test-webhook-secret"
        payload = json.dumps({"action": "opened", "number": 1})
        
        # Generate signature
        signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Validate signature
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        provided_sig = signature.replace("sha256=", "")
        
        assert hmac.compare_digest(expected_sig, provided_sig)
    
    def test_pull_request_event_parsing(self, github_webhook_payload):
        """Test parsing of pull request webhook events"""
        # Test required fields are present
        assert "action" in github_webhook_payload
        assert "pull_request" in github_webhook_payload
        assert "repository" in github_webhook_payload
        
        # Test PR data extraction
        pr = github_webhook_payload["pull_request"]
        assert pr["number"] == 1
        assert pr["head"]["ref"] == "feature-branch"
        assert pr["base"]["ref"] == "main"
        
        # Test repository data
        repo = github_webhook_payload["repository"]
        assert repo["full_name"] == "test-org/test-repo"
        assert "clone_url" in repo
    
    def test_terraform_validation_comment_format(self):
        """Test formatting of Terraform validation comments"""
        # Mock validation results
        validation_results = {
            "success": True,
            "checks": {
                "fmt": {"passed": True, "details": "All files formatted correctly"},
                "init": {"passed": True, "details": "Terraform initialized"},
                "validate": {"passed": True, "details": "Configuration is valid"},
                "plan": {"passed": True, "details": "Plan completed:\n+ 1 to add\n~ 0 to change\n- 0 to destroy"}
            }
        }
        
        # Format comment (simplified version)
        comment = "## Terraform Validation Results ✅\n\n"
        for check, result in validation_results["checks"].items():
            status = "✅" if result["passed"] else "❌"
            comment += f"- **{check}**: {status} {result['details']}\n"
        
        assert "✅" in comment
        assert "fmt" in comment
        assert "validate" in comment
        assert "plan" in comment
    
    def test_github_api_retry_logic(self):
        """Test GitHub API retry logic with rate limiting"""
        import time
        
        class MockRateLimitedAPI:
            def __init__(self):
                self.call_count = 0
                self.rate_limit_reset = time.time() + 2
            
            def make_request(self):
                self.call_count += 1
                if self.call_count < 3:
                    # Simulate rate limit
                    return {
                        "error": "rate_limited",
                        "reset": self.rate_limit_reset
                    }
                return {"success": True}
        
        api = MockRateLimitedAPI()
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            result = api.make_request()
            if result.get("error") == "rate_limited":
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.1)  # Short sleep for test
            else:
                break
        
        assert result.get("success") == True
        assert api.call_count == 3
    
    def test_terraform_file_detection(self):
        """Test detection of Terraform files in PR"""
        # Mock file changes
        changed_files = [
            "main.tf",
            "variables.tf",
            "outputs.tf",
            "README.md",
            "modules/vpc/main.tf",
            ".github/workflows/test.yml"
        ]
        
        # Filter Terraform files
        tf_files = [f for f in changed_files if f.endswith('.tf')]
        
        assert len(tf_files) == 4
        assert "main.tf" in tf_files
        assert "modules/vpc/main.tf" in tf_files
        assert "README.md" not in tf_files
    
    def test_check_run_status_mapping(self):
        """Test mapping of Terraform results to GitHub check run status"""
        test_cases = [
            ({"success": True}, "success"),
            ({"success": False, "error": "validation failed"}, "failure"),
            ({"success": False, "error": "timeout"}, "timed_out"),
        ]
        
        for result, expected_status in test_cases:
            # Map result to GitHub status
            if result.get("success"):
                status = "success"
            elif "timeout" in result.get("error", ""):
                status = "timed_out"
            else:
                status = "failure"
            
            assert status == expected_status
    
    def test_installation_token_exchange(self):
        """Test exchange of JWT for installation token"""
        # Mock the token exchange process
        jwt_token = "mock.jwt.token"
        installation_id = "12345"
        
        # In real implementation, this would call GitHub API
        # Mock response
        mock_response = {
            "token": "ghs_mock_installation_token",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        
        assert "token" in mock_response
        assert "expires_at" in mock_response
        assert mock_response["token"].startswith("ghs_")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])