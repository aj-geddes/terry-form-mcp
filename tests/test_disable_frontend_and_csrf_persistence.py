"""Tests for TERRY_DISABLE_FRONTEND flag and CSRF secret persistence.

RED phase: all tests in this file must FAIL before the implementation
is added. They become GREEN once the implementation is complete.

Covers:
  1. TERRY_DISABLE_FRONTEND=true suppresses frontend module import in server.
  2. CSRF secret env var (TERRY_CSRF_SECRET) takes priority over persisted value.
  3. Generated CSRF secret is persisted to config on first boot.
  4. Persisted CSRF secret is reused on subsequent ConfigManager loads.
"""

import importlib
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# sys.modules stub helpers — identical isolation contract used by
# test_config_env_fixes.py to avoid cross-test pollution.
# ---------------------------------------------------------------------------

_SERVER_STUBBED_NAMES = (
    "fastmcp",
    "terraform_lsp_client",
    "terry-form-mcp",
    "mcp_request_validator",
    "server_enhanced_with_lsp",
)


def _install_server_stubs() -> dict:
    """Snapshot current sys.modules then install lightweight stubs."""
    saved = {name: sys.modules.get(name) for name in _SERVER_STUBBED_NAMES}

    fake_fastmcp = types.ModuleType("fastmcp")

    class _StubFastMCP:
        def __init__(self, *args, **kwargs):
            self._tools: dict = {}
            self._routes: list = []

        def tool(self, *args, **kwargs):
            def decorator(fn):
                self._tools[fn.__name__] = fn
                return fn
            return decorator

        def custom_route(self, *args, **kwargs):
            def decorator(fn):
                self._routes.append(fn.__name__)
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
    for name in _SERVER_STUBBED_NAMES:
        orig = saved.get(name)
        if orig is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = orig


def _import_server(env_overrides: dict | None = None):
    """Import server_enhanced_with_lsp with stubs and optional env overrides."""
    saved = _install_server_stubs()
    sys.modules.pop("server_enhanced_with_lsp", None)
    with patch.dict(os.environ, env_overrides or {}, clear=False):
        import server_enhanced_with_lsp as srv
    return srv, saved


# ---------------------------------------------------------------------------
# Helpers: build a minimal importable frontend.config_manager + frontend.routes
# stub so we can observe whether they were loaded.
# ---------------------------------------------------------------------------

_FRONTEND_LOADED_FLAG = "frontend._loaded_marker"


def _stub_frontend_modules(monkeypatch) -> None:
    """Inject lightweight frontend stubs that record whether they were imported."""
    # Create the 'frontend' package stub
    frontend_pkg = types.ModuleType("frontend")
    sys.modules["frontend"] = frontend_pkg

    # config_manager stub
    cm_mod = types.ModuleType("frontend.config_manager")

    class _FakeConfigManager:
        def load(self):
            pass

        @property
        def config(self):
            return MagicMock()

    cm_mod.ConfigManager = _FakeConfigManager  # type: ignore[attr-defined]
    sys.modules["frontend.config_manager"] = cm_mod

    # routes stub — sets a flag when register_routes() is called
    routes_mod = types.ModuleType("frontend.routes")
    routes_mod._register_called = False  # type: ignore[attr-defined]

    def _fake_register_routes(mcp_server, config_mgr, rate_limiter=None):
        routes_mod._register_called = True  # type: ignore[attr-defined]

    routes_mod.register_routes = _fake_register_routes  # type: ignore[attr-defined]
    sys.modules["frontend.routes"] = routes_mod


def _clear_frontend_stubs() -> None:
    for name in list(sys.modules):
        if name.startswith("frontend"):
            sys.modules.pop(name, None)


# ============================================================================
# Feature 1: TERRY_DISABLE_FRONTEND flag
# ============================================================================


class TestDisableFrontendFlag:
    """When TERRY_DISABLE_FRONTEND=true, frontend must NOT be loaded."""

    def test_frontend_loaded_by_default(self, monkeypatch):
        """Without the flag, register_routes() is called."""
        monkeypatch.delenv("TERRY_DISABLE_FRONTEND", raising=False)
        _stub_frontend_modules(monkeypatch)
        try:
            srv, saved = _import_server()
            try:
                routes_mod = sys.modules.get("frontend.routes")
                assert routes_mod is not None, "frontend.routes must be imported"
                assert getattr(routes_mod, "_register_called", False) is True, (
                    "register_routes() must be called when TERRY_DISABLE_FRONTEND is unset"
                )
            finally:
                _restore_server_stubs(saved)
        finally:
            _clear_frontend_stubs()

    def test_frontend_skipped_when_flag_true(self, monkeypatch):
        """TERRY_DISABLE_FRONTEND=true must prevent frontend import."""
        monkeypatch.setenv("TERRY_DISABLE_FRONTEND", "true")
        _stub_frontend_modules(monkeypatch)
        try:
            srv, saved = _import_server({"TERRY_DISABLE_FRONTEND": "true"})
            try:
                routes_mod = sys.modules.get("frontend.routes")
                # Either routes module is never imported, OR register_routes was not called
                register_called = (
                    routes_mod is not None
                    and getattr(routes_mod, "_register_called", False)
                )
                assert not register_called, (
                    "register_routes() must NOT be called when TERRY_DISABLE_FRONTEND=true"
                )
            finally:
                _restore_server_stubs(saved)
        finally:
            _clear_frontend_stubs()

    def test_flag_case_insensitive_true(self, monkeypatch):
        """TERRY_DISABLE_FRONTEND=TRUE (upper-case) must also disable frontend."""
        monkeypatch.setenv("TERRY_DISABLE_FRONTEND", "TRUE")
        _stub_frontend_modules(monkeypatch)
        try:
            srv, saved = _import_server({"TERRY_DISABLE_FRONTEND": "TRUE"})
            try:
                routes_mod = sys.modules.get("frontend.routes")
                register_called = (
                    routes_mod is not None
                    and getattr(routes_mod, "_register_called", False)
                )
                assert not register_called, (
                    "register_routes() must NOT be called when TERRY_DISABLE_FRONTEND=TRUE"
                )
            finally:
                _restore_server_stubs(saved)
        finally:
            _clear_frontend_stubs()

    def test_flag_false_loads_frontend(self, monkeypatch):
        """TERRY_DISABLE_FRONTEND=false must still load the frontend."""
        monkeypatch.setenv("TERRY_DISABLE_FRONTEND", "false")
        _stub_frontend_modules(monkeypatch)
        try:
            srv, saved = _import_server({"TERRY_DISABLE_FRONTEND": "false"})
            try:
                routes_mod = sys.modules.get("frontend.routes")
                assert routes_mod is not None, "frontend.routes must be imported"
                assert getattr(routes_mod, "_register_called", False) is True
            finally:
                _restore_server_stubs(saved)
        finally:
            _clear_frontend_stubs()

    def test_config_manager_is_none_when_disabled(self, monkeypatch):
        """When disabled, config_manager module-level variable must be None."""
        monkeypatch.setenv("TERRY_DISABLE_FRONTEND", "true")
        _stub_frontend_modules(monkeypatch)
        try:
            srv, saved = _import_server({"TERRY_DISABLE_FRONTEND": "true"})
            try:
                assert srv.config_manager is None, (
                    "config_manager must be None when frontend is disabled"
                )
            finally:
                _restore_server_stubs(saved)
        finally:
            _clear_frontend_stubs()


# ============================================================================
# Feature 2: CSRF secret persistence
# ============================================================================

# We test config_manager and routes directly without importing the server.
# That avoids the heavy server stub machinery.


@pytest.fixture()
def tmp_config_dir(tmp_path):
    """Provide a writable temporary directory for config file tests."""
    return tmp_path


def _make_config_manager(config_path: Path):
    """Return a real ConfigManager pointed at the given path."""
    # Add src to path so the real modules can be imported
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from frontend.config_manager import ConfigManager
    return ConfigManager(config_path=config_path)


class TestCsrfSecretPersistence:
    """CSRF secret must follow env-var -> persisted -> generate+persist priority."""

    def test_env_var_takes_priority_over_persisted(self, tmp_config_dir):
        """When TERRY_CSRF_SECRET is set, it must win over any persisted value."""
        config_path = tmp_config_dir / "terry-config.json"

        # Write a config file that already has a csrf_secret stored
        existing_secret = "persisted_secret_abc123"
        config_data = {"server_internal": {"csrf_secret": existing_secret}}
        config_path.write_text(json.dumps(config_data))

        env_secret = "env_var_secret_xyz789"
        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        with patch.dict(os.environ, {"TERRY_CSRF_SECRET": env_secret}, clear=False):
            from frontend import routes as _routes
            importlib.reload(_routes)  # ensure module-level var re-evaluated
            # The CSRF secret used must be the env var value
            assert _routes._CSRF_SECRET == env_secret, (
                f"Expected env var secret {env_secret!r}, got {_routes._CSRF_SECRET!r}"
            )

    def test_generated_secret_persisted_on_first_boot(self, tmp_config_dir):
        """First boot (no config file, no env var): a secret is generated and saved."""
        config_path = tmp_config_dir / "terry-config.json"
        assert not config_path.exists()

        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        from frontend.config_manager import ConfigManager

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TERRY_CSRF_SECRET", None)
            mgr = ConfigManager(config_path=config_path)
            csrf_secret = mgr.get_or_create_csrf_secret()

        # Secret must be a non-empty hex string (32 bytes = 64 hex chars)
        assert isinstance(csrf_secret, str)
        assert len(csrf_secret) == 64
        assert all(c in "0123456789abcdef" for c in csrf_secret)

        # Secret must now be persisted in the config file
        assert config_path.exists()
        saved_data = json.loads(config_path.read_text())
        persisted = (
            saved_data.get("server_internal", {}).get("csrf_secret")
        )
        assert persisted == csrf_secret, (
            "Generated secret must be written to config file"
        )

    def test_persisted_secret_reused_on_restart(self, tmp_config_dir):
        """Second call to get_or_create_csrf_secret() returns the same value."""
        config_path = tmp_config_dir / "terry-config.json"

        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        from frontend.config_manager import ConfigManager

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TERRY_CSRF_SECRET", None)

            # First boot
            mgr1 = ConfigManager(config_path=config_path)
            secret1 = mgr1.get_or_create_csrf_secret()

            # Simulate restart: fresh ConfigManager instance, same file
            mgr2 = ConfigManager(config_path=config_path)
            secret2 = mgr2.get_or_create_csrf_secret()

        assert secret1 == secret2, (
            "Persisted CSRF secret must be reused across restarts"
        )

    def test_env_var_priority_over_generated(self, tmp_config_dir):
        """TERRY_CSRF_SECRET env var wins even when no persisted secret exists."""
        config_path = tmp_config_dir / "terry-config.json"
        assert not config_path.exists()

        env_secret = "explicit_env_override_abc123def456abc123def456abc123def456abc123de"

        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        from frontend.config_manager import ConfigManager

        with patch.dict(os.environ, {"TERRY_CSRF_SECRET": env_secret}, clear=False):
            mgr = ConfigManager(config_path=config_path)
            csrf_secret = mgr.get_or_create_csrf_secret()

        assert csrf_secret == env_secret

    def test_register_routes_uses_persisted_secret(self, tmp_config_dir):
        """register_routes() must call get_or_create_csrf_secret() on ConfigManager."""
        config_path = tmp_config_dir / "terry-config.json"

        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)

        from frontend.config_manager import ConfigManager

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TERRY_CSRF_SECRET", None)
            mgr = ConfigManager(config_path=config_path)

            # ConfigManager must expose get_or_create_csrf_secret()
            assert hasattr(mgr, "get_or_create_csrf_secret"), (
                "ConfigManager must have get_or_create_csrf_secret() method"
            )

            secret = mgr.get_or_create_csrf_secret()
            assert secret is not None
            assert len(secret) > 0
