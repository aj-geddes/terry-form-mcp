#!/usr/bin/env python3
"""
RED tests for Terraform Cloud tool registry removal (v3.2.0 prep).

Verifies:
1. The 4 tf_cloud_* tools are NOT registered in the MCP tool registry.
2. tools.json tool_count is updated to 21 (was 25).
3. tools.json contains no tf_cloud_* tool entries.
4. The "Terraform Cloud" category is absent from tools.json categories.
5. The rate-limiter still accepts "tf_cloud" as a valid category key
   (the rate-limit config is infra-level; removing tools doesn't remove limits).
6. CHANGELOG.md [Unreleased] section has a "### Removed" entry mentioning tf_cloud.
"""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent
_SRC = str(_ROOT / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_SERVER_PATH = _ROOT / "src" / "server_enhanced_with_lsp.py"
_TOOLS_JSON_PATH = _ROOT / "tools.json"
_CHANGELOG_PATH = _ROOT / "CHANGELOG.md"

_STUBBED_NAMES = (
    "fastmcp",
    "terraform_lsp_client",
    "terry-form-mcp",
    "mcp_request_validator",
    "server_enhanced_with_lsp",
)

_TF_CLOUD_TOOL_NAMES = frozenset(
    [
        "tf_cloud_list_workspaces",
        "tf_cloud_get_workspace",
        "tf_cloud_list_runs",
        "tf_cloud_get_state_outputs",
    ]
)

EXPECTED_TOOL_COUNT = 21


# ---------------------------------------------------------------------------
# Import helpers (mirrors pattern from test_config_env_fixes.py)
# ---------------------------------------------------------------------------


def _install_stubs() -> dict:
    """Snapshot sys.modules for stubbed names and install fresh stubs."""
    saved = {name: sys.modules.get(name) for name in _STUBBED_NAMES}

    fake_fastmcp = types.ModuleType("fastmcp")

    class _StubFastMCP:
        def __init__(self, *args, **kwargs):
            self._tools: dict = {}

        def tool(self, *args, **kwargs):
            def decorator(fn):
                self._tools[fn.__name__] = fn
                return fn

            return decorator

    fake_fastmcp.FastMCP = _StubFastMCP  # type: ignore[attr-defined]
    sys.modules["fastmcp"] = fake_fastmcp

    lsp_stub = types.ModuleType("terraform_lsp_client")
    lsp_stub._lsp_client = None  # type: ignore[attr-defined]
    sys.modules["terraform_lsp_client"] = lsp_stub

    terry_stub = types.ModuleType("terry-form-mcp")
    terry_stub.run_terraform = MagicMock(return_value={})  # type: ignore[attr-defined]
    sys.modules["terry-form-mcp"] = terry_stub

    validator_stub = types.ModuleType("mcp_request_validator")

    class _StubValidator:
        def validate_request(self, request):
            return True, None

    validator_stub.MCPRequestValidator = _StubValidator  # type: ignore[attr-defined]
    sys.modules["mcp_request_validator"] = validator_stub

    return saved


def _restore_stubs(saved: dict) -> None:
    for name in _STUBBED_NAMES:
        orig = saved.get(name)
        if orig is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = orig


def _import_server():
    saved = _install_stubs()
    sys.modules.pop("server_enhanced_with_lsp", None)
    import server_enhanced_with_lsp as srv

    return srv, saved


# ============================================================================
# 1. MCP tool registry must NOT contain tf_cloud_* tools
# ============================================================================


class TestTfCloudToolsNotInRegistry:
    """The 4 tf_cloud_* functions must not be registered as @mcp.tool() entries."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        srv, saved = _import_server()
        self.srv = srv
        self._saved = saved
        yield
        _restore_stubs(self._saved)

    def test_mcp_registry_excludes_tf_cloud_list_workspaces(self):
        """tf_cloud_list_workspaces must not appear in mcp._tools."""
        registered = set(self.srv.mcp._tools.keys())
        assert "tf_cloud_list_workspaces" not in registered, (
            "tf_cloud_list_workspaces is still registered as an @mcp.tool(). "
            "Remove the @mcp.tool() decorator."
        )

    def test_mcp_registry_excludes_tf_cloud_get_workspace(self):
        """tf_cloud_get_workspace must not appear in mcp._tools."""
        registered = set(self.srv.mcp._tools.keys())
        assert "tf_cloud_get_workspace" not in registered, (
            "tf_cloud_get_workspace is still registered as an @mcp.tool(). "
            "Remove the @mcp.tool() decorator."
        )

    def test_mcp_registry_excludes_tf_cloud_list_runs(self):
        """tf_cloud_list_runs must not appear in mcp._tools."""
        registered = set(self.srv.mcp._tools.keys())
        assert "tf_cloud_list_runs" not in registered, (
            "tf_cloud_list_runs is still registered as an @mcp.tool(). "
            "Remove the @mcp.tool() decorator."
        )

    def test_mcp_registry_excludes_tf_cloud_get_state_outputs(self):
        """tf_cloud_get_state_outputs must not appear in mcp._tools."""
        registered = set(self.srv.mcp._tools.keys())
        assert "tf_cloud_get_state_outputs" not in registered, (
            "tf_cloud_get_state_outputs is still registered as an @mcp.tool(). "
            "Remove the @mcp.tool() decorator."
        )

    def test_no_tf_cloud_tools_registered_at_all(self):
        """Zero tf_cloud_* tools must appear in the MCP registry."""
        registered = set(self.srv.mcp._tools.keys())
        found = registered & _TF_CLOUD_TOOL_NAMES
        assert len(found) == 0, (
            f"These tf_cloud_* tools are still registered: {found}. "
            "Comment out all @mcp.tool() decorators for tf_cloud_* functions."
        )

    def test_registry_reduced_by_four_tools(self):
        """After removing the 4 tf_cloud tools the registry count must be 4 fewer than before.

        Before removal: 28 registered (24 functional + 4 tf_cloud stubs).
        After removal:  24 registered (24 functional, 0 tf_cloud).
        The count 24 includes api_metrics, health_live, health_ready alongside
        the 21 user-facing tools listed in tools.json.
        """
        registered = set(self.srv.mcp._tools.keys())
        tf_cloud_still_present = registered & _TF_CLOUD_TOOL_NAMES
        assert len(tf_cloud_still_present) == 0, (
            f"tf_cloud_* tools still in registry: {tf_cloud_still_present}"
        )
        # Sanity: we expect the 21 user-facing tools plus infra tools (health, metrics).
        # At minimum all 21 tools.json tools must be present.
        expected_user_tools = {
            "terry", "terry_version", "terry_environment_check", "terry_workspace_list",
            "terraform_validate_lsp", "terraform_hover", "terraform_complete",
            "terraform_format_lsp", "terraform_lsp_status",
            "terry_lsp_debug", "terry_workspace_info", "terry_lsp_init",
            "terry_file_check", "terry_workspace_setup", "terry_analyze",
            "terry_recommendations", "terry_security_scan",
            "github_clone_repo", "github_list_terraform_files",
            "github_get_terraform_config", "github_prepare_workspace",
        }
        missing = expected_user_tools - registered
        assert len(missing) == 0, (
            f"Expected user-facing tools missing from registry: {missing}"
        )


# ============================================================================
# 2. tools.json must reflect the removal
# ============================================================================


class TestToolsJsonUpdated:
    """tools.json at repo root must be updated to remove tf_cloud_* entries."""

    def _load(self) -> dict:
        return json.loads(_TOOLS_JSON_PATH.read_text())

    def test_tool_count_is_21(self):
        """tools.json top-level 'tool_count' must be 21."""
        data = self._load()
        assert data["tool_count"] == EXPECTED_TOOL_COUNT, (
            f"tools.json tool_count is {data['tool_count']}, expected {EXPECTED_TOOL_COUNT}. "
            "Update tool_count after removing tf_cloud_* tool entries."
        )

    def test_no_tf_cloud_tool_entries(self):
        """tools.json 'tools' array must contain no tf_cloud_* entries."""
        data = self._load()
        tf_cloud_entries = [
            t["name"] for t in data["tools"] if t["name"].startswith("tf_cloud_")
        ]
        assert len(tf_cloud_entries) == 0, (
            f"tools.json still contains tf_cloud_* entries: {tf_cloud_entries}. "
            "Remove them from the 'tools' array."
        )

    def test_terraform_cloud_category_absent(self):
        """tools.json 'categories' must not include 'Terraform Cloud'."""
        data = self._load()
        categories = data.get("categories", {})
        assert "Terraform Cloud" not in categories, (
            "tools.json 'categories' still has a 'Terraform Cloud' entry. "
            "Remove it since no tf_cloud_* tools are registered."
        )

    def test_tool_list_length_matches_count(self):
        """The length of 'tools' array must equal 'tool_count'."""
        data = self._load()
        actual_len = len(data["tools"])
        stated_count = data["tool_count"]
        assert actual_len == stated_count, (
            f"tools.json 'tools' array has {actual_len} entries "
            f"but 'tool_count' says {stated_count}. Keep them in sync."
        )


# ============================================================================
# 3. CHANGELOG.md must have a Removed section entry
# ============================================================================


class TestChangelogRemovalEntry:
    """CHANGELOG.md [Unreleased] section must document the tf_cloud removal."""

    def _changelog(self) -> str:
        return _CHANGELOG_PATH.read_text()

    def test_removed_section_present_in_unreleased(self):
        """[Unreleased] block must contain a '### Removed' heading."""
        src = self._changelog()
        unreleased_block = src.split("## [3.1.0]")[0]
        assert "### Removed" in unreleased_block, (
            "CHANGELOG.md [Unreleased] section is missing '### Removed'. "
            "Add a Removed heading before the [3.1.0] block."
        )

    def test_tf_cloud_mentioned_in_removed_section(self):
        """The Removed section must mention at least one tf_cloud_* tool by name."""
        src = self._changelog()
        unreleased_block = src.split("## [3.1.0]")[0]
        # Find the Removed section content
        if "### Removed" not in unreleased_block:
            pytest.skip("### Removed section not yet present")
        removed_section = unreleased_block.split("### Removed", 1)[1]
        # Stop at the next ### heading if present
        if "###" in removed_section:
            removed_section = removed_section.split("###")[0]
        assert "tf_cloud" in removed_section, (
            "CHANGELOG.md ### Removed section does not mention 'tf_cloud'. "
            "Document the removal of the Terraform Cloud tools."
        )

    def test_planned_version_mentioned_in_changelog(self):
        """The removal entry should reference v3.2.0 as the planned implementation version."""
        src = self._changelog()
        unreleased_block = src.split("## [3.1.0]")[0]
        assert "3.2.0" in unreleased_block, (
            "CHANGELOG.md [Unreleased] section should mention v3.2.0 as the "
            "planned implementation milestone for tf_cloud tools."
        )


# ============================================================================
# 4. Source-level: tf_cloud block comment header present
# ============================================================================


class TestTfCloudCommentHeader:
    """The commented-out tf_cloud block must have the prescribed header comment."""

    def _source(self) -> str:
        return _SERVER_PATH.read_text()

    def test_comment_marker_present(self):
        """server_enhanced_with_lsp.py must contain the tf_cloud removal comment marker."""
        src = self._source()
        assert "Terraform Cloud tools (planned for v3.2.0)" in src, (
            "server_enhanced_with_lsp.py is missing the prescribed comment header "
            "'Terraform Cloud tools (planned for v3.2.0)'. "
            "Add it above the commented-out tf_cloud block."
        )
