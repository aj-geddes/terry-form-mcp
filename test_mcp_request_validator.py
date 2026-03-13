#!/usr/bin/env python3
"""
Comprehensive tests for mcp_request_validator.py

Covers:
- Path safety validation (_is_safe_path)
- Input sanitization (_sanitize_params, _validate_terraform_vars)
- Rate limiting categories (via tool routing)
- JSON/schema validation (validate_request structure checks)
- The validate_request method and validate_mcp_request convenience function
- Terry, GitHub, TF Cloud, and extended terry tool validation
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from mcp_request_validator import MCPRequestValidator, validate_mcp_request


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def validator():
    """Create a validator with the default workspace root."""
    return MCPRequestValidator(workspace_root="/mnt/workspace")


@pytest.fixture
def validator_tmp(tmp_path):
    """Create a validator whose workspace root is a real temporary directory.

    Useful for tests that rely on Path.resolve() producing a real path.
    """
    return MCPRequestValidator(workspace_root=str(tmp_path))


# ---------------------------------------------------------------------------
# 1. Path Safety Validation (_is_safe_path)
# ---------------------------------------------------------------------------


class TestPathSafety:
    """Tests for the _is_safe_path method."""

    def test_relative_path_inside_workspace(self, validator_tmp):
        """A simple relative path should resolve inside the workspace."""
        assert validator_tmp._is_safe_path("modules/main.tf") is True

    def test_absolute_path_inside_workspace(self, validator_tmp, tmp_path):
        """An absolute path under the workspace root should be accepted."""
        safe = str(tmp_path / "project" / "main.tf")
        assert validator_tmp._is_safe_path(safe) is True

    def test_path_traversal_dot_dot(self, validator_tmp):
        """../../etc/passwd style traversal must be blocked."""
        assert validator_tmp._is_safe_path("../../etc/passwd") is False

    def test_path_traversal_absolute(self, validator_tmp):
        """/etc/passwd (absolute path outside workspace) must be blocked."""
        assert validator_tmp._is_safe_path("/etc/passwd") is False

    def test_path_traversal_mixed(self, validator_tmp):
        """A path that starts inside the workspace but traverses out must be blocked."""
        assert validator_tmp._is_safe_path("modules/../../etc/shadow") is False

    def test_path_traversal_encoded_dots(self, validator_tmp):
        """Paths with multiple .. components should be caught by resolve()."""
        assert validator_tmp._is_safe_path("a/b/c/../../../../etc/hosts") is False

    def test_github_protocol_prefix(self, validator):
        """Paths starting with github:// are always considered safe."""
        assert validator._is_safe_path("github://owner/repo") is True

    def test_workspace_protocol_prefix(self, validator):
        """Paths starting with workspace:// are always considered safe."""
        assert validator._is_safe_path("workspace://some/path") is True

    def test_empty_string_path(self, validator_tmp):
        """An empty string resolves to the workspace root itself, which is inside."""
        # Empty string -> workspace_root / "" -> workspace_root, which is valid
        assert validator_tmp._is_safe_path("") is True

    def test_dot_path(self, validator_tmp):
        """'.' resolves to the workspace root, which should be acceptable."""
        assert validator_tmp._is_safe_path(".") is True

    def test_absolute_root_slash(self, validator):
        """Just '/' should be blocked (outside /mnt/workspace)."""
        assert validator._is_safe_path("/") is False

    def test_path_with_null_byte(self, validator_tmp):
        """Paths containing null bytes should be rejected (ValueError from Path)."""
        # Path() raises ValueError for embedded NUL on most systems
        assert validator_tmp._is_safe_path("/mnt/workspace/\x00evil") is False

    def test_very_long_path(self, validator_tmp, tmp_path):
        """A very long but valid path should still pass if it resolves inside workspace."""
        long_component = "a" * 200
        long_path = str(tmp_path / long_component / "main.tf")
        assert validator_tmp._is_safe_path(long_path) is True

    def test_very_long_traversal_path(self, validator):
        """A very long traversal path should be blocked."""
        traversal = "../" * 100 + "etc/passwd"
        assert validator._is_safe_path(traversal) is False


# ---------------------------------------------------------------------------
# 2. Input Sanitization (_validate_terraform_vars, _sanitize_params)
# ---------------------------------------------------------------------------


class TestInputSanitization:
    """Tests for input sanitization and dangerous character detection."""

    def test_clean_variable_passes(self, validator):
        """Normal alphanumeric variable names and values should pass."""
        valid, msg = validator._validate_terraform_vars(
            {"region": "us-east-1", "instance_count": "3"}
        )
        assert valid is True
        assert msg == ""

    def test_variable_name_with_underscore_and_hyphen(self, validator):
        """Variable names with underscores and hyphens are valid."""
        valid, msg = validator._validate_terraform_vars(
            {"my-var": "value", "my_var": "value"}
        )
        assert valid is True

    def test_variable_name_with_special_chars_rejected(self, validator):
        """Variable names with special characters should be rejected."""
        valid, msg = validator._validate_terraform_vars({"var name!": "value"})
        assert valid is False
        assert "Invalid variable name" in msg

    def test_variable_value_with_shell_metachar_dollar(self, validator):
        """Dollar signs in values should be flagged as dangerous."""
        valid, msg = validator._validate_terraform_vars({"key": "$(rm -rf /)"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_backtick(self, validator):
        """Backtick injection attempts should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "`whoami`"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_semicolon(self, validator):
        """Semicolons that could chain commands should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "val; rm -rf /"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_pipe(self, validator):
        """Pipe characters should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "val | cat /etc/passwd"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_ampersand(self, validator):
        """Ampersand characters should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "val && evil"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_angle_brackets(self, validator):
        """Angle brackets (redirection) should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "> /dev/null"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_curly_braces(self, validator):
        """Curly braces should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "${evil}"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_parentheses(self, validator):
        """Parentheses should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "$(evil)"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_backslash(self, validator):
        """Backslash characters should be caught."""
        valid, msg = validator._validate_terraform_vars({"key": "a\\nb"})
        assert valid is False
        assert "dangerous characters" in msg

    def test_variable_value_with_quotes(self, validator):
        """Quotes (single and double) should be caught."""
        valid1, _ = validator._validate_terraform_vars({"k": "it's bad"})
        valid2, _ = validator._validate_terraform_vars({"k": 'say "hello"'})
        assert valid1 is False
        assert valid2 is False

    def test_integer_variable_value(self, validator):
        """Integer values should be stringified and pass if clean."""
        valid, msg = validator._validate_terraform_vars({"count": 5})
        assert valid is True

    def test_empty_vars_dict(self, validator):
        """An empty variables dict is fine (no vars to check)."""
        valid, msg = validator._validate_terraform_vars({})
        assert valid is True

    def test_sanitize_params_resolves_relative_path(self, validator_tmp, tmp_path):
        """_sanitize_params should resolve relative paths to absolute within workspace."""
        result = validator_tmp._sanitize_params({"path": "modules/main.tf"})
        assert result["path"] == str((tmp_path / "modules" / "main.tf").resolve())

    def test_sanitize_params_resolves_absolute_path(self, validator_tmp, tmp_path):
        """_sanitize_params should resolve absolute workspace paths."""
        abs_path = str(tmp_path / "main.tf")
        result = validator_tmp._sanitize_params({"path": abs_path})
        assert result["path"] == str(Path(abs_path).resolve())

    def test_sanitize_params_preserves_github_protocol(self, validator):
        """_sanitize_params should not modify github:// paths."""
        result = validator._sanitize_params({"path": "github://owner/repo"})
        assert result["path"] == "github://owner/repo"

    def test_sanitize_params_preserves_workspace_protocol(self, validator):
        """_sanitize_params should not modify workspace:// paths."""
        result = validator._sanitize_params({"path": "workspace://dir"})
        assert result["path"] == "workspace://dir"

    def test_sanitize_params_no_path_key(self, validator):
        """_sanitize_params should return params unchanged when no path key exists."""
        params = {"action": "init", "vars": {"a": "b"}}
        result = validator._sanitize_params(params)
        assert result == params

    def test_sanitize_params_unsafe_path_kept(self, validator):
        """If the path is unsafe, _sanitize_params skips resolution and keeps original."""
        result = validator._sanitize_params({"path": "/etc/passwd"})
        # Unsafe path -> _is_safe_path returns False -> original kept
        assert result["path"] == "/etc/passwd"


# ---------------------------------------------------------------------------
# 3. Validate Request — Structure and Routing
# ---------------------------------------------------------------------------


class TestValidateRequestStructure:
    """Tests for the top-level validate_request method's structure checks."""

    def test_non_dict_request_rejected(self, validator):
        """A request that is not a dict should be rejected."""
        valid, msg = validator.validate_request("not a dict")
        assert valid is False
        assert "must be a dictionary" in msg

    def test_non_dict_request_list(self, validator):
        """A list request should be rejected."""
        valid, msg = validator.validate_request([1, 2, 3])
        assert valid is False
        assert "must be a dictionary" in msg

    def test_non_tool_call_method_passes(self, validator):
        """Requests with method != 'tools/call' should pass through."""
        valid, msg = validator.validate_request({"method": "resources/list"})
        assert valid is True
        assert msg == ""

    def test_missing_method_passes(self, validator):
        """A request with no method key defaults to '' and passes (not tools/call)."""
        valid, msg = validator.validate_request({})
        assert valid is True

    def test_params_must_be_dict(self, validator):
        """If params is not a dict, the request should be rejected."""
        valid, msg = validator.validate_request(
            {"method": "tools/call", "params": "bad"}
        )
        assert valid is False
        assert "Params must be a dictionary" in msg

    def test_unknown_tool_passes(self, validator):
        """Tools not matching any known prefix should pass through."""
        valid, msg = validator.validate_request(
            {
                "method": "tools/call",
                "params": {"name": "some_unknown_tool", "arguments": {}},
            }
        )
        assert valid is True

    def test_validation_exception_returns_false(self, validator):
        """If an unexpected exception occurs during validation, it returns False."""
        # Force an exception by patching _validate_terry_request
        with patch.object(
            validator,
            "_validate_terry_request",
            side_effect=RuntimeError("boom"),
        ):
            valid, msg = validator.validate_request(
                {
                    "method": "tools/call",
                    "params": {"name": "terry", "arguments": {}},
                }
            )
            assert valid is False
            assert "Validation error" in msg


# ---------------------------------------------------------------------------
# 4. Terry Tool Validation (_validate_terry_request)
# ---------------------------------------------------------------------------


class TestTerryToolValidation:
    """Tests for the core 'terry' tool validation."""

    def _make_request(self, arguments):
        return {
            "method": "tools/call",
            "params": {"name": "terry", "arguments": arguments},
        }

    def test_valid_init_request(self, validator_tmp, tmp_path):
        """A well-formed init request should pass."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": ["init"]}
            )
        )
        assert valid is True
        assert msg == ""

    def test_valid_multiple_actions(self, validator_tmp, tmp_path):
        """Multiple allowed actions in a single request should pass."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {
                    "path": str(tmp_path / "project"),
                    "actions": ["init", "validate", "plan"],
                }
            )
        )
        assert valid is True

    def test_missing_path_rejected(self, validator):
        """A terry request with no path should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request({"actions": ["init"]})
        )
        assert valid is False
        assert "Path is required" in msg

    def test_empty_path_rejected(self, validator):
        """A terry request with empty path string should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request({"path": "", "actions": ["init"]})
        )
        assert valid is False
        assert "Path is required" in msg

    def test_path_traversal_rejected(self, validator):
        """A terry request with path traversal should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request({"path": "../../etc/passwd", "actions": ["init"]})
        )
        assert valid is False
        assert "outside workspace" in msg

    def test_apply_action_blocked(self, validator_tmp, tmp_path):
        """The 'apply' action must be blocked."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": ["apply"]}
            )
        )
        assert valid is False
        assert "blocked" in msg

    def test_destroy_action_blocked(self, validator_tmp, tmp_path):
        """The 'destroy' action must be blocked."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": ["destroy"]}
            )
        )
        assert valid is False
        assert "blocked" in msg

    def test_import_action_blocked(self, validator_tmp, tmp_path):
        """The 'import' action must be blocked."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": ["import"]}
            )
        )
        assert valid is False
        assert "blocked" in msg

    def test_taint_action_blocked(self, validator_tmp, tmp_path):
        """The 'taint' action must be blocked."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": ["taint"]}
            )
        )
        assert valid is False
        assert "blocked" in msg

    def test_untaint_action_blocked(self, validator_tmp, tmp_path):
        """The 'untaint' action must be blocked."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": ["untaint"]}
            )
        )
        assert valid is False
        assert "blocked" in msg

    def test_unknown_action_rejected(self, validator_tmp, tmp_path):
        """Actions not in the allowed set should be rejected."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": ["bogus"]}
            )
        )
        assert valid is False
        assert "Unknown action" in msg

    def test_actions_not_a_list_rejected(self, validator_tmp, tmp_path):
        """Actions must be a list, not a string or other type."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": "init"}
            )
        )
        assert valid is False
        assert "Actions must be a list" in msg

    def test_vars_not_a_dict_rejected(self, validator_tmp, tmp_path):
        """Variables must be a dict if provided."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {
                    "path": str(tmp_path / "project"),
                    "actions": ["init"],
                    "vars": "not_a_dict",
                }
            )
        )
        assert valid is False
        assert "Variables must be a dictionary" in msg

    def test_vars_with_dangerous_value_rejected(self, validator_tmp, tmp_path):
        """Dangerous characters in variable values should be caught."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {
                    "path": str(tmp_path / "project"),
                    "actions": ["init"],
                    "vars": {"region": "$(whoami)"},
                }
            )
        )
        assert valid is False
        assert "dangerous characters" in msg

    def test_auto_approve_blocked(self, validator_tmp, tmp_path):
        """The auto_approve flag must be blocked."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {
                    "path": str(tmp_path / "project"),
                    "actions": ["init"],
                    "auto_approve": True,
                }
            )
        )
        assert valid is False
        assert "auto_approve is blocked" in msg

    def test_destroy_flag_blocked(self, validator_tmp, tmp_path):
        """The destroy flag must be blocked."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {
                    "path": str(tmp_path / "project"),
                    "actions": ["plan"],
                    "destroy": True,
                }
            )
        )
        assert valid is False
        assert "destroy is blocked" in msg

    def test_auto_approve_false_allowed(self, validator_tmp, tmp_path):
        """auto_approve=False should not trigger the block."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {
                    "path": str(tmp_path / "project"),
                    "actions": ["init"],
                    "auto_approve": False,
                }
            )
        )
        assert valid is True

    def test_empty_actions_list_allowed(self, validator_tmp, tmp_path):
        """An empty actions list should pass (no invalid actions to check)."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {"path": str(tmp_path / "project"), "actions": []}
            )
        )
        assert valid is True

    def test_all_allowed_actions(self, validator_tmp, tmp_path):
        """All explicitly allowed actions should pass individually."""
        for action in [
            "init",
            "validate",
            "fmt",
            "plan",
            "show",
            "graph",
            "providers",
            "version",
        ]:
            valid, msg = validator_tmp.validate_request(
                self._make_request(
                    {"path": str(tmp_path / "project"), "actions": [action]}
                )
            )
            assert valid is True, f"Action '{action}' should be allowed but got: {msg}"

    def test_empty_vars_dict_allowed(self, validator_tmp, tmp_path):
        """An empty vars dict should pass."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                {
                    "path": str(tmp_path / "project"),
                    "actions": ["init"],
                    "vars": {},
                }
            )
        )
        assert valid is True


# ---------------------------------------------------------------------------
# 5. GitHub Tool Validation (_validate_github_request)
# ---------------------------------------------------------------------------


class TestGitHubToolValidation:
    """Tests for GitHub tool request validation."""

    def _make_request(self, tool_name, arguments):
        return {
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

    def test_valid_github_request(self, validator):
        """A GitHub request with valid owner/repo should pass."""
        valid, msg = validator.validate_request(
            self._make_request(
                "github_clone_repo", {"owner": "hashicorp", "repo": "terraform"}
            )
        )
        assert valid is True

    def test_valid_repo_with_dots(self, validator):
        """Repository names with dots (e.g., terraform.js) should be allowed."""
        valid, msg = validator.validate_request(
            self._make_request(
                "github_clone_repo", {"owner": "user", "repo": "my-repo.js"}
            )
        )
        assert valid is True

    def test_invalid_owner_name(self, validator):
        """Owner names with special characters should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "github_clone_repo",
                {"owner": "bad owner!", "repo": "terraform"},
            )
        )
        assert valid is False
        assert "Invalid repository owner name" in msg

    def test_invalid_repo_name(self, validator):
        """Repo names with invalid characters should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "github_clone_repo",
                {"owner": "hashicorp", "repo": "bad repo name!"},
            )
        )
        assert valid is False
        assert "Invalid repository name" in msg

    def test_owner_with_path_traversal(self, validator):
        """Owner names attempting path traversal should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "github_clone_repo",
                {"owner": "../../../etc", "repo": "passwd"},
            )
        )
        assert valid is False

    def test_cleanup_repos_valid_days(self, validator):
        """github_cleanup_repos with a valid days_old parameter should pass."""
        valid, msg = validator.validate_request(
            self._make_request("github_cleanup_repos", {"days_old": 30})
        )
        assert valid is True

    def test_cleanup_repos_negative_days(self, validator):
        """github_cleanup_repos with negative days_old should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request("github_cleanup_repos", {"days_old": -1})
        )
        assert valid is False
        assert "Invalid days_old" in msg

    def test_cleanup_repos_excessive_days(self, validator):
        """github_cleanup_repos with days_old > 365 should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request("github_cleanup_repos", {"days_old": 500})
        )
        assert valid is False
        assert "Invalid days_old" in msg

    def test_cleanup_repos_non_int_days(self, validator):
        """github_cleanup_repos with a string days_old should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request("github_cleanup_repos", {"days_old": "thirty"})
        )
        assert valid is False
        assert "Invalid days_old" in msg

    def test_cleanup_repos_zero_days(self, validator):
        """github_cleanup_repos with days_old=0 should pass (0 is >= 0 and <= 365)."""
        valid, msg = validator.validate_request(
            self._make_request("github_cleanup_repos", {"days_old": 0})
        )
        assert valid is True

    def test_cleanup_repos_boundary_365(self, validator):
        """github_cleanup_repos with days_old=365 should pass."""
        valid, msg = validator.validate_request(
            self._make_request("github_cleanup_repos", {"days_old": 365})
        )
        assert valid is True

    def test_empty_owner_and_repo_passes(self, validator):
        """Missing or empty owner/repo should pass (the regex check is conditional)."""
        valid, msg = validator.validate_request(
            self._make_request("github_list_repos", {})
        )
        assert valid is True


# ---------------------------------------------------------------------------
# 6. Terraform Cloud Tool Validation (_validate_tf_cloud_request)
# ---------------------------------------------------------------------------


class TestTFCloudToolValidation:
    """Tests for Terraform Cloud tool request validation."""

    def _make_request(self, tool_name, arguments):
        return {
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

    def test_valid_tf_cloud_request(self, validator):
        """A valid TF Cloud request with clean org and workspace should pass."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "my-org", "workspace": "staging"},
            )
        )
        assert valid is True

    def test_invalid_organization_name(self, validator):
        """Organization names with special characters should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "my org!", "workspace": "staging"},
            )
        )
        assert valid is False
        assert "Invalid organization name" in msg

    def test_invalid_workspace_name(self, validator):
        """Workspace names with special characters should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "my-org", "workspace": "bad workspace!"},
            )
        )
        assert valid is False
        assert "Invalid workspace name" in msg

    def test_valid_limit_parameter(self, validator):
        """A limit parameter within 1-100 should pass."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "org", "limit": 50},
            )
        )
        assert valid is True

    def test_limit_zero_rejected(self, validator):
        """limit=0 is out of range (minimum is 1) and should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "org", "limit": 0},
            )
        )
        assert valid is False
        assert "Invalid limit" in msg

    def test_limit_over_100_rejected(self, validator):
        """limit > 100 should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "org", "limit": 101},
            )
        )
        assert valid is False
        assert "Invalid limit" in msg

    def test_limit_negative_rejected(self, validator):
        """Negative limit should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "org", "limit": -5},
            )
        )
        assert valid is False
        assert "Invalid limit" in msg

    def test_limit_non_integer_rejected(self, validator):
        """Non-integer limit should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "org", "limit": "ten"},
            )
        )
        assert valid is False
        assert "Invalid limit" in msg

    def test_limit_boundary_1(self, validator):
        """limit=1 is the minimum valid value."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "org", "limit": 1},
            )
        )
        assert valid is True

    def test_limit_boundary_100(self, validator):
        """limit=100 is the maximum valid value."""
        valid, msg = validator.validate_request(
            self._make_request(
                "tf_cloud_list_workspaces",
                {"organization": "org", "limit": 100},
            )
        )
        assert valid is True

    def test_empty_org_and_workspace_passes(self, validator):
        """Missing org/workspace should pass (regex check is conditional on non-empty)."""
        valid, msg = validator.validate_request(
            self._make_request("tf_cloud_get_runs", {})
        )
        assert valid is True


# ---------------------------------------------------------------------------
# 7. Extended Terry Tool Validation (_validate_terry_extended_request)
# ---------------------------------------------------------------------------


class TestTerryExtendedToolValidation:
    """Tests for extended terry_* tool validation."""

    def _make_request(self, tool_name, arguments):
        return {
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

    def test_valid_file_path(self, validator_tmp, tmp_path):
        """An extended tool with a safe file_path should pass."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                "terry_file_read",
                {"file_path": str(tmp_path / "main.tf")},
            )
        )
        assert valid is True

    def test_valid_path_key(self, validator_tmp, tmp_path):
        """An extended tool with a safe 'path' key should pass."""
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                "terry_workspace_list", {"path": str(tmp_path / "project")}
            )
        )
        assert valid is True

    def test_file_path_traversal_rejected(self, validator):
        """An extended tool with path traversal in file_path should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "terry_file_read", {"file_path": "../../etc/passwd"}
            )
        )
        assert valid is False
        assert "outside workspace" in msg

    def test_path_traversal_rejected(self, validator):
        """An extended tool with path traversal in 'path' should be rejected."""
        valid, msg = validator.validate_request(
            self._make_request(
                "terry_analyze", {"path": "/etc/shadow"}
            )
        )
        assert valid is False
        assert "outside workspace" in msg

    def test_no_path_arguments_passes(self, validator):
        """An extended tool with no path arguments should pass."""
        valid, msg = validator.validate_request(
            self._make_request("terry_recommendations", {"category": "security"})
        )
        assert valid is True

    def test_file_path_takes_precedence_over_path(self, validator_tmp, tmp_path):
        """When both file_path and path are present, file_path is used first.

        The code does `arguments.get('file_path') or arguments.get('path')`.
        If file_path is truthy, it's checked. If file_path is empty/None, path is checked.
        """
        # file_path is valid, path is irrelevant
        valid, msg = validator_tmp.validate_request(
            self._make_request(
                "terry_file_read",
                {
                    "file_path": str(tmp_path / "ok.tf"),
                    "path": "/etc/shadow",
                },
            )
        )
        assert valid is True

    def test_empty_file_path_falls_back_to_path(self, validator):
        """If file_path is empty, the validator falls back to the 'path' key."""
        valid, msg = validator.validate_request(
            self._make_request(
                "terry_file_read",
                {"file_path": "", "path": "/etc/shadow"},
            )
        )
        assert valid is False
        assert "outside workspace" in msg


# ---------------------------------------------------------------------------
# 8. Convenience Function (validate_mcp_request)
# ---------------------------------------------------------------------------


class TestConvenienceFunction:
    """Tests for the module-level validate_mcp_request function."""

    def test_valid_request(self, tmp_path):
        """The convenience function should accept valid requests."""
        valid, msg = validate_mcp_request(
            {
                "method": "tools/call",
                "params": {
                    "name": "terry",
                    "arguments": {
                        "path": str(tmp_path / "project"),
                        "actions": ["init"],
                    },
                },
            },
            workspace_root=str(tmp_path),
        )
        assert valid is True

    def test_invalid_request(self):
        """The convenience function should reject invalid requests."""
        valid, msg = validate_mcp_request("not a dict")
        assert valid is False

    def test_custom_workspace_root(self, tmp_path):
        """The convenience function should accept a custom workspace root."""
        project_dir = tmp_path / "custom"
        project_dir.mkdir()
        valid, msg = validate_mcp_request(
            {
                "method": "tools/call",
                "params": {
                    "name": "terry",
                    "arguments": {
                        "path": str(project_dir / "main.tf"),
                        "actions": ["validate"],
                    },
                },
            },
            workspace_root=str(tmp_path / "custom"),
        )
        assert valid is True

    def test_path_outside_custom_workspace(self, tmp_path):
        """Paths outside the custom workspace should be rejected."""
        valid, msg = validate_mcp_request(
            {
                "method": "tools/call",
                "params": {
                    "name": "terry",
                    "arguments": {
                        "path": "/etc/passwd",
                        "actions": ["init"],
                    },
                },
            },
            workspace_root=str(tmp_path),
        )
        assert valid is False


# ---------------------------------------------------------------------------
# 9. Dangerous Characters Pattern Coverage
# ---------------------------------------------------------------------------


class TestDangerousCharactersPattern:
    """Exhaustive tests for the dangerous_chars_pattern regex."""

    @pytest.mark.parametrize(
        "char,description",
        [
            ("$", "dollar sign"),
            ("`", "backtick"),
            ("\\", "backslash"),
            ('"', "double quote"),
            ("'", "single quote"),
            (";", "semicolon"),
            ("|", "pipe"),
            ("&", "ampersand"),
            (">", "greater than"),
            ("<", "less than"),
            ("(", "open paren"),
            (")", "close paren"),
            ("{", "open brace"),
            ("}", "close brace"),
        ],
    )
    def test_individual_dangerous_char(self, validator, char, description):
        """Each dangerous character should be detected individually."""
        assert validator.dangerous_chars_pattern.search(
            f"value{char}here"
        ), f"{description} ({char!r}) should be detected as dangerous"

    @pytest.mark.parametrize(
        "safe_value",
        [
            "us-east-1",
            "t2.micro",
            "my_value",
            "192.168.1.0/24",
            "hello world",
            "123",
            "true",
            "arn:aws:iam::123456:role/MyRole",  # colons and slashes are allowed
            "https://example.com",  # colons and slashes are allowed
        ],
    )
    def test_safe_values_not_flagged(self, validator, safe_value):
        """Values without dangerous characters should not be flagged."""
        assert not validator.dangerous_chars_pattern.search(
            safe_value
        ), f"{safe_value!r} should NOT be flagged as dangerous"


# ---------------------------------------------------------------------------
# 10. Valid Name Pattern Coverage
# ---------------------------------------------------------------------------


class TestValidNamePattern:
    """Tests for the valid_name_pattern used for owner/org/workspace names."""

    @pytest.mark.parametrize(
        "name",
        ["hashicorp", "my-org", "my_org", "Org123", "a", "A-B_C-1"],
    )
    def test_valid_names(self, validator, name):
        """Names with alphanumeric chars, hyphens, and underscores should match."""
        assert validator.valid_name_pattern.match(name)

    @pytest.mark.parametrize(
        "name",
        ["", "bad name", "bad/name", "bad.name", "bad@name", "bad!name", " leading"],
    )
    def test_invalid_names(self, validator, name):
        """Names with spaces, dots, slashes, or other specials should not match."""
        assert not validator.valid_name_pattern.match(name)


# ---------------------------------------------------------------------------
# 11. Tool Routing
# ---------------------------------------------------------------------------


class TestToolRouting:
    """Verify that validate_request routes to the correct sub-validator."""

    def test_routes_to_terry(self, validator):
        """Tool name 'terry' should route to _validate_terry_request."""
        with patch.object(
            validator, "_validate_terry_request", return_value=(True, "")
        ) as mock:
            validator.validate_request(
                {
                    "method": "tools/call",
                    "params": {"name": "terry", "arguments": {"path": "/mnt/workspace"}},
                }
            )
            mock.assert_called_once_with({"path": "/mnt/workspace"})

    def test_routes_to_github(self, validator):
        """Tool names starting with 'github_' should route to _validate_github_request."""
        with patch.object(
            validator, "_validate_github_request", return_value=(True, "")
        ) as mock:
            validator.validate_request(
                {
                    "method": "tools/call",
                    "params": {
                        "name": "github_clone_repo",
                        "arguments": {"owner": "x"},
                    },
                }
            )
            mock.assert_called_once_with("github_clone_repo", {"owner": "x"})

    def test_routes_to_tf_cloud(self, validator):
        """Tool names starting with 'tf_cloud_' should route to _validate_tf_cloud_request."""
        with patch.object(
            validator, "_validate_tf_cloud_request", return_value=(True, "")
        ) as mock:
            validator.validate_request(
                {
                    "method": "tools/call",
                    "params": {
                        "name": "tf_cloud_list_workspaces",
                        "arguments": {"organization": "o"},
                    },
                }
            )
            mock.assert_called_once_with(
                "tf_cloud_list_workspaces", {"organization": "o"}
            )

    def test_routes_to_terry_extended(self, validator):
        """Tool names starting with 'terry_' should route to _validate_terry_extended_request."""
        with patch.object(
            validator, "_validate_terry_extended_request", return_value=(True, "")
        ) as mock:
            validator.validate_request(
                {
                    "method": "tools/call",
                    "params": {
                        "name": "terry_file_read",
                        "arguments": {"file_path": "/mnt/workspace/main.tf"},
                    },
                }
            )
            mock.assert_called_once_with(
                "terry_file_read",
                {"file_path": "/mnt/workspace/main.tf"},
            )
