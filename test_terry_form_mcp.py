#!/usr/bin/env python3
"""
Comprehensive tests for terry-form-mcp.py (core Terraform execution module).

Covers:
- build_terraform_command(): all valid actions, var/var-file flags, invalid actions
- parse_plan_output(): non-existent paths, valid JSON plan parsing, error handling
- parse_text_plan_summary(): regex-based fallback plan parsing
- get_controlled_env(): environment variable filtering and forced vars
- run_terraform(): subprocess execution, error handling, timeout, env vars
- run_terraform_actions(): sequential multi-action execution, stop-on-failure
"""

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the hyphenated module using importlib and register it under a valid
# dotted name so that unittest.mock.patch() string targets work correctly.
terry_form_mcp = importlib.import_module("terry-form-mcp")
sys.modules["terry_form_mcp"] = terry_form_mcp

# Convenient aliases for the functions under test
build_terraform_command = terry_form_mcp.build_terraform_command
parse_plan_output = terry_form_mcp.parse_plan_output
parse_text_plan_summary = terry_form_mcp.parse_text_plan_summary
get_controlled_env = terry_form_mcp.get_controlled_env
run_terraform = terry_form_mcp.run_terraform
run_terraform_actions = terry_form_mcp.run_terraform_actions
ALLOWED_ENV_VARS = terry_form_mcp.ALLOWED_ENV_VARS
FORCED_ENV_VARS = terry_form_mcp.FORCED_ENV_VARS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace directory for Terraform operations."""
    return str(tmp_path)


@pytest.fixture
def workspace_with_plan(tmp_path):
    """Create a workspace containing a dummy tfplan file."""
    plan_file = tmp_path / "tfplan"
    plan_file.write_text("dummy plan content")
    return str(tmp_path)


@pytest.fixture
def clean_env(monkeypatch):
    """Strip environment down to only HOME and PATH for deterministic tests."""
    for key in list(os.environ.keys()):
        if key not in ("HOME", "PATH"):
            monkeypatch.delenv(key, raising=False)


# ---------------------------------------------------------------------------
# 1. build_terraform_command()
# ---------------------------------------------------------------------------


class TestBuildTerraformCommand:
    """Tests for the build_terraform_command function."""

    # -- Valid actions -------------------------------------------------------

    def test_init_command(self):
        """init action produces correct CLI arguments with -input=false."""
        cmd = build_terraform_command("init")
        assert cmd == ["terraform", "init", "-input=false", "-no-color"]

    def test_validate_command(self):
        """validate action produces correct CLI arguments."""
        cmd = build_terraform_command("validate")
        assert cmd == ["terraform", "validate", "-no-color"]

    def test_fmt_command(self):
        """fmt action includes -check, -diff, and -no-color flags."""
        cmd = build_terraform_command("fmt")
        assert cmd == ["terraform", "fmt", "-check", "-diff", "-no-color"]

    def test_plan_command_basic(self):
        """plan action produces correct CLI arguments with -out=tfplan."""
        cmd = build_terraform_command("plan")
        assert cmd == ["terraform", "plan", "-input=false", "-no-color", "-out=tfplan"]

    def test_plan_command_with_var_file(self):
        """plan action passes -var-file flag when var_file is specified."""
        cmd = build_terraform_command("plan", var_file="/tmp/vars.tfvars.json")
        assert cmd == [
            "terraform",
            "plan",
            "-input=false",
            "-no-color",
            "-out=tfplan",
            "-var-file",
            "/tmp/vars.tfvars.json",
        ]

    def test_plan_command_without_var_file(self):
        """plan action omits -var-file when var_file is None."""
        cmd = build_terraform_command("plan", var_file=None)
        assert "-var-file" not in cmd

    def test_show_command(self):
        """show action includes -json and -no-color flags."""
        cmd = build_terraform_command("show")
        assert cmd == ["terraform", "show", "-json", "-no-color"]

    def test_graph_command(self):
        """graph action produces minimal command without extra flags."""
        cmd = build_terraform_command("graph")
        assert cmd == ["terraform", "graph"]

    def test_providers_command(self):
        """providers action produces minimal command."""
        cmd = build_terraform_command("providers")
        assert cmd == ["terraform", "providers"]

    def test_version_command(self):
        """version action includes -json flag."""
        cmd = build_terraform_command("version")
        assert cmd == ["terraform", "version", "-json"]

    # -- All commands start with 'terraform' --------------------------------

    @pytest.mark.parametrize(
        "action",
        ["init", "validate", "fmt", "plan", "show", "graph", "providers", "version"],
    )
    def test_all_valid_actions_start_with_terraform(self, action):
        """Every valid action should produce a command starting with 'terraform'."""
        cmd = build_terraform_command(action)
        assert cmd[0] == "terraform"
        assert cmd[1] == action

    # -- Invalid / destructive actions --------------------------------------

    def test_apply_is_rejected(self):
        """apply is a destructive action and must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported Terraform action"):
            build_terraform_command("apply")

    def test_destroy_is_rejected(self):
        """destroy is a destructive action and must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported Terraform action"):
            build_terraform_command("destroy")

    def test_import_is_rejected(self):
        """import is an unsupported action and must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported Terraform action"):
            build_terraform_command("import")

    def test_taint_is_rejected(self):
        """taint is an unsupported action and must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported Terraform action"):
            build_terraform_command("taint")

    def test_untaint_is_rejected(self):
        """untaint is an unsupported action and must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported Terraform action"):
            build_terraform_command("untaint")

    def test_empty_action_is_rejected(self):
        """An empty string action must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported Terraform action"):
            build_terraform_command("")

    def test_arbitrary_string_is_rejected(self):
        """An arbitrary string should be rejected."""
        with pytest.raises(ValueError, match="Unsupported Terraform action"):
            build_terraform_command("rm -rf /")

    # -- vars parameter is accepted but unused by build_terraform_command ----

    def test_vars_parameter_is_ignored(self):
        """vars parameter is accepted but does not affect the command.

        Variable injection happens at the run_terraform level via temp var files.
        """
        cmd_with_vars = build_terraform_command("plan", vars={"region": "us-east-1"})
        cmd_without_vars = build_terraform_command("plan")
        assert cmd_with_vars == cmd_without_vars

    def test_init_ignores_var_file(self):
        """Non-plan actions ignore var_file even if passed."""
        cmd = build_terraform_command("init", var_file="/tmp/vars.tfvars")
        assert "-var-file" not in cmd

    # -- Return type ---------------------------------------------------------

    @pytest.mark.parametrize(
        "action",
        ["init", "validate", "fmt", "plan", "show", "graph", "providers", "version"],
    )
    def test_returns_list_of_strings(self, action):
        """Every valid action should return a list of strings."""
        cmd = build_terraform_command(action)
        assert isinstance(cmd, list)
        assert all(isinstance(part, str) for part in cmd)


# ---------------------------------------------------------------------------
# 2. parse_text_plan_summary()
# ---------------------------------------------------------------------------


class TestParseTextPlanSummary:
    """Tests for the parse_text_plan_summary fallback parser."""

    def test_typical_plan_output(self):
        """Parse standard Terraform plan summary line."""
        stdout = "Plan: 3 to add, 1 to change, 2 to destroy."
        result = parse_text_plan_summary(stdout)
        assert result == {"add": 3, "change": 1, "destroy": 2}

    def test_no_changes(self):
        """Output with no matching summary returns all zeros."""
        stdout = "No changes. Your infrastructure matches the configuration."
        result = parse_text_plan_summary(stdout)
        assert result == {"add": 0, "change": 0, "destroy": 0}

    def test_only_add(self):
        """Parse output with only additions."""
        stdout = "Plan: 5 to add, 0 to change, 0 to destroy."
        result = parse_text_plan_summary(stdout)
        assert result == {"add": 5, "change": 0, "destroy": 0}

    def test_only_destroy(self):
        """Parse output with only destructions."""
        stdout = "Plan: 0 to add, 0 to change, 10 to destroy."
        result = parse_text_plan_summary(stdout)
        assert result == {"add": 0, "change": 0, "destroy": 10}

    def test_empty_string(self):
        """Empty stdout returns all zeros."""
        result = parse_text_plan_summary("")
        assert result == {"add": 0, "change": 0, "destroy": 0}

    def test_multiline_output_finds_summary(self):
        """Summary line embedded in multi-line output is still found."""
        stdout = (
            "Terraform will perform the following actions:\n"
            "\n"
            "  # aws_instance.web will be created\n"
            "\n"
            "Plan: 1 to add, 0 to change, 0 to destroy.\n"
            "\n"
            "Changes to Outputs:\n"
        )
        result = parse_text_plan_summary(stdout)
        assert result == {"add": 1, "change": 0, "destroy": 0}

    def test_large_numbers(self):
        """Large resource counts are parsed correctly."""
        stdout = "Plan: 100 to add, 50 to change, 25 to destroy."
        result = parse_text_plan_summary(stdout)
        assert result == {"add": 100, "change": 50, "destroy": 25}


# ---------------------------------------------------------------------------
# 3. get_controlled_env()
# ---------------------------------------------------------------------------


class TestGetControlledEnv:
    """Tests for the get_controlled_env function."""

    def test_forced_vars_always_present(self, clean_env):
        """FORCED_ENV_VARS must always appear in the controlled environment."""
        env = get_controlled_env()
        assert env["TF_IN_AUTOMATION"] == "true"
        assert env["TF_INPUT"] == "false"
        assert env["CHECKPOINT_DISABLE"] == "true"

    def test_allowed_vars_passed_through(self, monkeypatch):
        """Allowed environment variables from os.environ are included."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
        env = get_controlled_env()
        assert env["AWS_DEFAULT_REGION"] == "us-west-2"

    def test_disallowed_vars_excluded(self, monkeypatch):
        """Variables not in ALLOWED_ENV_VARS are excluded."""
        monkeypatch.setenv("SUPER_SECRET_TOKEN", "hunter2")
        env = get_controlled_env()
        assert "SUPER_SECRET_TOKEN" not in env

    def test_forced_vars_override_allowed(self, monkeypatch):
        """Forced variables override any existing values from the environment."""
        monkeypatch.setenv("TF_IN_AUTOMATION", "false")
        env = get_controlled_env()
        assert env["TF_IN_AUTOMATION"] == "true"

    def test_path_and_home_included(self, monkeypatch):
        """HOME and PATH (common allowed vars) are included when present."""
        monkeypatch.setenv("HOME", "/home/testuser")
        monkeypatch.setenv("PATH", "/usr/bin")
        env = get_controlled_env()
        assert env["HOME"] == "/home/testuser"
        assert env["PATH"] == "/usr/bin"

    def test_cloud_provider_vars_included(self, monkeypatch):
        """Cloud provider credentials are passed through when present."""
        monkeypatch.setenv("ARM_CLIENT_ID", "azure-id")
        monkeypatch.setenv("GOOGLE_PROJECT", "my-project")
        env = get_controlled_env()
        assert env["ARM_CLIENT_ID"] == "azure-id"
        assert env["GOOGLE_PROJECT"] == "my-project"

    def test_returns_dict(self, clean_env):
        """get_controlled_env returns a plain dict."""
        env = get_controlled_env()
        assert isinstance(env, dict)


# ---------------------------------------------------------------------------
# 4. parse_plan_output()
# ---------------------------------------------------------------------------


class TestParsePlanOutput:
    """Tests for the parse_plan_output function."""

    def test_nonexistent_path_returns_none(self, tmp_path):
        """A path with no tfplan file should return None."""
        result = parse_plan_output(str(tmp_path))
        assert result is None

    def test_nonexistent_directory_returns_none(self):
        """A completely non-existent directory should return None."""
        result = parse_plan_output("/nonexistent/path/that/does/not/exist")
        assert result is None

    @patch("terry_form_mcp.subprocess.run")
    def test_successful_plan_parse(self, mock_run, workspace_with_plan):
        """Valid plan JSON is parsed into summary and resource list."""
        plan_json = {
            "resource_changes": [
                {
                    "address": "aws_instance.web",
                    "type": "aws_instance",
                    "name": "web",
                    "change": {"actions": ["create"]},
                },
                {
                    "address": "aws_s3_bucket.data",
                    "type": "aws_s3_bucket",
                    "name": "data",
                    "change": {"actions": ["update"]},
                },
                {
                    "address": "aws_iam_role.old",
                    "type": "aws_iam_role",
                    "name": "old",
                    "change": {"actions": ["delete"]},
                },
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(plan_json),
            stderr="",
        )

        result = parse_plan_output(workspace_with_plan)

        assert result is not None
        assert result["plan_summary"]["add"] == 1
        assert result["plan_summary"]["change"] == 1
        assert result["plan_summary"]["destroy"] == 1
        assert len(result["resources"]) == 3

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_parse_nonzero_exit(self, mock_run, workspace_with_plan):
        """Non-zero exit code from terraform show returns None."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error reading plan file",
        )
        result = parse_plan_output(workspace_with_plan)
        assert result is None

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_parse_invalid_json(self, mock_run, workspace_with_plan):
        """Invalid JSON from terraform show returns None."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json {{{",
            stderr="",
        )
        result = parse_plan_output(workspace_with_plan)
        assert result is None

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_parse_timeout(self, mock_run, workspace_with_plan):
        """Timeout during terraform show returns None."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="terraform", timeout=60)
        result = parse_plan_output(workspace_with_plan)
        assert result is None

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_parse_empty_resource_changes(self, mock_run, workspace_with_plan):
        """Plan with no resource changes returns zero counts."""
        plan_json = {"resource_changes": []}
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(plan_json),
            stderr="",
        )
        result = parse_plan_output(workspace_with_plan)
        assert result is not None
        assert result["plan_summary"] == {"add": 0, "change": 0, "destroy": 0}
        assert result["resources"] == []

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_parse_multiple_actions_per_resource(self, mock_run, workspace_with_plan):
        """A resource with both delete and create (replace) is counted for both."""
        plan_json = {
            "resource_changes": [
                {
                    "address": "aws_instance.replaced",
                    "type": "aws_instance",
                    "name": "replaced",
                    "change": {"actions": ["delete", "create"]},
                },
            ]
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(plan_json),
            stderr="",
        )
        result = parse_plan_output(workspace_with_plan)
        assert result is not None
        assert result["plan_summary"]["add"] == 1
        assert result["plan_summary"]["destroy"] == 1

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_parse_calls_subprocess_with_correct_args(
        self, mock_run, workspace_with_plan
    ):
        """Verify subprocess.run is called with expected command and kwargs."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"resource_changes": []}),
            stderr="",
        )
        parse_plan_output(workspace_with_plan)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "terraform"
        assert cmd[1] == "show"
        assert "-json" in cmd
        assert call_args[1]["cwd"] == workspace_with_plan
        assert call_args[1]["timeout"] == 60


# ---------------------------------------------------------------------------
# 5. run_terraform()
# ---------------------------------------------------------------------------


class TestRunTerraform:
    """Tests for the run_terraform function."""

    # -- Path validation ----------------------------------------------------

    def test_nonexistent_path_returns_failure(self):
        """Non-existent workspace path returns failure without running subprocess."""
        result = run_terraform("/nonexistent/workspace/path", "init")
        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "does not exist" in result["stderr"]
        assert result["action"] == "init"

    def test_file_path_returns_failure(self, tmp_path):
        """A file (not a directory) as workspace returns failure."""
        file_path = tmp_path / "not_a_dir.tf"
        file_path.write_text("resource {}")
        result = run_terraform(str(file_path), "init")
        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "not a directory" in result["stderr"]

    # -- Successful execution -----------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_successful_init(self, mock_run, workspace):
        """Successful init returns success=True with exit_code=0."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Terraform has been successfully initialized!",
            stderr="",
        )
        result = run_terraform(workspace, "init")

        assert result["success"] is True
        assert result["exit_code"] == 0
        assert result["action"] == "init"
        assert "successfully initialized" in result["stdout"]
        assert isinstance(result["duration"], float)

    @patch("terry_form_mcp.subprocess.run")
    def test_successful_validate(self, mock_run, workspace):
        """Successful validate returns expected structure."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Success! The configuration is valid.",
            stderr="",
        )
        result = run_terraform(workspace, "validate")

        assert result["success"] is True
        assert result["action"] == "validate"

    @patch("terry_form_mcp.subprocess.run")
    def test_successful_fmt(self, mock_run, workspace):
        """Successful fmt returns expected structure."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        result = run_terraform(workspace, "fmt")

        assert result["success"] is True
        assert result["action"] == "fmt"

    # -- Failed execution ---------------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_failed_validate(self, mock_run, workspace):
        """Failed validate returns success=False with nonzero exit_code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Missing required argument",
        )
        result = run_terraform(workspace, "validate")

        assert result["success"] is False
        assert result["exit_code"] == 1
        assert "Missing required argument" in result["stderr"]

    # -- Invalid / destructive actions are blocked ----------------------------

    def test_apply_action_returns_failure(self, workspace):
        """apply is caught by the generic exception handler and returns failure."""
        result = run_terraform(workspace, "apply")
        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "Unsupported Terraform action" in result["stderr"]
        assert result["action"] == "apply"

    def test_destroy_action_returns_failure(self, workspace):
        """destroy is caught by the generic exception handler and returns failure."""
        result = run_terraform(workspace, "destroy")
        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "Unsupported Terraform action" in result["stderr"]
        assert result["action"] == "destroy"

    # -- Environment variables -----------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_env_vars_set_correctly(self, mock_run, workspace):
        """Subprocess is called with controlled environment containing forced vars."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        run_terraform(workspace, "init")

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        env = call_kwargs["env"]
        assert env["TF_IN_AUTOMATION"] == "true"
        assert env["TF_INPUT"] == "false"
        assert env["CHECKPOINT_DISABLE"] == "true"

    @patch("terry_form_mcp.subprocess.run")
    def test_subprocess_called_with_shell_false(self, mock_run, workspace):
        """Subprocess is called with a list command (shell=False by default)."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        run_terraform(workspace, "init")

        call_args = mock_run.call_args
        # First positional arg is the command list
        cmd = call_args[0][0]
        assert isinstance(cmd, list)
        # shell should not be True (default is False, or not passed)
        assert call_args[1].get("shell", False) is False

    @patch("terry_form_mcp.subprocess.run")
    def test_cwd_set_to_workspace(self, mock_run, workspace):
        """Subprocess runs in the specified workspace directory."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        run_terraform(workspace, "validate")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == workspace

    # -- Timeout handling ---------------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_timeout_returns_failure(self, mock_run, workspace):
        """TimeoutExpired is caught and returns a failure dict."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="terraform", timeout=300, output=b"partial output"
        )
        result = run_terraform(workspace, "plan")

        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"]
        assert result["action"] == "plan"

    @patch("terry_form_mcp.subprocess.run")
    def test_timeout_with_no_output(self, mock_run, workspace):
        """TimeoutExpired with None stdout is handled gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="terraform", timeout=300, output=None
        )
        result = run_terraform(workspace, "init")

        assert result["success"] is False
        assert result["stdout"] == ""

    @patch("terry_form_mcp.subprocess.run")
    def test_custom_timeout_from_env(self, mock_run, workspace, monkeypatch):
        """MAX_OPERATION_TIMEOUT environment variable controls the timeout."""
        monkeypatch.setenv("MAX_OPERATION_TIMEOUT", "60")
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        run_terraform(workspace, "init")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60

    @patch("terry_form_mcp.subprocess.run")
    def test_default_timeout_is_300(self, mock_run, workspace, monkeypatch):
        """Default timeout is 300 seconds when MAX_OPERATION_TIMEOUT is not set."""
        monkeypatch.delenv("MAX_OPERATION_TIMEOUT", raising=False)
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        run_terraform(workspace, "init")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 300

    # -- Error handling -----------------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_file_not_found_error(self, mock_run, workspace):
        """FileNotFoundError (missing terraform binary) returns failure."""
        mock_run.side_effect = FileNotFoundError("terraform not found")
        result = run_terraform(workspace, "init")

        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "Terraform binary not found" in result["stderr"]

    @patch("terry_form_mcp.subprocess.run")
    def test_permission_error(self, mock_run, workspace):
        """PermissionError is caught and returns failure with message."""
        mock_run.side_effect = PermissionError("Permission denied: /usr/bin/terraform")
        result = run_terraform(workspace, "init")

        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "Permission denied" in result["stderr"]

    @patch("terry_form_mcp.subprocess.run")
    def test_unexpected_exception(self, mock_run, workspace):
        """Unexpected exceptions are caught and return failure."""
        mock_run.side_effect = RuntimeError("Something unexpected")
        result = run_terraform(workspace, "init")

        assert result["success"] is False
        assert result["exit_code"] == -1
        assert "Unexpected error" in result["stderr"]

    # -- Response structure -------------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_response_contains_required_keys(self, mock_run, workspace):
        """Response dict always contains action, success, exit_code, stdout, stderr, duration."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ok", stderr=""
        )
        result = run_terraform(workspace, "init")

        required_keys = {"action", "success", "exit_code", "stdout", "stderr", "duration"}
        assert required_keys.issubset(result.keys())

    @patch("terry_form_mcp.subprocess.run")
    def test_duration_is_non_negative(self, mock_run, workspace):
        """Duration should be a non-negative float."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""
        )
        result = run_terraform(workspace, "init")
        assert result["duration"] >= 0.0

    # -- Plan action specifics -----------------------------------------------

    @patch("terry_form_mcp.parse_plan_output")
    @patch("terry_form_mcp.subprocess.run")
    def test_plan_includes_plan_summary(self, mock_run, mock_parse, workspace):
        """Plan action includes plan_summary when parse_plan_output succeeds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Plan: 2 to add, 0 to change, 0 to destroy.",
            stderr="",
        )
        mock_parse.return_value = {
            "plan_summary": {"add": 2, "change": 0, "destroy": 0},
            "resources": [
                {
                    "address": "aws_instance.a",
                    "type": "aws_instance",
                    "name": "a",
                    "actions": ["create"],
                },
                {
                    "address": "aws_instance.b",
                    "type": "aws_instance",
                    "name": "b",
                    "actions": ["create"],
                },
            ],
        }
        result = run_terraform(workspace, "plan")

        assert result["plan_summary"] == {"add": 2, "change": 0, "destroy": 0}
        assert len(result["resources"]) == 2

    @patch("terry_form_mcp.parse_plan_output")
    @patch("terry_form_mcp.subprocess.run")
    def test_plan_falls_back_to_text_parsing(self, mock_run, mock_parse, workspace):
        """Plan action falls back to text parsing when parse_plan_output returns None."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Plan: 1 to add, 0 to change, 0 to destroy.",
            stderr="",
        )
        mock_parse.return_value = None

        result = run_terraform(workspace, "plan")

        assert result["plan_summary"] == {"add": 1, "change": 0, "destroy": 0}
        assert "resources" not in result

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_with_vars_creates_var_file(self, mock_run, workspace):
        """Plan action with vars creates a temporary var file and cleans it up."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No changes.",
            stderr="",
        )
        # Patch parse_plan_output to avoid secondary subprocess call
        with patch.object(terry_form_mcp, "parse_plan_output", return_value=None):
            run_terraform(workspace, "plan", vars={"region": "us-east-1"})

        # Verify the command included -var-file
        call_args = mock_run.call_args[0][0]
        assert "-var-file" in call_args

    # -- Version action specifics --------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_version_parses_json_output(self, mock_run, workspace):
        """Version action parses JSON output into terraform_version field."""
        version_json = {
            "terraform_version": "1.12.0",
            "platform": "linux_amd64",
            "provider_selections": {"registry.terraform.io/hashicorp/aws": "5.0.0"},
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(version_json),
            stderr="",
        )
        result = run_terraform(workspace, "version")

        assert result["terraform_version"] == "1.12.0"
        assert result["platform"] == "linux_amd64"
        assert "registry.terraform.io/hashicorp/aws" in result["provider_selections"]

    @patch("terry_form_mcp.subprocess.run")
    def test_version_handles_invalid_json(self, mock_run, workspace):
        """Version action handles invalid JSON gracefully (no crash)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Terraform v1.12.0\non linux_amd64",
            stderr="",
        )
        result = run_terraform(workspace, "version")

        assert result["success"] is True
        # Should not have terraform_version key since JSON parsing failed
        assert "terraform_version" not in result

    # -- Show action specifics -----------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_show_parses_state_json(self, mock_run, workspace):
        """Show action includes parsed state when JSON output is valid."""
        state_json = {
            "format_version": "1.0",
            "terraform_version": "1.12.0",
            "values": {"root_module": {"resources": []}},
        }
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(state_json),
            stderr="",
        )
        result = run_terraform(workspace, "show")

        assert result["success"] is True
        assert result["state"]["format_version"] == "1.0"

    @patch("terry_form_mcp.subprocess.run")
    def test_show_handles_invalid_json(self, mock_run, workspace):
        """Show action handles invalid JSON gracefully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No state file found.",
            stderr="",
        )
        result = run_terraform(workspace, "show")

        assert result["success"] is True
        assert "state" not in result

    # -- Cleanup verification ------------------------------------------------

    @patch("terry_form_mcp.subprocess.run")
    def test_plan_file_cleaned_up_after_execution(self, mock_run, workspace):
        """The tfplan file is cleaned up in the finally block after plan execution."""
        # Create a tfplan file that should be cleaned up
        plan_file = Path(workspace) / "tfplan"
        plan_file.write_text("dummy plan")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="No changes.",
            stderr="",
        )
        with patch.object(terry_form_mcp, "parse_plan_output", return_value=None):
            run_terraform(workspace, "plan")

        # Plan file should have been cleaned up
        assert not plan_file.exists()


# ---------------------------------------------------------------------------
# 6. run_terraform_actions()
# ---------------------------------------------------------------------------


class TestRunTerraformActions:
    """Tests for the run_terraform_actions function."""

    @patch("terry_form_mcp.run_terraform")
    def test_single_action(self, mock_run_tf, workspace):
        """Single action returns a list with one result."""
        mock_run_tf.return_value = {
            "action": "init",
            "success": True,
            "exit_code": 0,
            "stdout": "Initialized.",
            "stderr": "",
            "duration": 1.0,
        }
        results = run_terraform_actions(workspace, ["init"])

        assert len(results) == 1
        assert results[0]["action"] == "init"
        assert results[0]["success"] is True

    @patch("terry_form_mcp.run_terraform")
    def test_multiple_actions_sequential(self, mock_run_tf, workspace):
        """Multiple actions are executed in order and all results returned."""
        mock_run_tf.side_effect = [
            {
                "action": "init",
                "success": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration": 1.0,
            },
            {
                "action": "validate",
                "success": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration": 0.5,
            },
            {
                "action": "plan",
                "success": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration": 2.0,
            },
        ]
        results = run_terraform_actions(workspace, ["init", "validate", "plan"])

        assert len(results) == 3
        assert results[0]["action"] == "init"
        assert results[1]["action"] == "validate"
        assert results[2]["action"] == "plan"

    @patch("terry_form_mcp.run_terraform")
    def test_stops_on_failure(self, mock_run_tf, workspace):
        """Execution stops after a non-fmt action fails."""
        mock_run_tf.side_effect = [
            {
                "action": "init",
                "success": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration": 1.0,
            },
            {
                "action": "validate",
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": "Error",
                "duration": 0.5,
            },
        ]
        results = run_terraform_actions(
            workspace, ["init", "validate", "plan"]
        )

        # Should stop after validate failure, plan never runs
        assert len(results) == 2
        assert results[1]["success"] is False
        assert mock_run_tf.call_count == 2

    @patch("terry_form_mcp.run_terraform")
    def test_fmt_failure_does_not_stop_execution(self, mock_run_tf, workspace):
        """fmt failure does not stop subsequent actions."""
        mock_run_tf.side_effect = [
            {
                "action": "fmt",
                "success": False,
                "exit_code": 3,
                "stdout": "main.tf\n",
                "stderr": "",
                "duration": 0.2,
            },
            {
                "action": "validate",
                "success": True,
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "duration": 0.5,
            },
        ]
        results = run_terraform_actions(workspace, ["fmt", "validate"])

        assert len(results) == 2
        assert results[0]["success"] is False
        assert results[1]["success"] is True

    @patch("terry_form_mcp.run_terraform")
    def test_vars_only_passed_to_plan(self, mock_run_tf, workspace):
        """Variables are only passed to the plan action, not to init or validate."""
        mock_run_tf.return_value = {
            "action": "init",
            "success": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "duration": 0.5,
        }
        my_vars = {"region": "us-east-1"}
        run_terraform_actions(workspace, ["init", "plan"], vars=my_vars)

        calls = mock_run_tf.call_args_list
        # init should be called with vars=None
        assert calls[0][0] == (workspace, "init", None)
        # plan should be called with vars=my_vars
        assert calls[1][0] == (workspace, "plan", my_vars)

    @patch("terry_form_mcp.run_terraform")
    def test_empty_actions_list(self, mock_run_tf, workspace):
        """Empty actions list returns empty results."""
        results = run_terraform_actions(workspace, [])
        assert results == []
        mock_run_tf.assert_not_called()

    @patch("terry_form_mcp.run_terraform")
    def test_returns_list_type(self, mock_run_tf, workspace):
        """run_terraform_actions always returns a list."""
        mock_run_tf.return_value = {
            "action": "init",
            "success": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "duration": 0.5,
        }
        results = run_terraform_actions(workspace, ["init"])
        assert isinstance(results, list)

    @patch("terry_form_mcp.run_terraform")
    def test_init_failure_prevents_plan(self, mock_run_tf, workspace):
        """A common pattern: init failure prevents plan from running."""
        mock_run_tf.return_value = {
            "action": "init",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "Failed to install providers",
            "duration": 3.0,
        }
        results = run_terraform_actions(workspace, ["init", "plan"])

        assert len(results) == 1
        assert results[0]["action"] == "init"
        assert results[0]["success"] is False


# ---------------------------------------------------------------------------
# 7. Module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Tests for module-level constants and their correctness."""

    def test_allowed_env_vars_is_set(self):
        """ALLOWED_ENV_VARS should be a set type."""
        assert isinstance(ALLOWED_ENV_VARS, set)

    def test_allowed_env_vars_contains_critical_vars(self):
        """ALLOWED_ENV_VARS includes HOME, PATH, and key cloud provider vars."""
        assert "HOME" in ALLOWED_ENV_VARS
        assert "PATH" in ALLOWED_ENV_VARS
        assert "AWS_ACCESS_KEY_ID" in ALLOWED_ENV_VARS
        assert "GOOGLE_CREDENTIALS" in ALLOWED_ENV_VARS
        assert "ARM_CLIENT_ID" in ALLOWED_ENV_VARS

    def test_forced_env_vars_is_dict(self):
        """FORCED_ENV_VARS should be a dict type."""
        assert isinstance(FORCED_ENV_VARS, dict)

    def test_forced_env_vars_contain_automation_flags(self):
        """FORCED_ENV_VARS should enforce automation mode."""
        assert FORCED_ENV_VARS["TF_IN_AUTOMATION"] == "true"
        assert FORCED_ENV_VARS["TF_INPUT"] == "false"
        assert FORCED_ENV_VARS["CHECKPOINT_DISABLE"] == "true"

    def test_no_sensitive_defaults_in_forced_vars(self):
        """FORCED_ENV_VARS should not contain credentials or secrets."""
        for key in FORCED_ENV_VARS:
            assert "SECRET" not in key.upper()
            assert "TOKEN" not in key.upper()
            assert "PASSWORD" not in key.upper()
