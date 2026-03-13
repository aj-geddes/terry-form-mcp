#!/usr/bin/env python3
"""
Comprehensive tests for the pure-logic infrastructure in server_enhanced_with_lsp.py

Covers:
- RateLimiter: tool categorisation, sliding-window enforcement, window expiry
- AuthManager: API-key authentication, role-based authorisation
- validate_safe_path: workspace-bound path validation
- _pre_validate: auth + rate-limit + path integration gate
- _post_process: metadata injection into results
- validate_request decorator: sync and async function wrapping
"""

import asyncio
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import helpers — the module has top-level side effects (FastMCP creation,
# importlib.import_module("terry-form-mcp"), terraform_lsp_client import).
# We mock what is needed so the classes and functions can be imported cleanly.
#
# IMPORTANT: We snapshot sys.modules before injecting stubs and restore the
# originals once the import is complete.  This prevents stub leakage into
# other test modules that need the real implementations (e.g.
# test_terraform_lsp_client.py importing the real terraform_lsp_client).
# ---------------------------------------------------------------------------

_STUBBED_NAMES = ("fastmcp", "terraform_lsp_client", "terry-form-mcp")
_saved_modules = {name: sys.modules.get(name) for name in _STUBBED_NAMES}

# Patch FastMCP before importing the module so `mcp = FastMCP(...)` succeeds
# without requiring the real fastmcp package or its server machinery.
_fake_fastmcp_mod = types.ModuleType("fastmcp")


class _StubFastMCP:
    """Minimal stand-in for FastMCP that records tool registrations."""

    def __init__(self, *args, **kwargs):
        self._tools = {}

    def tool(self, *args, **kwargs):
        """Return a no-op decorator so @mcp.tool() does not crash."""
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator


_fake_fastmcp_mod.FastMCP = _StubFastMCP  # type: ignore[attr-defined]
sys.modules["fastmcp"] = _fake_fastmcp_mod

# Stub out heavy sibling modules that the server imports at module level
_lsp_stub = types.ModuleType("terraform_lsp_client")
_lsp_stub._lsp_client = None  # type: ignore[attr-defined]
sys.modules["terraform_lsp_client"] = _lsp_stub

# terry-form-mcp is loaded via importlib.import_module inside the server.
# Provide a minimal stub so the import does not fail.
_terry_stub = types.ModuleType("terry-form-mcp")
_terry_stub.run_terraform = MagicMock(return_value={})  # type: ignore[attr-defined]
sys.modules["terry-form-mcp"] = _terry_stub

# Now import the actual components under test
from server_enhanced_with_lsp import (  # noqa: E402
    AuthManager,
    RateLimiter,
    _post_process,
    _pre_validate,
    validate_request,
    validate_safe_path,
)

# Restore original sys.modules entries so stubs do not leak into other
# test modules collected after this one.
for _name in _STUBBED_NAMES:
    _orig = _saved_modules[_name]
    if _orig is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _orig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def limiter():
    """Return a fresh RateLimiter with default configuration."""
    return RateLimiter()


@pytest.fixture
def auth_no_key(monkeypatch):
    """AuthManager with no API key configured (open access)."""
    monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
    return AuthManager()


@pytest.fixture
def auth_with_key(monkeypatch):
    """AuthManager with a known API key configured."""
    monkeypatch.setenv("TERRY_FORM_API_KEY", "test-secret-key-42")
    return AuthManager()


# ---------------------------------------------------------------------------
# 1. RateLimiter — get_tool_category
# ---------------------------------------------------------------------------


class TestRateLimiterCategory:
    """Tests for RateLimiter.get_tool_category()."""

    def test_terry_core_tool(self, limiter):
        """The bare 'terry' tool is categorised as terraform."""
        assert limiter.get_tool_category("terry") == "terraform"

    def test_terry_prefixed_tool(self, limiter):
        """Tools starting with 'terry_' fall into the terraform category."""
        assert limiter.get_tool_category("terry_validate") == "terraform"

    def test_terraform_lsp_tool(self, limiter):
        """Tools starting with 'terraform_' are also terraform-category."""
        assert limiter.get_tool_category("terraform_hover") == "terraform"

    def test_github_tool(self, limiter):
        """Tools starting with 'github_' map to the github category."""
        assert limiter.get_tool_category("github_clone_repo") == "github"

    def test_tf_cloud_tool(self, limiter):
        """Tools starting with 'tf_cloud_' map to the tf_cloud category."""
        assert limiter.get_tool_category("tf_cloud_list_workspaces") == "tf_cloud"

    def test_unknown_tool_defaults(self, limiter):
        """Any unrecognised prefix falls back to 'default'."""
        assert limiter.get_tool_category("something_else") == "default"


# ---------------------------------------------------------------------------
# 2. RateLimiter — is_allowed (sliding window)
# ---------------------------------------------------------------------------


class TestRateLimiterAllowance:
    """Tests for RateLimiter.is_allowed() sliding-window logic."""

    def test_first_request_is_allowed(self, limiter):
        """A fresh limiter allows the very first request."""
        allowed, info = limiter.is_allowed("terry_validate")
        assert allowed is True
        assert info["category"] == "terraform"
        assert info["limit"] == 20

    def test_under_limit_remains_allowed(self, limiter):
        """Multiple requests under the limit are all accepted."""
        for _ in range(19):
            allowed, _ = limiter.is_allowed("terry_validate")
            assert allowed is True

    def test_at_limit_is_rejected(self, limiter):
        """The request that would exceed the limit is rejected."""
        for _ in range(20):
            limiter.is_allowed("terry_validate")

        allowed, info = limiter.is_allowed("terry_validate")
        assert allowed is False
        assert info["remaining"] == 0

    def test_window_expiry_allows_again(self, limiter):
        """After the 60-second window elapses, requests are accepted again."""
        # Fill the terraform bucket (limit 20)
        for _ in range(20):
            limiter.is_allowed("terry_validate")

        # Advance time past the 60-second window
        future = time.time() + 61
        with patch("server_enhanced_with_lsp.time.time", return_value=future):
            allowed, info = limiter.is_allowed("terry_validate")

        assert allowed is True
        assert info["remaining"] >= 0

    def test_categories_are_independent(self, limiter):
        """Exhausting one category does not affect another."""
        # Exhaust terraform (20 requests)
        for _ in range(20):
            limiter.is_allowed("terry_validate")

        # github should still be available
        allowed, info = limiter.is_allowed("github_clone_repo")
        assert allowed is True
        assert info["category"] == "github"

    def test_github_limit_is_30(self, limiter):
        """The github category allows 30 requests per minute."""
        for i in range(30):
            allowed, _ = limiter.is_allowed("github_clone_repo")
            assert allowed is True, f"Request {i+1} should have been allowed"

        allowed, _ = limiter.is_allowed("github_clone_repo")
        assert allowed is False

    def test_default_limit_is_100(self, limiter):
        """The default category allows 100 requests per minute."""
        for _ in range(100):
            allowed, _ = limiter.is_allowed("something_random")
            assert allowed is True

        allowed, _ = limiter.is_allowed("something_random")
        assert allowed is False

    def test_rate_limit_info_structure(self, limiter):
        """The info dict returned by is_allowed has the expected keys."""
        _, info = limiter.is_allowed("terry")
        assert "limit" in info
        assert "remaining" in info
        assert "reset" in info
        assert "category" in info

    def test_remaining_decreases(self, limiter):
        """The 'remaining' count decreases with each allowed request."""
        _, info1 = limiter.is_allowed("terry")
        _, info2 = limiter.is_allowed("terry")
        assert info2["remaining"] < info1["remaining"]

    def test_thread_safety(self, limiter):
        """Concurrent requests do not corrupt internal state."""
        results = []

        def make_request():
            allowed, _ = limiter.is_allowed("terry_validate")
            results.append(allowed)

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(make_request) for _ in range(50)]
            for f in futures:
                f.result()

        allowed_count = sum(1 for r in results if r)
        denied_count = sum(1 for r in results if not r)

        # With a limit of 20, exactly 20 should be allowed
        assert allowed_count == 20
        assert denied_count == 30


# ---------------------------------------------------------------------------
# 3. AuthManager — authenticate
# ---------------------------------------------------------------------------


class TestAuthManagerAuthenticate:
    """Tests for AuthManager.authenticate().

    The authenticate method supports three modes:
    1. No API key configured -> pass-through as anonymous user.
    2. API key provided via HTTP Authorization header (Bearer token) or kwargs.
    3. No key provided and no HTTP headers (stdio transport) -> authenticates as
       stdio_user with the default role, since stdio is inherently authenticated
       by process-level access.
    HTTP transport with key required but not provided -> rejected.
    """

    def test_no_key_configured_allows_anonymous(self, auth_no_key):
        """When no API key is set, all requests pass as anonymous/user."""
        authenticated, user_id, role = auth_no_key.authenticate()
        assert authenticated is True
        assert user_id == "anonymous"
        assert role == "user"

    def test_valid_bearer_token(self, auth_with_key):
        """A correct Bearer token authenticates as admin."""
        headers = {"Authorization": "Bearer test-secret-key-42"}
        authenticated, user_id, role = auth_with_key.authenticate(headers=headers)
        assert authenticated is True
        assert user_id == "api_user"
        assert role == "admin"

    def test_valid_api_key_via_kwargs(self, auth_with_key):
        """A correct api_key in kwargs authenticates as admin (stdio fallback)."""
        authenticated, user_id, role = auth_with_key.authenticate(
            kwargs={"api_key": "test-secret-key-42"}
        )
        assert authenticated is True
        assert user_id == "api_user"
        assert role == "admin"

    def test_invalid_bearer_token(self, auth_with_key):
        """A wrong Bearer token is rejected."""
        headers = {"Authorization": "Bearer wrong-key"}
        authenticated, user_id, role = auth_with_key.authenticate(headers=headers)
        assert authenticated is False
        assert user_id == ""
        assert role == ""

    def test_invalid_api_key_via_kwargs(self, auth_with_key):
        """A wrong api_key in kwargs is rejected."""
        authenticated, _, _ = auth_with_key.authenticate(
            kwargs={"api_key": "wrong-key"}
        )
        assert authenticated is False

    def test_stdio_transport_no_headers_allows_default_role(self, auth_with_key):
        """When API key is configured but no headers/kwargs are provided
        (stdio transport), authentication passes as stdio_user."""
        authenticated, user_id, role = auth_with_key.authenticate()
        assert authenticated is True
        assert user_id == "stdio_user"
        assert role == "user"

    def test_http_transport_missing_token_rejected(self, auth_with_key):
        """HTTP headers present but no Authorization header -> rejected."""
        authenticated, _, _ = auth_with_key.authenticate(headers={"X-Request-Id": "123"})
        assert authenticated is False

    def test_empty_headers_dict_treated_as_stdio(self, auth_with_key):
        """An empty headers dict is falsy in Python, so it is treated the same
        as no headers (stdio transport) and authentication succeeds."""
        authenticated, user_id, _ = auth_with_key.authenticate(headers={})
        assert authenticated is True
        assert user_id == "stdio_user"

    def test_malformed_auth_header(self, auth_with_key):
        """An Authorization header that does not start with 'Bearer ' is not
        extracted, so it falls through to HTTP-with-no-key rejection."""
        headers = {"Authorization": "Basic dXNlcjpwYXNz"}
        authenticated, _, _ = auth_with_key.authenticate(headers=headers)
        assert authenticated is False

    def test_none_headers_allows_stdio(self, auth_with_key):
        """Passing headers=None (the default) with key configured falls through
        to stdio transport, which is allowed."""
        authenticated, user_id, _ = auth_with_key.authenticate(headers=None)
        assert authenticated is True
        assert user_id == "stdio_user"


# ---------------------------------------------------------------------------
# 4. AuthManager — authorize
# ---------------------------------------------------------------------------


class TestAuthManagerAuthorize:
    """Tests for AuthManager.authorize()."""

    def test_admin_accesses_everything(self, auth_no_key):
        """The admin role has wildcard access to any tool."""
        assert auth_no_key.authorize("terry_validate", "admin") is True
        assert auth_no_key.authorize("github_clone_repo", "admin") is True
        assert auth_no_key.authorize("unknown_tool", "admin") is True

    def test_user_accesses_terry_tools(self, auth_no_key):
        """The user role can access terry_* tools."""
        assert auth_no_key.authorize("terry_validate", "user") is True
        assert auth_no_key.authorize("terry_version", "user") is True

    def test_user_accesses_bare_terry(self, auth_no_key):
        """The user role can access the bare 'terry' tool (exact match)."""
        assert auth_no_key.authorize("terry", "user") is True

    def test_user_accesses_github_tools(self, auth_no_key):
        """The user role can access github_* tools."""
        assert auth_no_key.authorize("github_clone_repo", "user") is True

    def test_user_accesses_terraform_lsp_tools(self, auth_no_key):
        """The user role can access terraform_* tools."""
        assert auth_no_key.authorize("terraform_hover", "user") is True

    def test_user_accesses_tf_cloud_tools(self, auth_no_key):
        """The user role can access tf_cloud_* tools."""
        assert auth_no_key.authorize("tf_cloud_list_workspaces", "user") is True

    def test_user_denied_unknown_tool(self, auth_no_key):
        """The user role is denied access to tools outside allowed patterns."""
        assert auth_no_key.authorize("some_random_tool", "user") is False

    def test_readonly_accesses_version(self, auth_no_key):
        """The readonly role can access terry_version."""
        assert auth_no_key.authorize("terry_version", "readonly") is True

    def test_readonly_accesses_environment_check(self, auth_no_key):
        """The readonly role can access terry_environment_check."""
        assert auth_no_key.authorize("terry_environment_check", "readonly") is True

    def test_readonly_accesses_workspace_list(self, auth_no_key):
        """The readonly role can access terry_workspace_list."""
        assert auth_no_key.authorize("terry_workspace_list", "readonly") is True

    def test_readonly_denied_terry_validate(self, auth_no_key):
        """The readonly role cannot access terry_validate."""
        assert auth_no_key.authorize("terry_validate", "readonly") is False

    def test_readonly_denied_github(self, auth_no_key):
        """The readonly role cannot access github_* tools."""
        assert auth_no_key.authorize("github_clone_repo", "readonly") is False

    def test_unknown_role_denied(self, auth_no_key):
        """A role that does not exist in the permissions map is denied."""
        assert auth_no_key.authorize("terry_validate", "hacker") is False


# ---------------------------------------------------------------------------
# 5. validate_safe_path
# ---------------------------------------------------------------------------


class TestValidateSafePath:
    """Tests for validate_safe_path()."""

    def test_relative_path_inside_workspace(self, tmp_path):
        """A simple relative filename resolves inside the workspace."""
        assert validate_safe_path("main.tf", workspace_root=str(tmp_path)) is True

    def test_nested_relative_path(self, tmp_path):
        """A nested relative path stays within workspace bounds."""
        assert validate_safe_path("modules/vpc/main.tf", workspace_root=str(tmp_path)) is True

    def test_path_traversal_rejected(self, tmp_path):
        """Paths containing ../ that escape the workspace are rejected."""
        assert validate_safe_path("../../etc/passwd", workspace_root=str(tmp_path)) is False

    def test_absolute_path_outside_workspace(self, tmp_path):
        """An absolute path outside the workspace is rejected."""
        assert validate_safe_path("/etc/passwd", workspace_root=str(tmp_path)) is False

    def test_absolute_path_inside_workspace(self, tmp_path):
        """An absolute path that resolves within the workspace is allowed."""
        inside = str(tmp_path / "project" / "main.tf")
        assert validate_safe_path(inside, workspace_root=str(tmp_path)) is True

    def test_github_prefix_bypass(self):
        """Paths starting with github:// bypass workspace checks."""
        assert validate_safe_path("github://owner/repo") is True

    def test_workspace_prefix_bypass(self):
        """Paths starting with workspace:// bypass workspace checks."""
        assert validate_safe_path("workspace://my-project") is True

    def test_dot_path_stays_in_workspace(self, tmp_path):
        """The bare '.' path resolves to the workspace root itself."""
        assert validate_safe_path(".", workspace_root=str(tmp_path)) is True

    def test_sneaky_traversal_with_absolute_overlay(self, tmp_path):
        """An absolute path disguised with extra components is rejected."""
        assert validate_safe_path("/tmp/../etc/shadow", workspace_root=str(tmp_path)) is False

    def test_double_dot_in_middle(self, tmp_path):
        """A path that uses .. to land back inside workspace is allowed."""
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True, exist_ok=True)
        assert validate_safe_path("a/b/../../c", workspace_root=str(tmp_path)) is True


# ---------------------------------------------------------------------------
# 6. _pre_validate
# ---------------------------------------------------------------------------


class TestPreValidate:
    """Tests for _pre_validate() integration gate."""

    def test_passes_with_no_key_configured(self, monkeypatch):
        """With no API key set, a basic tool call passes pre-validation."""
        monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
        # Reinitialise the global auth_manager so it picks up the env change
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        original_limiter = mod.rate_limiter
        mod.rate_limiter = RateLimiter()

        try:
            ok, info = _pre_validate("terry_validate", {})
            assert ok is True
            assert info["user_id"] == "anonymous"
            assert info["role"] == "user"
            assert "rate_info" in info
        finally:
            mod.rate_limiter = original_limiter

    def test_stdio_transport_passes_with_key_configured(self, monkeypatch):
        """When an API key is configured but no key is provided (stdio transport),
        _pre_validate succeeds because stdio is inherently authenticated."""
        monkeypatch.setenv("TERRY_FORM_API_KEY", "secret")
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()

        try:
            ok, info = _pre_validate("terry_validate", {})
            assert ok is True
            assert info["user_id"] == "stdio_user"
        finally:
            monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
            mod.auth_manager = AuthManager()
            mod.rate_limiter = RateLimiter()

    def test_fails_when_invalid_api_key_provided(self, monkeypatch):
        """When an explicit but wrong api_key is provided, pre-validation fails."""
        monkeypatch.setenv("TERRY_FORM_API_KEY", "secret")
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()

        try:
            ok, info = _pre_validate("terry_validate", {"api_key": "wrong"})
            assert ok is False
            assert "error" in info
            assert "Authentication" in info["error"]
        finally:
            monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
            mod.auth_manager = AuthManager()
            mod.rate_limiter = RateLimiter()

    def test_fails_on_rate_limit(self, monkeypatch):
        """Pre-validation fails when the rate limit is exhausted."""
        monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()

        try:
            # Exhaust the terraform bucket (limit 20)
            for _ in range(20):
                mod.rate_limiter.is_allowed("terry_validate")

            ok, info = _pre_validate("terry_validate", {})
            assert ok is False
            assert "Rate limit" in info["error"]
        finally:
            mod.rate_limiter = RateLimiter()

    def test_rejects_unsafe_path_key(self, monkeypatch, tmp_path):
        """Pre-validation rejects kwargs containing unsafe paths."""
        monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()
        # Disable request_validator so only path check matters
        saved_validator = mod.request_validator
        mod.request_validator = None

        try:
            ok, info = _pre_validate(
                "terry_validate",
                {"path": "/etc/passwd"},
            )
            assert ok is False
            assert "Invalid path" in info["error"]
        finally:
            mod.request_validator = saved_validator
            mod.rate_limiter = RateLimiter()

    def test_checks_all_four_path_keys(self, monkeypatch):
        """Pre-validation scans path, file_path, workspace_path, and config_path."""
        monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()
        saved_validator = mod.request_validator
        mod.request_validator = None

        try:
            for key in ("path", "file_path", "workspace_path", "config_path"):
                mod.rate_limiter = RateLimiter()  # reset between iterations
                ok, info = _pre_validate(
                    "terry_validate",
                    {key: "../../etc/shadow"},
                )
                assert ok is False, f"Expected rejection for key '{key}'"
                assert key in info["error"]
        finally:
            mod.request_validator = saved_validator
            mod.rate_limiter = RateLimiter()

    def test_valid_request_passes_through(self, monkeypatch, tmp_path):
        """A well-formed request passes all validation stages."""
        monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()
        saved_validator = mod.request_validator
        mod.request_validator = None

        try:
            ok, info = _pre_validate("terry_validate", {"path": "github://owner/repo"})
            assert ok is True
            assert info["user_id"] == "anonymous"
        finally:
            mod.request_validator = saved_validator
            mod.rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# 7. _post_process
# ---------------------------------------------------------------------------


class TestPostProcess:
    """Tests for _post_process() metadata injection."""

    def test_injects_metadata_into_dict(self):
        """A dict result receives _rate_limit and _auth metadata."""
        info = {
            "user_id": "anonymous",
            "role": "user",
            "rate_info": {"limit": 20, "remaining": 19, "reset": 9999, "category": "terraform"},
        }
        result = {"status": "ok"}
        processed = _post_process(result, info)

        assert processed["_rate_limit"] == info["rate_info"]
        assert processed["_auth"]["user"] == "anonymous"
        assert processed["_auth"]["role"] == "user"
        # Original keys preserved
        assert processed["status"] == "ok"

    def test_non_dict_result_passes_through(self):
        """Non-dict results (string, list, None) are returned unchanged."""
        info = {
            "user_id": "u",
            "role": "admin",
            "rate_info": {},
        }
        assert _post_process("hello", info) == "hello"
        assert _post_process([1, 2, 3], info) == [1, 2, 3]
        assert _post_process(None, info) is None

    def test_modifies_result_in_place(self):
        """The function mutates and returns the same dict object."""
        info = {
            "user_id": "u",
            "role": "r",
            "rate_info": {"x": 1},
        }
        original = {"key": "value"}
        processed = _post_process(original, info)
        assert processed is original


# ---------------------------------------------------------------------------
# 8. validate_request decorator
# ---------------------------------------------------------------------------


class TestValidateRequestDecorator:
    """Tests for the validate_request() decorator factory."""

    def _setup_open_auth(self, monkeypatch):
        """Configure globals for open (no-key) authentication."""
        monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()
        saved_validator = mod.request_validator
        mod.request_validator = None
        return mod, saved_validator

    def _teardown(self, mod, saved_validator):
        """Restore globals after a test."""
        mod.request_validator = saved_validator
        mod.rate_limiter = RateLimiter()

    def test_wraps_sync_function(self, monkeypatch):
        """The decorator wraps a synchronous function and injects metadata."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terry_validate")
            def my_tool(path: str = "."):
                return {"result": "success"}

            result = my_tool(path="github://test/repo")
            assert result["result"] == "success"
            assert "_rate_limit" in result
            assert "_auth" in result
        finally:
            self._teardown(mod, saved)

    def test_wraps_async_function(self, monkeypatch):
        """The decorator wraps an async function and injects metadata."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terraform_hover")
            async def my_async_tool(file_path: str = "."):
                return {"hover": "info"}

            result = asyncio.run(
                my_async_tool(file_path="github://test/repo")
            )
            assert result["hover"] == "info"
            assert "_rate_limit" in result
        finally:
            self._teardown(mod, saved)

    def test_decorator_returns_error_on_auth_failure(self, monkeypatch):
        """When auth fails (wrong api_key), the decorated function returns an error dict."""
        monkeypatch.setenv("TERRY_FORM_API_KEY", "secret")
        import server_enhanced_with_lsp as mod
        mod.auth_manager = AuthManager()
        mod.rate_limiter = RateLimiter()
        saved_validator = mod.request_validator
        mod.request_validator = None

        try:
            @validate_request("terry_validate")
            def guarded_tool(api_key: str = ""):
                return {"should": "not reach"}

            result = guarded_tool(api_key="wrong-key")
            assert "error" in result
            assert "Authentication" in result["error"]
        finally:
            monkeypatch.delenv("TERRY_FORM_API_KEY", raising=False)
            mod.auth_manager = AuthManager()
            mod.request_validator = saved_validator
            mod.rate_limiter = RateLimiter()

    def test_decorator_catches_tool_exception(self, monkeypatch):
        """If the wrapped function raises, the decorator returns an error dict."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terry_validate")
            def failing_tool():
                raise RuntimeError("boom")

            result = failing_tool()
            assert "error" in result
            assert "boom" in result["error"]
        finally:
            self._teardown(mod, saved)

    def test_async_decorator_catches_tool_exception(self, monkeypatch):
        """If the wrapped async function raises, the decorator returns an error dict."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terraform_hover")
            async def failing_async_tool():
                raise ValueError("async boom")

            result = asyncio.run(
                failing_async_tool()
            )
            assert "error" in result
            assert "async boom" in result["error"]
        finally:
            self._teardown(mod, saved)

    def test_preserves_function_name(self, monkeypatch):
        """functools.wraps preserves the original function name."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terry_validate")
            def my_named_function():
                return {}

            assert my_named_function.__name__ == "my_named_function"
        finally:
            self._teardown(mod, saved)

    def test_preserves_async_function_name(self, monkeypatch):
        """functools.wraps preserves the original async function name."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terraform_hover")
            async def my_async_named():
                return {}

            assert my_async_named.__name__ == "my_async_named"
        finally:
            self._teardown(mod, saved)

    def test_non_dict_result_not_modified(self, monkeypatch):
        """When the tool returns a non-dict, no metadata is injected."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terry_version")
            def string_tool():
                return "v3.1.0"

            result = string_tool()
            assert result == "v3.1.0"
        finally:
            self._teardown(mod, saved)

    def test_rate_limit_rejection_through_decorator(self, monkeypatch):
        """Exhausting the rate limit causes the decorator to return an error."""
        mod, saved = self._setup_open_auth(monkeypatch)

        try:
            @validate_request("terry_validate")
            def limited_tool():
                return {"ok": True}

            # Exhaust terraform limit (20)
            for _ in range(20):
                mod.rate_limiter.is_allowed("terry_validate")

            result = limited_tool()
            assert "error" in result
            assert "Rate limit" in result["error"]
        finally:
            self._teardown(mod, saved)
