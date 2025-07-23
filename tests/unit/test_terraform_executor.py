"""
Unit tests for Terraform Executor
"""
import pytest
import os
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from tests.test_base import TerryFormTestBase

class TestTerraformExecutor(TerryFormTestBase):
    """Test Terraform execution functionality"""

    def test_terraform_init(self, test_workspace, terraform_config):
        """Test terraform init command"""
        # Create test project
        project_path = self.create_terraform_project(
            test_workspace / "init_test",
            terraform_config
        )

        # Run terraform init
        result = self.run_command(
            "terraform init -input=false",
            cwd=str(project_path)
        )

        assert result["success"], f"Terraform init failed: {result.get('stderr', '')}"
        assert "Terraform has been successfully initialized" in result["stdout"]
        assert (project_path / ".terraform").exists()

    def test_terraform_validate(self, test_workspace, terraform_config):
        """Test terraform validate command"""
        # Create and init project
        project_path = self.create_terraform_project(
            test_workspace / "validate_test",
            terraform_config
        )

        # Init first
        self.run_command("terraform init -input=false", cwd=str(project_path))

        # Run validate
        result = self.run_command(
            "terraform validate",
            cwd=str(project_path)
        )

        assert result["success"], f"Terraform validate failed: {result.get('stderr', '')}"
        assert "Success" in result["stdout"] or result["stdout"].strip() == ""

    def test_terraform_fmt_check(self, test_workspace):
        """Test terraform fmt check"""
        # Create unformatted config
        unformatted = '''
resource "null_resource" "test" {
provisioner "local-exec" {
command = "echo test"
}
}
'''
        project_path = self.create_terraform_project(
            test_workspace / "fmt_test",
            unformatted
        )

        # Check formatting
        result = self.run_command(
            "terraform fmt -check",
            cwd=str(project_path)
        )

        # Should fail because unformatted
        assert not result["success"], "Expected fmt check to fail on unformatted code"

        # Format it
        self.run_command("terraform fmt", cwd=str(project_path))

        # Check again
        result = self.run_command(
            "terraform fmt -check",
            cwd=str(project_path)
        )

        assert result["success"], "Terraform fmt check should pass after formatting"

    def test_terraform_plan(self, test_workspace, terraform_config):
        """Test terraform plan command"""
        # Create and init project
        project_path = self.create_terraform_project(
            test_workspace / "plan_test",
            terraform_config
        )

        # Init
        self.run_command("terraform init -input=false", cwd=str(project_path))

        # Plan
        result = self.run_command(
            "terraform plan -input=false -no-color",
            cwd=str(project_path)
        )

        assert result["success"], f"Terraform plan failed: {result.get('stderr', '')}"
        assert "Plan:" in result["stdout"] or "No changes" in result["stdout"]

    def test_terraform_plan_with_vars(self, test_workspace, terraform_config):
        """Test terraform plan with variables"""
        project_path = self.create_terraform_project(
            test_workspace / "plan_vars_test",
            terraform_config
        )

        # Init
        self.run_command("terraform init -input=false", cwd=str(project_path))

        # Plan with variable
        result = self.run_command(
            ['terraform', 'plan', '-input=false', '-no-color', '-var', 'test_var=custom_value'],
            cwd=str(project_path)
        )

        assert result["success"], f"Terraform plan with vars failed: {result.get('stderr', '')}"

    def test_invalid_terraform_config(self, test_workspace, invalid_terraform_config):
        """Test handling of invalid Terraform configuration"""
        project_path = self.create_terraform_project(
            test_workspace / "invalid_test",
            invalid_terraform_config
        )

        # Init (should succeed even with invalid config)
        self.run_command("terraform init -input=false", cwd=str(project_path))

        # Validate should fail
        result = self.run_command(
            "terraform validate",
            cwd=str(project_path)
        )

        assert not result["success"], "Validation should fail for invalid config"
        assert "error" in result["stdout"].lower() or "error" in result["stderr"].lower()

    def test_terraform_version(self):
        """Test terraform version command"""
        result = self.run_command("terraform version")

        assert result["success"], "Terraform version command failed"
        assert "Terraform v" in result["stdout"]

    def test_concurrent_executions(self, test_workspace, terraform_config):
        """Test concurrent Terraform executions don't interfere"""
        import concurrent.futures

        def run_terraform_in_dir(dir_name):
            project_path = self.create_terraform_project(
                test_workspace / dir_name,
                terraform_config
            )

            # Init and validate
            init_result = self.run_command(
                "terraform init -input=false",
                cwd=str(project_path)
            )

            if not init_result["success"]:
                return False, f"Init failed: {init_result}"

            validate_result = self.run_command(
                "terraform validate",
                cwd=str(project_path)
            )

            return validate_result["success"], validate_result

        # Run 5 concurrent executions
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(run_terraform_in_dir, f"concurrent_{i}")
                for i in range(5)
            ]

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        for success, result in results:
            assert success, f"Concurrent execution failed: {result}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
