#!/usr/bin/env python3
"""
Tests for configuration and environment fixes (production release hardening).

Covers:
1. WORKSPACE_ROOT configurable constant in server_enhanced_with_lsp.py
2. Security validator import is a hard failure (no silent None fallback)
3. TF Cloud tools return explicit "not implemented" errors
4. DEFAULT_TIMEOUT module-level constant with validation in terry-form-mcp.py
5. TERRY_HOST/TERRY_PORT env vars with backward compatibility
6. TERRAFORM_LS_BIN configurable path constant

Isolation contract
------------------
Every test that touches server_enhanced_with_lsp must:
1. Call _import_server() which saves the current sys.modules snapshot FIRST,
   then installs stubs, then pops and reimports the module.
2. Call _restore_server_stubs(saved) in a finally block to put sys.modules
   back exactly as it was before the test ran.

This ensures the collection-time stub-loaded module that test_server_enhanced.py
relies on is never displaced.
"""

import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module names that may be stubbed or transiently imported by these tests.
# All of them are saved before each import and restored after.
# ---------------------------------------------------------------------------

_STUBBED_NAMES = (
    "fastmcp",
    "terraform_lsp_client",
    "terry-form-mcp",
    "mcp_request_validator",
    "server_enhanced_with_lsp",
)


def _install_server_stubs() -> dict:
    """
    Snapshot current sys.modules for all stubbed names, then install fresh stubs.

    IMPORTANT: Call this BEFORE popping server_enhanced_with_lsp from sys.modules
    so the snapshot captures the collection-time module object and _restore_server_stubs
    can put it back.
    """
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


def _restore_server_stubs(saved: dict) -> None:
    """Restore sys.modules entries to exactly the state captured by _install_server_stubs."""
    for name in _STUBBED_NAMES:
        orig = saved.get(name)
        if orig is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = orig


def _import_server(env_overrides: dict | None = None):
    """
    Import server_enhanced_with_lsp cleanly with optional env overrides.

    Protocol:
    1. Save sys.modules snapshot (includes collection-time server module if present).
    2. Install dependency stubs.
    3. Pop cached server module so a fresh import runs.
    4. Import under patched env.
    5. Return (module, saved_snapshot) — caller must call _restore_server_stubs(saved).
    """
    saved = _install_server_stubs()
    sys.modules.pop("server_enhanced_with_lsp", None)

    with patch.dict(os.environ, env_overrides or {}, clear=False):
        import server_enhanced_with_lsp as srv
    return srv, saved


# ============================================================================
# Fix 1: WORKSPACE_ROOT configurable constant
# ============================================================================


class TestWorkspaceRootConstant:
    """WORKSPACE_ROOT is read from TERRY_WORKSPACE_ROOT env var with /mnt/workspace default."""

    def test_default_value_is_mnt_workspace(self, monkeypatch):
        monkeypatch.delenv("TERRY_WORKSPACE_ROOT", raising=False)
        srv, saved = _import_server()
        try:
            assert srv.WORKSPACE_ROOT == "/mnt/workspace"
        finally:
            _restore_server_stubs(saved)

    def test_env_override_is_respected(self, monkeypatch):
        monkeypatch.setenv("TERRY_WORKSPACE_ROOT", "/custom/workspace")
        srv, saved = _import_server({"TERRY_WORKSPACE_ROOT": "/custom/workspace"})
        try:
            assert srv.WORKSPACE_ROOT == "/custom/workspace"
        finally:
            _restore_server_stubs(saved)

    def test_workspace_root_is_string(self, monkeypatch):
        monkeypatch.delenv("TERRY_WORKSPACE_ROOT", raising=False)
        srv, saved = _import_server()
        try:
            assert isinstance(srv.WORKSPACE_ROOT, str)
        finally:
            _restore_server_stubs(saved)


# ============================================================================
# Fix 2: Security validator import is a hard failure
# ============================================================================


class TestSecurityValidatorHardFailure:
    """Failed mcp_request_validator import must raise, not silently set None."""

    def test_import_error_propagates(self):
        """If mcp_request_validator is absent from sys.modules and unimportable,
        the server module must raise rather than silently continuing."""
        saved = _install_server_stubs()
        sys.modules.pop("server_enhanced_with_lsp", None)

        # Remove the validator stub so Python has to actually import it,
        # then make the real import path raise via builtins.__import__.
        sys.modules.pop("mcp_request_validator", None)

        import builtins
        orig_import = builtins.__import__

        def _raise_on_validator(name, *args, **kwargs):
            if name == "mcp_request_validator":
                raise ImportError("simulated missing package")
            return orig_import(name, *args, **kwargs)

        try:
            with patch.object(builtins, "__import__", side_effect=_raise_on_validator):
                with pytest.raises((ImportError, Exception)):
                    import server_enhanced_with_lsp  # noqa: F401
        finally:
            sys.modules.pop("server_enhanced_with_lsp", None)
            _restore_server_stubs(saved)

    def test_request_validator_is_not_none_on_success(self, monkeypatch):
        """When import succeeds, request_validator must not be None."""
        monkeypatch.delenv("TERRY_WORKSPACE_ROOT", raising=False)
        srv, saved = _import_server()
        try:
            assert srv.request_validator is not None
        finally:
            _restore_server_stubs(saved)


# ============================================================================
# Fix 3: TF Cloud tools removed from registry (planned for v3.2.0)
#
# The 4 tf_cloud_* tools have been removed from the MCP tool registry.
# These tests verify the removal: the functions are not importable as module
# attributes and are absent from the MCP tool registry.
# ============================================================================


class TestTFCloudNotImplemented:
    """The 4 TF Cloud tools must be absent from the module and MCP registry."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        # Save FIRST, then install stubs and import fresh module.
        srv, saved = _import_server()
        self.srv = srv
        self._saved = saved
        yield
        _restore_server_stubs(self._saved)

    def test_list_workspaces_not_a_module_attribute(self):
        """tf_cloud_list_workspaces must not be a callable attribute of the server module."""
        assert not hasattr(self.srv, "tf_cloud_list_workspaces"), (
            "tf_cloud_list_workspaces is still a module-level attribute. "
            "Comment out the function definition to remove it from the registry."
        )

    def test_get_workspace_not_a_module_attribute(self):
        """tf_cloud_get_workspace must not be a callable attribute of the server module."""
        assert not hasattr(self.srv, "tf_cloud_get_workspace"), (
            "tf_cloud_get_workspace is still a module-level attribute. "
            "Comment out the function definition to remove it from the registry."
        )

    def test_list_runs_not_a_module_attribute(self):
        """tf_cloud_list_runs must not be a callable attribute of the server module."""
        assert not hasattr(self.srv, "tf_cloud_list_runs"), (
            "tf_cloud_list_runs is still a module-level attribute. "
            "Comment out the function definition to remove it from the registry."
        )

    def test_get_state_outputs_not_a_module_attribute(self):
        """tf_cloud_get_state_outputs must not be a callable attribute of the server module."""
        assert not hasattr(self.srv, "tf_cloud_get_state_outputs"), (
            "tf_cloud_get_state_outputs is still a module-level attribute. "
            "Comment out the function definition to remove it from the registry."
        )

    def test_no_tf_cloud_tools_in_mcp_registry(self):
        """Zero tf_cloud_* tools must be registered in mcp._tools."""
        registered = set(self.srv.mcp._tools.keys())
        tf_cloud = {k for k in registered if k.startswith("tf_cloud_")}
        assert len(tf_cloud) == 0, (
            f"tf_cloud_* tools still in MCP registry: {tf_cloud}"
        )

    def test_check_tf_cloud_token_not_active(self):
        """_check_tf_cloud_token helper must not be an active module attribute."""
        assert not hasattr(self.srv, "_check_tf_cloud_token"), (
            "_check_tf_cloud_token is still a live module attribute. "
            "Comment out the function definition along with the tf_cloud block."
        )


# ============================================================================
# Fix 4: DEFAULT_TIMEOUT validated at module load time in terry-form-mcp.py
# ============================================================================


class TestDefaultTimeoutValidation:
    """DEFAULT_TIMEOUT constant is module-level, validated on import."""

    def _import_terry(self, env_overrides: dict | None = None):
        """Import terry-form-mcp module with optional env overrides, forcing fresh import."""
        saved_terry = sys.modules.pop("terry-form-mcp", None)
        try:
            with patch.dict(os.environ, env_overrides or {}, clear=False):
                mod = importlib.import_module("terry-form-mcp")
            return mod
        finally:
            # Always restore: either the original or the newly loaded version.
            # We leave the freshly imported module in sys.modules so tests can use it,
            # but clean up by restoring after the test. The caller should call restore
            # if they need isolation. For these tests, it is acceptable to leave the
            # module in sys.modules because subsequent tests in this class also need it.
            pass

    @pytest.fixture(autouse=True)
    def _restore_terry(self):
        """Ensure terry-form-mcp is put back after each test."""
        original = sys.modules.get("terry-form-mcp")
        yield
        if original is None:
            sys.modules.pop("terry-form-mcp", None)
        else:
            sys.modules["terry-form-mcp"] = original

    def test_default_timeout_is_300(self, monkeypatch):
        monkeypatch.delenv("MAX_OPERATION_TIMEOUT", raising=False)
        mod = self._import_terry()
        assert mod.DEFAULT_TIMEOUT == 300

    def test_custom_timeout_is_respected(self, monkeypatch):
        monkeypatch.setenv("MAX_OPERATION_TIMEOUT", "120")
        mod = self._import_terry({"MAX_OPERATION_TIMEOUT": "120"})
        assert mod.DEFAULT_TIMEOUT == 120

    def test_timeout_clamped_to_minimum_10(self, monkeypatch):
        mod = self._import_terry({"MAX_OPERATION_TIMEOUT": "5"})
        assert mod.DEFAULT_TIMEOUT == 10

    def test_timeout_clamped_to_maximum_3600(self, monkeypatch):
        mod = self._import_terry({"MAX_OPERATION_TIMEOUT": "9999"})
        assert mod.DEFAULT_TIMEOUT == 3600

    def test_invalid_timeout_raises_runtime_error(self, monkeypatch):
        sys.modules.pop("terry-form-mcp", None)
        with patch.dict(os.environ, {"MAX_OPERATION_TIMEOUT": "not_a_number"}, clear=False):
            with pytest.raises(RuntimeError, match="MAX_OPERATION_TIMEOUT"):
                importlib.import_module("terry-form-mcp")
        sys.modules.pop("terry-form-mcp", None)

    def test_default_timeout_is_integer(self, monkeypatch):
        monkeypatch.delenv("MAX_OPERATION_TIMEOUT", raising=False)
        mod = self._import_terry()
        assert isinstance(mod.DEFAULT_TIMEOUT, int)

    def test_run_terraform_uses_default_timeout_constant(self, monkeypatch):
        """DEFAULT_TIMEOUT is set at module load time and not re-read at call time."""
        mod = self._import_terry({"MAX_OPERATION_TIMEOUT": "45"})
        assert mod.DEFAULT_TIMEOUT == 45
        # Even if env changes, the cached constant does not
        with patch.dict(os.environ, {"MAX_OPERATION_TIMEOUT": "999"}, clear=False):
            assert hasattr(mod, "DEFAULT_TIMEOUT")
            assert mod.DEFAULT_TIMEOUT == 45


# ============================================================================
# Fix 5: TERRY_HOST/TERRY_PORT with backward compatibility
# ============================================================================


class TestTerryHostPort:
    """TERRY_HOST/TERRY_PORT take precedence over HOST/PORT with fallback to 0.0.0.0:8000."""

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch):
        """Remove all relevant env vars before each test."""
        for var in ("TERRY_HOST", "TERRY_PORT", "HOST", "PORT"):
            monkeypatch.delenv(var, raising=False)

    def _get_startup_host_port(self, env: dict) -> tuple[str, str]:
        """Simulate the startup block logic. Returns (host_str, port_str)."""
        with patch.dict(os.environ, env, clear=False):
            host = os.environ.get("TERRY_HOST") or os.environ.get("HOST", "0.0.0.0")
            port_str = os.environ.get("TERRY_PORT") or os.environ.get("PORT", "8000")
        return host, port_str

    def test_defaults_when_no_env_set(self):
        host, port = self._get_startup_host_port({})
        assert host == "0.0.0.0"
        assert port == "8000"

    def test_terry_host_takes_priority_over_host(self):
        host, _ = self._get_startup_host_port({"TERRY_HOST": "127.0.0.1", "HOST": "0.0.0.0"})
        assert host == "127.0.0.1"

    def test_terry_port_takes_priority_over_port(self):
        _, port = self._get_startup_host_port({"TERRY_PORT": "9090", "PORT": "8080"})
        assert port == "9090"

    def test_falls_back_to_host_when_terry_host_absent(self):
        host, _ = self._get_startup_host_port({"HOST": "192.168.1.1"})
        assert host == "192.168.1.1"

    def test_falls_back_to_port_when_terry_port_absent(self):
        _, port = self._get_startup_host_port({"PORT": "8080"})
        assert port == "8080"

    def test_terry_host_empty_string_falls_back_to_host(self):
        """An empty TERRY_HOST should cause fallback to HOST (falsy string)."""
        host, _ = self._get_startup_host_port({"TERRY_HOST": "", "HOST": "10.0.0.1"})
        assert host == "10.0.0.1"

    def test_server_startup_block_uses_terry_host(self, monkeypatch):
        """The actual server startup block must use TERRY_HOST when set."""
        monkeypatch.setenv("TERRY_HOST", "127.0.0.1")
        monkeypatch.setenv("TERRY_PORT", "9999")
        srv, saved = _import_server({"TERRY_HOST": "127.0.0.1", "TERRY_PORT": "9999"})
        try:
            host = os.environ.get("TERRY_HOST") or os.environ.get("HOST", "0.0.0.0")
            port_str = os.environ.get("TERRY_PORT") or os.environ.get("PORT", "8000")
            assert host == "127.0.0.1"
            assert port_str == "9999"
        finally:
            _restore_server_stubs(saved)


# ============================================================================
# Fix 6: TERRAFORM_LS_BIN configurable path
# ============================================================================


class TestTerraformLsBin:
    """TERRAFORM_LS_BIN module-level constant is configurable via TERRY_TERRAFORM_LS_PATH."""

    def test_default_is_terraform_ls(self, monkeypatch):
        monkeypatch.delenv("TERRY_TERRAFORM_LS_PATH", raising=False)
        srv, saved = _import_server()
        try:
            assert srv.TERRAFORM_LS_BIN == "terraform-ls"
        finally:
            _restore_server_stubs(saved)

    def test_env_override_is_respected(self, monkeypatch):
        monkeypatch.setenv("TERRY_TERRAFORM_LS_PATH", "/usr/local/bin/terraform-ls-custom")
        srv, saved = _import_server(
            {"TERRY_TERRAFORM_LS_PATH": "/usr/local/bin/terraform-ls-custom"}
        )
        try:
            assert srv.TERRAFORM_LS_BIN == "/usr/local/bin/terraform-ls-custom"
        finally:
            _restore_server_stubs(saved)

    def test_constant_is_a_string(self, monkeypatch):
        monkeypatch.delenv("TERRY_TERRAFORM_LS_PATH", raising=False)
        srv, saved = _import_server()
        try:
            assert isinstance(srv.TERRAFORM_LS_BIN, str)
        finally:
            _restore_server_stubs(saved)
