#!/usr/bin/env python3
"""
Business logic tests for all MCP tool handlers in server_enhanced_with_lsp.py.

Covers tool bodies (not infrastructure):
- Core Terraform tools: terry, terry_workspace_list, terry_workspace_info,
  terry_workspace_setup
- LSP tools: terraform_validate_lsp, terraform_hover, terraform_complete,
  terraform_format_lsp, terraform_lsp_status
- Diagnostic/Analysis tools: terry_analyze, terry_security_scan,
  terry_recommendations
- Environment tools: terry_version, terry_environment_check
- Other tools: terry_lsp_init, terry_lsp_debug, terry_file_check,
  health_live, health_ready, api_metrics
- GitHub tools: github_clone_repo, github_list_terraform_files,
  github_get_terraform_config, github_prepare_workspace

NOTE: tf_cloud_* tools are excluded — they have been removed from the server.
"""

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import isolation — mirrors the pattern in test_server_enhanced.py.
# The server module has heavy import-time side effects (FastMCP creation,
# importlib.import_module calls, etc.). Stub everything before importing.
# ---------------------------------------------------------------------------

_STUBBED_NAMES = (
    "fastmcp",
    "terraform_lsp_client",
    "terry-form-mcp",
    "mcp_request_validator",
    "github_app_auth",
    "github_repo_handler",
    "frontend",
    "frontend.config_manager",
    "frontend.schemas",
    "frontend.routes",
)
_saved_modules = {name: sys.modules.get(name) for name in _STUBBED_NAMES}

# -- fastmcp stub ----------------------------------------------------------
_fake_fastmcp_mod = types.ModuleType("fastmcp")


class _StubFastMCP:
    def __init__(self, *args, **kwargs):
        self._tools = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn

        return decorator


_fake_fastmcp_mod.FastMCP = _StubFastMCP  # type: ignore[attr-defined]
sys.modules["fastmcp"] = _fake_fastmcp_mod

# -- terraform_lsp_client stub ---------------------------------------------
_lsp_stub = types.ModuleType("terraform_lsp_client")
_lsp_stub._lsp_client = None  # type: ignore[attr-defined]
_lsp_stub.get_lsp_client = AsyncMock()  # type: ignore[attr-defined]
sys.modules["terraform_lsp_client"] = _lsp_stub

# -- terry-form-mcp stub ---------------------------------------------------
_terry_stub = types.ModuleType("terry-form-mcp")
_terry_stub.run_terraform = MagicMock(return_value={})  # type: ignore[attr-defined]
sys.modules["terry-form-mcp"] = _terry_stub

# -- mcp_request_validator stub --------------------------------------------
_validator_stub = types.ModuleType("mcp_request_validator")


class _StubValidator:
    def validate_request(self, request):
        return True, None


_validator_stub.MCPRequestValidator = _StubValidator  # type: ignore[attr-defined]
sys.modules["mcp_request_validator"] = _validator_stub

# -- github_app_auth stub --------------------------------------------------
_gh_auth_stub = types.ModuleType("github_app_auth")


class _StubGitHubAppConfig:
    @classmethod
    def from_env(cls):
        raise ValueError("GITHUB_APP_ID not set")


class _StubGitHubAppAuth:
    def __init__(self, config):
        pass


_gh_auth_stub.GitHubAppConfig = _StubGitHubAppConfig  # type: ignore[attr-defined]
_gh_auth_stub.GitHubAppAuth = _StubGitHubAppAuth  # type: ignore[attr-defined]
sys.modules["github_app_auth"] = _gh_auth_stub

# -- github_repo_handler stub ----------------------------------------------
_gh_handler_stub = types.ModuleType("github_repo_handler")


class _StubGitHubRepoHandler:
    pass


_gh_handler_stub.GitHubRepoHandler = _StubGitHubRepoHandler  # type: ignore[attr-defined]
sys.modules["github_repo_handler"] = _gh_handler_stub

# -- frontend stubs --------------------------------------------------------
for _mod_name in ("frontend", "frontend.config_manager", "frontend.schemas", "frontend.routes"):
    _mod = types.ModuleType(_mod_name)
    sys.modules[_mod_name] = _mod

# -- Disable frontend to avoid config_manager import ----------------------
import os as _os
_os.environ["TERRY_DISABLE_FRONTEND"] = "true"

# Now import the server module under test
import server_enhanced_with_lsp as _srv  # noqa: E402

# Restore original sys.modules so stubs don't leak into other test modules
for _name in _STUBBED_NAMES:
    _orig = _saved_modules[_name]
    if _orig is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _orig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run an async coroutine synchronously inside tests."""
    return asyncio.run(coro)


def _inner(fn):
    """Return the unwrapped inner function, bypassing the validate_request
    decorator (and its rate limiter / auth side-effects).

    functools.wraps sets __wrapped__ on the wrapper to point at the original
    function, so we can recover it here.  If a function has no __wrapped__
    attribute it is returned unchanged.
    """
    return getattr(fn, "__wrapped__", fn)


WORKSPACE = _srv.WORKSPACE_ROOT  # "/mnt/workspace" or override


# ---------------------------------------------------------------------------
# 1. terry() — core Terraform execution
# ---------------------------------------------------------------------------


class TestTerry:
    """Tests for the terry() tool handler."""

    def test_defaults_to_plan_action(self):
        """When actions is not supplied the handler defaults to ['plan']."""
        mock_run = MagicMock(return_value={"status": "ok"})
        with patch.object(_srv.terry_form, "run_terraform", mock_run):
            result = _inner(_srv.terry)(path="myproject")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][1] == "plan"

    def test_single_action_passed_correctly(self):
        """A single named action is forwarded to run_terraform."""
        mock_run = MagicMock(return_value={"status": "ok"})
        with patch.object(_srv.terry_form, "run_terraform", mock_run):
            result = _inner(_srv.terry)(path="myproject", actions=["validate"])

        mock_run.assert_called_once()
        assert mock_run.call_args[0][1] == "validate"

    def test_multiple_actions_each_called(self):
        """Multiple actions each produce a separate run_terraform call."""
        mock_run = MagicMock(return_value={"status": "ok"})
        with patch.object(_srv.terry_form, "run_terraform", mock_run):
            result = _inner(_srv.terry)(path="myproject", actions=["init", "validate", "plan"])

        assert mock_run.call_count == 3
        actions_called = [call[0][1] for call in mock_run.call_args_list]
        assert actions_called == ["init", "validate", "plan"]

    def test_tf_vars_passed_only_to_plan(self):
        """tf_vars are forwarded to run_terraform only for the 'plan' action."""
        mock_run = MagicMock(return_value={})
        tf_vars = {"env": "prod"}
        with patch.object(_srv.terry_form, "run_terraform", mock_run):
            _inner(_srv.terry)(path="myproject", actions=["init", "plan"], tf_vars=tf_vars)

        calls = mock_run.call_args_list
        # init call — tf_vars argument should be None
        assert calls[0][0][2] is None
        # plan call — tf_vars argument should equal tf_vars
        assert calls[1][0][2] == tf_vars

    def test_results_returned_in_list(self):
        """Each action's result is collected and returned under 'terry-results'."""
        mock_run = MagicMock(return_value={"output": "ok"})
        with patch.object(_srv.terry_form, "run_terraform", mock_run):
            result = _inner(_srv.terry)(path="myproject", actions=["plan", "validate"])

        assert "terry-results" in result
        assert len(result["terry-results"]) == 2

    def test_empty_actions_list_returns_empty_results(self):
        """An explicitly empty actions list produces no run_terraform calls."""
        mock_run = MagicMock(return_value={})
        with patch.object(_srv.terry_form, "run_terraform", mock_run):
            result = _inner(_srv.terry)(path="myproject", actions=[])

        mock_run.assert_not_called()
        assert result["terry-results"] == []

    def test_full_path_constructed_from_workspace_root(self):
        """The full path passed to run_terraform is WORKSPACE_ROOT / path."""
        mock_run = MagicMock(return_value={})
        with patch.object(_srv.terry_form, "run_terraform", mock_run):
            _inner(_srv.terry)(path="subdir/project", actions=["plan"])

        expected_path = f"{WORKSPACE}/subdir/project"
        assert mock_run.call_args[0][0] == expected_path


# ---------------------------------------------------------------------------
# 2. terry_workspace_list()
# ---------------------------------------------------------------------------


class TestTerryWorkspaceList:
    """Tests for terry_workspace_list()."""

    def test_empty_workspace_returns_empty_list(self, tmp_path):
        """When workspace has no .tf files, workspaces list is empty."""
        with patch.object(_srv, "WORKSPACE_ROOT", str(tmp_path)):
            # Re-resolve the Path inside the function via monkeypatching
            with patch("server_enhanced_with_lsp.Path") as MockPath:
                # Let Path() calls through for everything except WORKSPACE_ROOT
                import pathlib

                def path_side_effect(arg):
                    if arg == _srv.WORKSPACE_ROOT:
                        return pathlib.Path(str(tmp_path))
                    return pathlib.Path(arg)

                MockPath.side_effect = path_side_effect
                # Simpler: just patch WORKSPACE_ROOT on the module
            # Patch at module level for the duration of the call
            original_root = _srv.WORKSPACE_ROOT
            _srv.WORKSPACE_ROOT = str(tmp_path)
            try:
                result = _inner(_srv.terry_workspace_list)()
            finally:
                _srv.WORKSPACE_ROOT = original_root

        assert "workspaces" in result
        assert result["workspaces"] == []

    def test_directory_with_tf_files_is_listed(self, tmp_path):
        """A directory containing .tf files appears in the workspaces list."""
        proj = tmp_path / "myproject"
        proj.mkdir()
        (proj / "main.tf").write_text('provider "aws" {}')

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_list)()
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert len(result["workspaces"]) == 1
        assert result["workspaces"][0]["path"] == "myproject"

    def test_providers_extracted_from_tf_files(self, tmp_path):
        """Provider names are extracted from Terraform files."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "main.tf").write_text('provider "aws" {}\nprovider "azurerm" {}')

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_list)()
        finally:
            _srv.WORKSPACE_ROOT = original_root

        providers = result["workspaces"][0]["providers"]
        assert "aws" in providers
        assert "azurerm" in providers

    def test_oversized_files_are_skipped(self, tmp_path):
        """Files larger than _MAX_TF_FILE_SIZE are skipped without error."""
        proj = tmp_path / "bigproject"
        proj.mkdir()
        big_file = proj / "main.tf"
        big_file.write_text("x" * 10)

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        # Patch stat to report oversized file
        import pathlib

        real_stat = pathlib.Path.stat

        def fake_stat(self, *args, **kwargs):
            s = real_stat(self)
            # Trick: monkey-patch st_size only for our big file
            if str(self) == str(big_file):

                class _FakeStat:
                    st_size = _srv._MAX_TF_FILE_SIZE + 1
                    st_mtime = s.st_mtime

                return _FakeStat()
            return s

        try:
            with patch.object(pathlib.Path, "stat", fake_stat):
                result = _inner(_srv.terry_workspace_list)()
        finally:
            _srv.WORKSPACE_ROOT = original_root

        # Workspace is still listed (directory is found), but no providers extracted
        assert "workspaces" in result

    def test_initialized_workspace_detected(self, tmp_path):
        """Workspaces with .terraform dir are reported as initialized."""
        proj = tmp_path / "inited"
        proj.mkdir()
        (proj / "main.tf").write_text("resource {} {}")
        (proj / ".terraform").mkdir()

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_list)()
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["workspaces"][0]["initialized"] is True

    def test_uninitialized_workspace_detected(self, tmp_path):
        """Workspaces without .terraform dir are reported as not initialized."""
        proj = tmp_path / "uninited"
        proj.mkdir()
        (proj / "main.tf").write_text("resource {} {}")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_list)()
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["workspaces"][0]["initialized"] is False


# ---------------------------------------------------------------------------
# 3. terry_workspace_info()
# ---------------------------------------------------------------------------


class TestTerryWorkspaceInfo:
    """Tests for terry_workspace_info()."""

    def test_nonexistent_path_returns_error(self, tmp_path):
        """A path that does not exist returns an error dict."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_info)(path="does_not_exist")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terry-workspace"]

    def test_existing_path_returns_info(self, tmp_path):
        """An existing path returns workspace info without error."""
        proj = tmp_path / "myworkspace"
        proj.mkdir()
        (proj / "main.tf").write_text("terraform {}")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_info)(path="myworkspace")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        ws = result["terry-workspace"]
        assert "error" not in ws
        assert ws["path_info"]["exists"] is True

    def test_terraform_dir_detected_as_initialized(self, tmp_path):
        """A .terraform directory means initialized=True."""
        proj = tmp_path / "inited"
        proj.mkdir()
        (proj / ".terraform").mkdir()

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_info)(path="inited")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["terry-workspace"]["terraform_state"]["initialized"] is True

    def test_missing_terraform_dir_means_not_initialized(self, tmp_path):
        """Without .terraform directory, initialized=False."""
        proj = tmp_path / "uninited"
        proj.mkdir()

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_info)(path="uninited")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["terry-workspace"]["terraform_state"]["initialized"] is False

    def test_tf_files_listed(self, tmp_path):
        """Existing .tf files are listed in terraform_files."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "main.tf").write_text("terraform {}")
        (proj / "variables.tf").write_text("variable x {}")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_info)(path="proj")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        tf_files = result["terry-workspace"]["terraform_files"]
        assert "main.tf" in tf_files
        assert "variables.tf" in tf_files


# ---------------------------------------------------------------------------
# 4. terry_workspace_setup()
# ---------------------------------------------------------------------------


class TestTerryWorkspaceSetup:
    """Tests for terry_workspace_setup()."""

    def test_creates_standard_files(self, tmp_path):
        """Setup creates main.tf, variables.tf, and outputs.tf."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_setup)(path="newproject")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        setup = result["terry-workspace-setup"]
        assert setup["success"] is True
        assert "main.tf" in setup["created_files"]
        assert "variables.tf" in setup["created_files"]
        assert "outputs.tf" in setup["created_files"]

    def test_project_name_embedded_in_files(self, tmp_path):
        """The project name appears in the generated file content."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            _inner(_srv.terry_workspace_setup)(path="proj", project_name="my-app")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        main_tf = (tmp_path / "proj" / "main.tf").read_text()
        assert "my-app" in main_tf

    def test_existing_files_not_overwritten(self, tmp_path):
        """Files that already exist are not recreated."""
        proj = tmp_path / "existing"
        proj.mkdir()
        existing_content = "# existing content"
        (proj / "main.tf").write_text(existing_content)

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_setup)(path="existing")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        setup = result["terry-workspace-setup"]
        assert "main.tf" not in setup["created_files"]
        assert (proj / "main.tf").read_text() == existing_content

    def test_invalid_project_name_rejected(self, tmp_path):
        """A project name with special characters returns an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_workspace_setup)(path="proj", project_name="bad name!")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terry-workspace-setup"]

    def test_makedirs_failure_returns_error(self, tmp_path):
        """An OS error from makedirs is caught and returned as an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch("server_enhanced_with_lsp.os.makedirs", side_effect=OSError("no space")):
                result = _inner(_srv.terry_workspace_setup)(path="failproject")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terry-workspace-setup"]


# ---------------------------------------------------------------------------
# 5–8. LSP tools (terraform_validate_lsp, terraform_hover, terraform_complete,
#      terraform_format_lsp)
# ---------------------------------------------------------------------------


def _make_lsp_client(method_name: str, return_value: dict) -> MagicMock:
    """Build a synchronous MagicMock LSP client whose specified method is an AsyncMock.

    This avoids creating an AsyncMock for the entire client, which would cause
    auto-created child attributes (like .validate_document) to also be AsyncMocks
    that generate unawaited-coroutine warnings when accessed across asyncio.run()
    boundaries.
    """
    client = MagicMock()
    setattr(client, method_name, AsyncMock(return_value=return_value))
    return client


class TestTerraformValidateLsp:
    """Tests for terraform_validate_lsp()."""

    def test_missing_file_returns_error(self, tmp_path):
        """If the resolved file does not exist, return an error dict."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = run(_inner(_srv.terraform_validate_lsp)(file_path="nonexistent.tf"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terraform-ls-validation"]

    def test_path_resolution_without_workspace_path(self, tmp_path):
        """Without workspace_path, file is resolved relative to WORKSPACE_ROOT."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("terraform {}")

        mock_client = _make_lsp_client("validate_document", {"diagnostics": []})

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=mock_client)
                result = run(_inner(_srv.terraform_validate_lsp)(file_path="main.tf"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "terraform-ls-validation" in result
        assert "error" not in result["terraform-ls-validation"]

    def test_path_resolution_with_workspace_path(self, tmp_path):
        """With workspace_path, file is resolved as workspace_path / file_path."""
        ws = tmp_path / "myws"
        ws.mkdir()
        tf_file = ws / "main.tf"
        tf_file.write_text("terraform {}")

        mock_client = _make_lsp_client("validate_document", {"diagnostics": []})

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=mock_client)
                result = run(
                    _inner(_srv.terraform_validate_lsp)(
                        file_path="main.tf", workspace_path="myws"
                    )
                )
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "terraform-ls-validation" in result

    def test_lsp_client_exception_returns_error(self, tmp_path):
        """If get_lsp_client raises, an error dict is returned."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("terraform {}")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(side_effect=RuntimeError("LSP crashed"))
                result = run(_inner(_srv.terraform_validate_lsp)(file_path="main.tf"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terraform-ls-validation"]


class TestTerraformHover:
    """Tests for terraform_hover()."""

    def test_missing_file_returns_error(self, tmp_path):
        """Missing file produces an error with position info."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = run(_inner(_srv.terraform_hover)(file_path="ghost.tf", line=0, character=0))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        rv = result["terraform-hover"]
        assert "error" in rv
        assert rv["position"] == {"line": 0, "character": 0}

    def test_hover_result_includes_position(self, tmp_path):
        """Successful hover response includes the requested position."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("terraform {}")

        mock_client = _make_lsp_client("get_hover_info", {"content": "some docs"})

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=mock_client)
                result = run(
                    _inner(_srv.terraform_hover)(file_path="main.tf", line=3, character=5)
                )
        finally:
            _srv.WORKSPACE_ROOT = original_root

        rv = result["terraform-hover"]
        assert rv["position"] == {"line": 3, "character": 5}

    def test_lsp_exception_returns_error(self, tmp_path):
        """An LSP exception is caught and returned as an error."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("terraform {}")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(side_effect=RuntimeError("boom"))
                result = run(
                    _inner(_srv.terraform_hover)(file_path="main.tf", line=0, character=0)
                )
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terraform-hover"]


class TestTerraformComplete:
    """Tests for terraform_complete()."""

    def test_missing_file_returns_error(self, tmp_path):
        """Missing file produces an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = run(_inner(_srv.terraform_complete)(file_path="missing.tf", line=0, character=0))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terraform-completions"]

    def test_completions_result_returned(self, tmp_path):
        """Successful completions call returns items from LSP client."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("res")

        mock_client = _make_lsp_client("get_completions", {"items": [{"label": "resource"}]})

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=mock_client)
                result = run(
                    _inner(_srv.terraform_complete)(file_path="main.tf", line=0, character=3)
                )
        finally:
            _srv.WORKSPACE_ROOT = original_root

        rv = result["terraform-completions"]
        assert rv["items"] == [{"label": "resource"}]

    def test_lsp_exception_returns_error(self, tmp_path):
        """LSP exceptions are caught and returned as errors."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("x")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(side_effect=RuntimeError("fail"))
                result = run(
                    _inner(_srv.terraform_complete)(file_path="main.tf", line=0, character=0)
                )
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terraform-completions"]


class TestTerraformFormatLsp:
    """Tests for terraform_format_lsp()."""

    def test_missing_file_returns_error(self, tmp_path):
        """Missing file produces an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = run(_inner(_srv.terraform_format_lsp)(file_path="missing.tf"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terraform-format"]

    def test_format_result_returned(self, tmp_path):
        """Successful format call returns edits from LSP client."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("resource  { }")

        mock_client = _make_lsp_client("format_document", {"edits": []})

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=mock_client)
                result = run(_inner(_srv.terraform_format_lsp)(file_path="main.tf"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        rv = result["terraform-format"]
        assert "edits" in rv

    def test_lsp_exception_returns_error(self, tmp_path):
        """LSP exceptions are caught."""
        tf_file = tmp_path / "main.tf"
        tf_file.write_text("x")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod.get_lsp_client = AsyncMock(side_effect=RuntimeError("fail"))
                result = run(_inner(_srv.terraform_format_lsp)(file_path="main.tf"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terraform-format"]


# ---------------------------------------------------------------------------
# 9. terraform_lsp_status()
# ---------------------------------------------------------------------------


class TestTerraformLspStatus:
    """Tests for terraform_lsp_status()."""

    def test_no_active_client_returns_inactive(self):
        """When _lsp_client is None the status is 'inactive'."""
        with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
            mock_lsp_mod._lsp_client = None
            result = _inner(_srv.terraform_lsp_status)()

        assert result["terraform-ls-status"]["status"] == "inactive"
        assert result["terraform-ls-status"]["initialized"] is False

    def test_active_initialized_client_returns_active(self):
        """When _lsp_client exists and is initialized, status is 'active'."""
        mock_client = MagicMock()
        mock_client.initialized = True
        mock_client.capabilities = {"hover": True}
        mock_client.workspace_root = "/mnt/workspace/proj"

        with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
            mock_lsp_mod._lsp_client = mock_client
            result = _inner(_srv.terraform_lsp_status)()

        assert result["terraform-ls-status"]["status"] == "active"
        assert result["terraform-ls-status"]["initialized"] is True

    def test_client_exists_but_not_initialized_returns_inactive(self):
        """A client that is not yet initialized is reported as inactive."""
        mock_client = MagicMock()
        mock_client.initialized = False

        with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
            mock_lsp_mod._lsp_client = mock_client
            result = _inner(_srv.terraform_lsp_status)()

        assert result["terraform-ls-status"]["status"] == "inactive"


# ---------------------------------------------------------------------------
# 10. terry_analyze()
# ---------------------------------------------------------------------------


class TestTerryAnalyze:
    """Tests for terry_analyze()."""

    def test_nonexistent_path_returns_error(self, tmp_path):
        """A missing path returns an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_analyze)(path="ghost")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result

    def test_empty_directory_returns_perfect_score(self, tmp_path):
        """A directory with no .tf files returns score=100 and no issues."""
        proj = tmp_path / "empty"
        proj.mkdir()

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_analyze)(path="empty")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        analysis = result["analysis"]
        assert analysis["score"] == 100
        assert analysis["issues"] == []

    def test_variable_without_description_reduces_score(self, tmp_path):
        """A variable without a description field adds a warning and reduces score."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "main.tf").write_text('variable "my_var" {\n  type = string\n}\n')

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_analyze)(path="proj")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        analysis = result["analysis"]
        assert analysis["score"] < 100
        issue_types = [i["type"] for i in analysis["issues"]]
        assert "documentation" in issue_types

    def test_hardcoded_ami_id_reduces_score(self, tmp_path):
        """A hardcoded AMI ID is detected and reduces the score."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "main.tf").write_text('resource "aws_instance" "x" { ami = "ami-0abcdef123456789" }')

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_analyze)(path="proj")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        analysis = result["analysis"]
        assert analysis["score"] < 100
        issue_types = [i["type"] for i in analysis["issues"]]
        assert "hardcoding" in issue_types

    def test_score_never_goes_below_zero(self, tmp_path):
        """Score is clamped to 0, never negative."""
        proj = tmp_path / "proj"
        proj.mkdir()
        # Many issues: multiple vars without descriptions + hardcoded IDs
        content = "\n".join(
            [
                f'variable "v{i}" {{\n  type = string\n}}\n'
                for i in range(100)
            ]
        )
        (proj / "main.tf").write_text(content)

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_analyze)(path="proj")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["analysis"]["score"] >= 0

    def test_statistics_count_resources(self, tmp_path):
        """Resource count is tracked in statistics."""
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "main.tf").write_text(
            'resource "aws_instance" "web" {}\nresource "aws_instance" "db" {}'
        )

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_analyze)(path="proj")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["analysis"]["statistics"]["resources"] == 2


# ---------------------------------------------------------------------------
# 11. terry_security_scan() — CRITICAL
# ---------------------------------------------------------------------------


class TestTerrySecurityScan:
    """Tests for terry_security_scan(). Critical: all 4 vulnerability patterns."""

    def _make_scan(self, tmp_path, tf_content, severity="low"):
        """Helper: write tf_content to main.tf and run security scan."""
        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        (proj / "main.tf").write_text(tf_content)

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_security_scan)(path="proj", severity=severity)
        finally:
            _srv.WORKSPACE_ROOT = original_root

        return result

    def test_nonexistent_path_returns_error(self, tmp_path):
        """Missing path returns an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_security_scan)(path="ghost")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result

    def test_invalid_severity_returns_error(self, tmp_path):
        """An invalid severity value returns an error without scanning."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_security_scan)(path=".", severity="extreme")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result
        assert "Invalid severity" in result["error"]

    def test_public_s3_acl_detected(self, tmp_path):
        """Public S3 ACL triggers CKV_AWS_20 vulnerability (severity=high)."""
        tf = '''
resource "aws_s3_bucket" "public_bucket" {
  bucket = "my-bucket"
  acl    = "public-read"
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_20" in vuln_ids

    def test_s3_missing_encryption_detected(self, tmp_path):
        """S3 bucket without server_side_encryption_configuration triggers CKV_AWS_19."""
        tf = '''
resource "aws_s3_bucket" "unencrypted" {
  bucket = "my-bucket"
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_19" in vuln_ids

    def test_open_security_group_detected(self, tmp_path):
        """Security group with 0.0.0.0/0 triggers CKV_AWS_24 (severity=high)."""
        tf = '''
resource "aws_security_group" "open" {
  name = "open-sg"
  ingress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
  }
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_24" in vuln_ids

    def test_unencrypted_rds_detected(self, tmp_path):
        """RDS without storage_encrypted triggers CKV_AWS_16 (severity=high)."""
        tf = '''
resource "aws_db_instance" "mydb" {
  identifier = "mydb"
  engine     = "mysql"
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_16" in vuln_ids

    def test_rds_explicitly_unencrypted_detected(self, tmp_path):
        """RDS with storage_encrypted = false also triggers CKV_AWS_16."""
        tf = '''
resource "aws_db_instance" "mydb" {
  identifier        = "mydb"
  storage_encrypted = false
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_16" in vuln_ids

    def test_iam_wildcard_actions_detected(self, tmp_path):
        """IAM policy with wildcard actions triggers CKV_AWS_1."""
        tf = '''
data "aws_iam_policy_document" "admin" {
  statement {
    actions   = ["*"]
    resources = ["arn:aws:s3:::my-bucket"]
  }
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_1" in vuln_ids

    def test_iam_wildcard_resources_detected(self, tmp_path):
        """IAM policy with wildcard resources triggers CKV_AWS_1."""
        tf = '''
data "aws_iam_policy_document" "admin" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["*"]
  }
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_1" in vuln_ids

    def test_severity_filter_excludes_low_findings(self, tmp_path):
        """With severity='high', medium-severity findings are excluded."""
        # S3 without encryption is 'medium' severity
        tf = '''
resource "aws_s3_bucket" "unencrypted" {
  bucket = "my-bucket"
}
'''
        result = self._make_scan(tmp_path, tf, severity="high")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        # CKV_AWS_19 is medium — should NOT appear at high filter
        assert "CKV_AWS_19" not in vuln_ids

    def test_severity_filter_includes_high_findings_at_medium(self, tmp_path):
        """With severity='medium', high-severity findings are included."""
        tf = '''
resource "aws_s3_bucket" "public" {
  acl = "public-read"
}
'''
        result = self._make_scan(tmp_path, tf, severity="medium")
        vuln_ids = [v["id"] for v in result["security_scan"]["vulnerabilities"]]
        assert "CKV_AWS_20" in vuln_ids

    def test_clean_config_has_no_vulnerabilities(self, tmp_path):
        """A clean configuration produces no vulnerabilities."""
        tf = '''
resource "aws_s3_bucket" "clean" {
  bucket = "my-secure-bucket"
  acl    = "private"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        assert result["security_scan"]["vulnerabilities"] == []

    def test_summary_counts_match_vulnerabilities(self, tmp_path):
        """Summary severity counts match the number of vulnerability entries."""
        tf = '''
resource "aws_s3_bucket" "pub" {
  acl = "public-read"
}
'''
        result = self._make_scan(tmp_path, tf, severity="low")
        scan = result["security_scan"]
        total_in_summary = sum(scan["summary"].values())
        assert total_in_summary == len(scan["vulnerabilities"])


# ---------------------------------------------------------------------------
# 12. terry_recommendations()
# ---------------------------------------------------------------------------


class TestTerryRecommendations:
    """Tests for terry_recommendations()."""

    def _run_recs(self, tmp_path, tf_content, focus="security"):
        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        (proj / "main.tf").write_text(tf_content)

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_recommendations)(path="proj", focus=focus)
        finally:
            _srv.WORKSPACE_ROOT = original_root

        return result

    def test_invalid_focus_returns_error(self, tmp_path):
        """An unrecognised focus area returns an error."""
        proj = tmp_path / "proj"
        proj.mkdir(exist_ok=True)
        (proj / "main.tf").write_text("terraform {}")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_recommendations)(path="proj", focus="crypto")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result
        assert "Invalid focus" in result["error"]

    def test_nonexistent_path_returns_error(self, tmp_path):
        """A missing path returns an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_recommendations)(path="ghost")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result

    def test_security_focus_kms_recommendation(self, tmp_path):
        """Security focus with S3 and no KMS key recommends KMS encryption."""
        tf = 'resource "aws_s3_bucket" "b" {}'
        result = self._run_recs(tmp_path, tf, focus="security")
        titles = [r["title"] for r in result["recommendations"]["recommendations"]]
        assert any("KMS" in t for t in titles)

    def test_cost_focus_spot_instance_recommendation(self, tmp_path):
        """Cost focus with aws_instance and no spot recommends Spot Instances."""
        tf = 'resource "aws_instance" "x" { instance_type = "t3.medium" }'
        result = self._run_recs(tmp_path, tf, focus="cost")
        titles = [r["title"] for r in result["recommendations"]["recommendations"]]
        assert any("Spot" in t for t in titles)

    def test_performance_focus_monitoring_recommendation(self, tmp_path):
        """Performance focus with aws_instance and no monitoring recommends monitoring."""
        tf = 'resource "aws_instance" "x" { instance_type = "t3.medium" }'
        result = self._run_recs(tmp_path, tf, focus="performance")
        titles = [r["title"] for r in result["recommendations"]["recommendations"]]
        assert any("monitoring" in t.lower() for t in titles)

    def test_reliability_focus_backup_recommendation(self, tmp_path):
        """Reliability focus with RDS and no backup_retention_period recommends backups."""
        tf = 'resource "aws_db_instance" "db" { engine = "mysql" }'
        result = self._run_recs(tmp_path, tf, focus="reliability")
        titles = [r["title"] for r in result["recommendations"]["recommendations"]]
        assert any("backup" in t.lower() for t in titles)

    def test_priority_actions_contains_top_recommendations(self, tmp_path):
        """priority_actions contains the titles of the top recommendations."""
        tf = 'resource "aws_s3_bucket" "b" {}\nresource "aws_db_instance" "db" { engine = "mysql" }'
        result = self._run_recs(tmp_path, tf, focus="security")
        recs = result["recommendations"]
        if recs["recommendations"]:
            for action in recs["priority_actions"]:
                all_titles = [r["title"] for r in recs["recommendations"]]
                assert action in all_titles

    def test_recommendations_sorted_by_impact(self, tmp_path):
        """Recommendations are sorted high → medium → low impact."""
        tf = (
            'resource "aws_instance" "x" { instance_type = "t3.medium" }\n'
            'resource "aws_s3_bucket" "b" {}'
        )
        result = self._run_recs(tmp_path, tf, focus="security")
        recs = result["recommendations"]["recommendations"]
        impact_order = {"high": 3, "medium": 2, "low": 1}
        impact_values = [impact_order.get(r["impact"], 0) for r in recs]
        assert impact_values == sorted(impact_values, reverse=True)


# ---------------------------------------------------------------------------
# 13. terry_version()
# ---------------------------------------------------------------------------


class TestTerryVersion:
    """Tests for terry_version()."""

    def test_json_output_parsed_correctly(self):
        """When 'terraform version -json' succeeds, version info is returned."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"terraform_version": "1.12.0", "platform": "linux_amd64"}'

        with patch("server_enhanced_with_lsp.subprocess.run", return_value=mock_result):
            result = _inner(_srv.terry_version)()

        assert result["terraform_version"] == "1.12.0"
        assert result["platform"] == "linux_amd64"

    def test_fallback_when_json_decode_fails(self):
        """Non-JSON output falls back to plain version parsing."""
        json_fail = MagicMock()
        json_fail.returncode = 0
        json_fail.stdout = "not-json"

        plain_version = MagicMock()
        plain_version.returncode = 0
        plain_version.stdout = "Terraform v1.11.0\n"

        uname = MagicMock()
        uname.returncode = 0
        uname.stdout = "x86_64\n"

        with patch(
            "server_enhanced_with_lsp.subprocess.run",
            side_effect=[json_fail, plain_version, uname],
        ):
            result = _inner(_srv.terry_version)()

        assert "1.11.0" in result["terraform_version"]

    def test_terraform_not_found_returns_error(self):
        """FileNotFoundError (terraform binary missing) returns an error dict."""
        with patch(
            "server_enhanced_with_lsp.subprocess.run",
            side_effect=FileNotFoundError("not found"),
        ):
            result = _inner(_srv.terry_version)()

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_nonzero_returncode_returns_error(self):
        """A non-zero returncode causes an error to be returned."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("server_enhanced_with_lsp.subprocess.run", return_value=mock_result):
            result = _inner(_srv.terry_version)()

        assert "error" in result


# ---------------------------------------------------------------------------
# 14. terry_environment_check()
# ---------------------------------------------------------------------------


class TestTerryEnvironmentCheck:
    """Tests for terry_environment_check()."""

    def test_terraform_found_reported_as_available(self):
        """When 'which terraform' succeeds, terraform is reported available."""
        which_tf = MagicMock(returncode=0, stdout="/usr/local/bin/terraform\n")
        version_tf = MagicMock(returncode=0, stdout="Terraform v1.12.0\n")
        which_ls = MagicMock(returncode=0, stdout="/usr/local/bin/terraform-ls\n")
        version_ls = MagicMock(returncode=0, stdout="0.38.5\n")
        hostname = MagicMock(returncode=0, stdout="myhost\n")

        with patch(
            "server_enhanced_with_lsp.subprocess.run",
            side_effect=[which_tf, version_tf, which_ls, version_ls, hostname],
        ):
            result = _inner(_srv.terry_environment_check)()

        env = result["terry-environment"]
        assert env["terraform"]["available"] is True

    def test_terraform_not_found_reported_as_unavailable(self):
        """When 'which terraform' fails, terraform is reported unavailable."""
        which_tf = MagicMock(returncode=1, stdout="")
        which_ls = MagicMock(returncode=1, stdout="")
        hostname = MagicMock(returncode=0, stdout="myhost\n")

        with patch(
            "server_enhanced_with_lsp.subprocess.run",
            side_effect=[which_tf, which_ls, hostname],
        ):
            result = _inner(_srv.terry_environment_check)()

        env = result["terry-environment"]
        assert env["terraform"]["available"] is False

    def test_environment_keys_present(self):
        """Result always contains environment, terraform, terraform_ls, container."""
        which_tf = MagicMock(returncode=1, stdout="")
        which_ls = MagicMock(returncode=1, stdout="")
        hostname = MagicMock(returncode=0, stdout="h\n")

        with patch(
            "server_enhanced_with_lsp.subprocess.run",
            side_effect=[which_tf, which_ls, hostname],
        ):
            result = _inner(_srv.terry_environment_check)()

        env = result["terry-environment"]
        assert "environment" in env
        assert "terraform" in env
        assert "terraform_ls" in env


# ---------------------------------------------------------------------------
# 15. terry_lsp_init()
# ---------------------------------------------------------------------------


class TestTerryLspInit:
    """Tests for terry_lsp_init()."""

    def test_nonexistent_workspace_returns_error(self, tmp_path):
        """A workspace that doesn't exist returns an error."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = run(_inner(_srv.terry_lsp_init)(workspace_path="ghost"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert "error" in result["terry-lsp-init"]

    def test_successful_lsp_init(self, tmp_path):
        """A valid workspace with a working LSP client returns success."""
        ws = tmp_path / "myws"
        ws.mkdir()

        mock_client = MagicMock()
        mock_client.initialized = True
        mock_client.capabilities = {}

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod._lsp_client = None
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=mock_client)
                result = run(_inner(_srv.terry_lsp_init)(workspace_path="myws"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        init_result = result["terry-lsp-init"]
        assert init_result["success"] is True

    def test_failed_lsp_init_returns_success_false(self, tmp_path):
        """When the LSP client fails to initialize, returns success=False."""
        ws = tmp_path / "myws"
        ws.mkdir()

        mock_client = MagicMock()
        mock_client.initialized = False

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod._lsp_client = None
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=mock_client)
                result = run(_inner(_srv.terry_lsp_init)(workspace_path="myws"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["terry-lsp-init"]["success"] is False

    def test_existing_client_shut_down_before_new_init(self, tmp_path):
        """An existing LSP client is shut down before creating a new one."""
        ws = tmp_path / "myws"
        ws.mkdir()

        old_client = MagicMock()
        old_client.shutdown = AsyncMock()

        new_client = MagicMock()
        new_client.initialized = True
        new_client.capabilities = {}

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
                mock_lsp_mod._lsp_client = old_client
                mock_lsp_mod.get_lsp_client = AsyncMock(return_value=new_client)
                run(_inner(_srv.terry_lsp_init)(workspace_path="myws"))
        finally:
            _srv.WORKSPACE_ROOT = original_root

        old_client.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# 16. terry_lsp_debug()
# ---------------------------------------------------------------------------


class TestTerryLspDebug:
    """Tests for terry_lsp_debug()."""

    def test_no_active_client_lsp_client_exists_false(self):
        """When _lsp_client is None, lsp_client.exists is False."""
        version_result = MagicMock(returncode=0, stdout="0.38.5\n")
        help_result = MagicMock(returncode=0, stdout="Usage: terraform-ls serve")

        with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
            mock_lsp_mod._lsp_client = None
            with patch(
                "server_enhanced_with_lsp.subprocess.run",
                side_effect=[version_result, help_result],
            ):
                result = _inner(_srv.terry_lsp_debug)()

        debug = result["terry-lsp-debug"]
        assert debug["lsp_client"]["exists"] is False

    def test_active_client_lsp_client_exists_true(self):
        """When _lsp_client exists, lsp_client.exists is True."""
        mock_client = MagicMock()
        mock_client.initialized = True
        mock_client.workspace_root = "/mnt/workspace"
        mock_client.terraform_ls_process = MagicMock()

        version_result = MagicMock(returncode=0, stdout="0.38.5\n")
        help_result = MagicMock(returncode=0, stdout="Usage: terraform-ls serve")

        with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
            mock_lsp_mod._lsp_client = mock_client
            with patch(
                "server_enhanced_with_lsp.subprocess.run",
                side_effect=[version_result, help_result],
            ):
                result = _inner(_srv.terry_lsp_debug)()

        debug = result["terry-lsp-debug"]
        assert debug["lsp_client"]["exists"] is True
        assert debug["lsp_client"]["initialized"] is True

    def test_binary_not_found_reported_gracefully(self):
        """FileNotFoundError from terraform-ls is caught and reported."""
        with patch.object(_srv, "terraform_lsp_client") as mock_lsp_mod:
            mock_lsp_mod._lsp_client = None
            with patch(
                "server_enhanced_with_lsp.subprocess.run",
                side_effect=FileNotFoundError("binary not found"),
            ):
                result = _inner(_srv.terry_lsp_debug)()

        debug = result["terry-lsp-debug"]
        assert debug["terraform_ls_binary"]["available"] is False
        assert "binary not found" in debug["terraform_ls_binary"]["error"]


# ---------------------------------------------------------------------------
# 17. terry_file_check()
# ---------------------------------------------------------------------------


class TestTerryFileCheck:
    """Tests for terry_file_check()."""

    def test_missing_file_exists_false(self, tmp_path):
        """A non-existent file returns exists=False."""
        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_file_check)(file_path="ghost.tf")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        fc = result["terry-file-check"]
        assert fc["exists"] is False
        assert fc["readable"] is False

    def test_existing_file_returns_readable_true(self, tmp_path):
        """An existing readable file returns readable=True."""
        (tmp_path / "main.tf").write_text("terraform {}")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_file_check)(file_path="main.tf")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        fc = result["terry-file-check"]
        assert fc["exists"] is True
        assert fc["readable"] is True

    def test_empty_file_has_content_false(self, tmp_path):
        """An empty file is reported as has_content=False."""
        (tmp_path / "empty.tf").write_text("")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_file_check)(file_path="empty.tf")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        fc = result["terry-file-check"]
        assert fc["syntax_check"]["has_content"] is False

    def test_terraform_block_detected(self, tmp_path):
        """A file with 'terraform {' is reported as having a terraform block."""
        (tmp_path / "main.tf").write_text("terraform {\n  required_version = \">= 1.0\"\n}\n")

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_file_check)(file_path="main.tf")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["terry-file-check"]["syntax_check"]["has_terraform_block"] is True

    def test_resource_block_detected(self, tmp_path):
        """A file with 'resource "' is reported as having a resource block."""
        (tmp_path / "main.tf").write_text('resource "aws_instance" "x" {}')

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_file_check)(file_path="main.tf")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["terry-file-check"]["syntax_check"]["has_resource_block"] is True

    def test_size_reflects_file_content(self, tmp_path):
        """Size in result matches the byte length of the file content."""
        content = "terraform {}"
        (tmp_path / "main.tf").write_text(content)

        original_root = _srv.WORKSPACE_ROOT
        _srv.WORKSPACE_ROOT = str(tmp_path)
        try:
            result = _inner(_srv.terry_file_check)(file_path="main.tf")
        finally:
            _srv.WORKSPACE_ROOT = original_root

        assert result["terry-file-check"]["size"] == len(content)


# ---------------------------------------------------------------------------
# 18. health_live()
# ---------------------------------------------------------------------------


class TestHealthLive:
    """Tests for health_live()."""

    def test_always_returns_ok(self):
        """health_live always returns status=ok."""
        result = _srv.health_live()
        assert result == {"status": "ok"}

    def test_returns_dict(self):
        """health_live returns a dict, not some other type."""
        assert isinstance(_srv.health_live(), dict)


# ---------------------------------------------------------------------------
# 19. health_ready()
# ---------------------------------------------------------------------------


class TestHealthReady:
    """Tests for health_ready()."""

    def test_terraform_available_returns_ok(self):
        """When terraform binary is found, status is ok."""
        mock_result = MagicMock(returncode=0)
        with patch("server_enhanced_with_lsp.subprocess.run", return_value=mock_result):
            result = _srv.health_ready()

        assert result["status"] == "ok"
        assert result["terraform"] == "available"

    def test_terraform_not_found_returns_not_ready(self):
        """FileNotFoundError means terraform is missing -> not_ready."""
        with patch(
            "server_enhanced_with_lsp.subprocess.run",
            side_effect=FileNotFoundError("not found"),
        ):
            result = _srv.health_ready()

        assert result["status"] == "not_ready"
        assert "not found" in result["reason"].lower()

    def test_terraform_nonzero_exit_returns_not_ready(self):
        """A non-zero exit code means terraform can't run -> not_ready."""
        mock_result = MagicMock(returncode=1)
        with patch("server_enhanced_with_lsp.subprocess.run", return_value=mock_result):
            result = _srv.health_ready()

        assert result["status"] == "not_ready"

    def test_terraform_timeout_returns_not_ready(self):
        """A subprocess timeout returns not_ready."""
        with patch(
            "server_enhanced_with_lsp.subprocess.run",
            side_effect=__import__("subprocess").TimeoutExpired(cmd=["terraform"], timeout=10),
        ):
            result = _srv.health_ready()

        assert result["status"] == "not_ready"


# ---------------------------------------------------------------------------
# 20. api_metrics()
# ---------------------------------------------------------------------------


class TestApiMetrics:
    """Tests for api_metrics()."""

    def test_returns_uptime_seconds(self):
        """api_metrics includes uptime_seconds as a positive number."""
        result = _srv.api_metrics()
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] > 0

    def test_returns_rate_limiter_state(self):
        """api_metrics includes rate_limiter with limits and counts."""
        result = _srv.api_metrics()
        assert "rate_limiter" in result
        rl = result["rate_limiter"]
        assert "limits" in rl
        assert "current_window_counts" in rl

    def test_rate_limiter_limits_are_correct(self):
        """The reported limits match the known defaults."""
        result = _srv.api_metrics()
        limits = result["rate_limiter"]["limits"]
        assert limits["terraform"] == 20
        assert limits["github"] == 30
        assert limits["default"] == 100

    def test_uptime_increases_over_time(self):
        """Calling api_metrics twice yields a larger uptime on the second call."""
        r1 = _srv.api_metrics()
        import time

        time.sleep(0.01)
        r2 = _srv.api_metrics()
        assert r2["uptime_seconds"] > r1["uptime_seconds"]


# ---------------------------------------------------------------------------
# 21–24. GitHub tools
# ---------------------------------------------------------------------------


class TestGithubTools:
    """Tests for github_clone_repo, github_list_terraform_files,
    github_get_terraform_config, github_prepare_workspace."""

    # -- Helper: patch github_handler on the module --------------------------

    def _no_handler(self):
        """Context: github_handler is None (not configured)."""
        return patch.object(_srv, "github_handler", None)

    def _with_handler(self, handler):
        """Context: github_handler is the provided mock."""
        return patch.object(_srv, "github_handler", handler)

    # -- github_clone_repo ---------------------------------------------------

    def test_clone_repo_unconfigured_returns_error(self):
        """When github_handler is None, clone returns an error."""
        with self._no_handler():
            result = run(_inner(_srv.github_clone_repo)(owner="acme", repo="infra"))
        assert "error" in result
        assert "not configured" in result["error"].lower()

    def test_clone_repo_delegates_to_handler(self):
        """When configured, clone_repo delegates to github_handler."""
        mock_handler = AsyncMock()
        mock_handler.clone_or_update_repo = AsyncMock(
            return_value={"workspace_path": "/mnt/workspace/acme/infra"}
        )
        with self._with_handler(mock_handler):
            result = run(
                _inner(_srv.github_clone_repo)(owner="acme", repo="infra", branch="main")
            )

        mock_handler.clone_or_update_repo.assert_awaited_once_with(
            "acme", "infra", "main", False
        )
        assert result["workspace_path"] == "/mnt/workspace/acme/infra"

    def test_clone_repo_handler_exception_returns_error(self):
        """An exception from the handler is caught and returned as an error."""
        mock_handler = AsyncMock()
        mock_handler.clone_or_update_repo = AsyncMock(side_effect=RuntimeError("network fail"))
        with self._with_handler(mock_handler):
            result = run(_inner(_srv.github_clone_repo)(owner="acme", repo="infra"))

        assert "error" in result

    # -- github_list_terraform_files -----------------------------------------

    def test_list_tf_files_unconfigured_returns_error(self):
        """When github_handler is None, list_terraform_files returns an error."""
        with self._no_handler():
            result = run(_inner(_srv.github_list_terraform_files)(owner="acme", repo="infra"))
        assert "error" in result

    def test_list_tf_files_delegates_to_handler(self):
        """list_terraform_files delegates to github_handler.list_terraform_files."""
        mock_handler = AsyncMock()
        mock_handler.list_terraform_files = AsyncMock(
            return_value={"files": ["main.tf", "variables.tf"]}
        )
        with self._with_handler(mock_handler):
            result = run(
                _inner(_srv.github_list_terraform_files)(owner="acme", repo="infra", path="modules")
            )

        mock_handler.list_terraform_files.assert_awaited_once_with(
            "acme", "infra", "modules", "*.tf"
        )
        assert "files" in result

    def test_list_tf_files_handler_exception_returns_error(self):
        """Handler exception is returned as error."""
        mock_handler = AsyncMock()
        mock_handler.list_terraform_files = AsyncMock(side_effect=RuntimeError("API down"))
        with self._with_handler(mock_handler):
            result = run(_inner(_srv.github_list_terraform_files)(owner="acme", repo="infra"))

        assert "error" in result

    # -- github_get_terraform_config -----------------------------------------

    def test_get_config_unconfigured_returns_error(self):
        """When github_handler is None, get_terraform_config returns an error."""
        with self._no_handler():
            result = run(
                _inner(_srv.github_get_terraform_config)(
                    owner="acme", repo="infra", config_path="modules/vpc"
                )
            )
        assert "error" in result

    def test_get_config_delegates_to_handler(self):
        """get_terraform_config delegates to github_handler."""
        mock_handler = AsyncMock()
        mock_handler.get_terraform_config = AsyncMock(
            return_value={"providers": ["aws"], "modules": 2}
        )
        with self._with_handler(mock_handler):
            result = run(
                _inner(_srv.github_get_terraform_config)(
                    owner="acme", repo="infra", config_path="modules/vpc"
                )
            )

        mock_handler.get_terraform_config.assert_awaited_once_with(
            "acme", "infra", "modules/vpc"
        )
        assert result["providers"] == ["aws"]

    def test_get_config_handler_exception_returns_error(self):
        """Handler exception is returned as error."""
        mock_handler = AsyncMock()
        mock_handler.get_terraform_config = AsyncMock(side_effect=RuntimeError("timeout"))
        with self._with_handler(mock_handler):
            result = run(
                _inner(_srv.github_get_terraform_config)(
                    owner="acme", repo="infra", config_path="modules/vpc"
                )
            )

        assert "error" in result

    # -- github_prepare_workspace --------------------------------------------

    def test_prepare_workspace_unconfigured_returns_error(self):
        """When github_handler is None, prepare_workspace returns an error."""
        with self._no_handler():
            result = run(
                _inner(_srv.github_prepare_workspace)(
                    owner="acme", repo="infra", config_path="modules/vpc"
                )
            )
        assert "error" in result

    def test_prepare_workspace_delegates_to_handler(self):
        """prepare_workspace delegates to github_handler."""
        mock_handler = AsyncMock()
        mock_handler.prepare_terraform_workspace = AsyncMock(
            return_value={"workspace_path": "/mnt/workspace/vpc", "success": True}
        )
        with self._with_handler(mock_handler):
            result = run(
                _inner(_srv.github_prepare_workspace)(
                    owner="acme",
                    repo="infra",
                    config_path="modules/vpc",
                    workspace_name="my-vpc",
                )
            )

        mock_handler.prepare_terraform_workspace.assert_awaited_once_with(
            "acme", "infra", "modules/vpc", "my-vpc"
        )
        assert result["success"] is True

    def test_prepare_workspace_handler_exception_returns_error(self):
        """Handler exception is returned as error."""
        mock_handler = AsyncMock()
        mock_handler.prepare_terraform_workspace = AsyncMock(
            side_effect=RuntimeError("disk full")
        )
        with self._with_handler(mock_handler):
            result = run(
                _inner(_srv.github_prepare_workspace)(
                    owner="acme", repo="infra", config_path="modules/vpc"
                )
            )

        assert "error" in result
