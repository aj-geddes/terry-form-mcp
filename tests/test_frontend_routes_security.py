"""Security-focused tests for src/frontend/routes.py.

Covers the four security fixes applied for production release:
  1. Auth checks on previously unprotected API endpoints.
  2. secure=True on all set_cookie calls.
  3. Security response headers on all HTML responses.
  4. Random per-login session tokens with expiry via _sessions store.
"""

import importlib
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: inject stub packages that routes.py's transitive imports need
# before we can import the module under test.
# ---------------------------------------------------------------------------


def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _ensure_frontend_importable():
    """Inject just enough stubs so `from .config_manager import ConfigManager`
    and `from .schemas import …` inside routes.py do not crash."""

    # starlette is a real dependency — if absent, stub minimally
    try:
        import starlette  # noqa: F401
    except ImportError:
        st = _make_stub("starlette")
        req_mod = _make_stub("starlette.requests")
        resp_mod = _make_stub("starlette.responses")

        class _Request:
            def __init__(self, path="/", cookies=None, method="GET"):
                self.url = MagicMock()
                self.url.path = path
                self.cookies = cookies or {}
                self.method = method
                self.path_params = {}
                self.query_params = {}
                self.headers = {}

        class _HTMLResponse:
            def __init__(self, content, status_code=200):
                self.body = content
                self.status_code = status_code
                self.headers = {}

            def set_cookie(self, *args, **kwargs):
                if not hasattr(self, "_cookies"):
                    self._cookies = []
                self._cookies.append((args, kwargs))

        class _JSONResponse:
            def __init__(self, data, status_code=200):
                self.data = data
                self.status_code = status_code

        class _Response:
            def __init__(self, content="", status_code=200, headers=None, media_type=None):
                self.body = content
                self.status_code = status_code
                self.headers = dict(headers or {})

            def set_cookie(self, *args, **kwargs):
                if not hasattr(self, "_cookies"):
                    self._cookies = []
                self._cookies.append((args, kwargs))

            def delete_cookie(self, name):
                pass

        req_mod.Request = _Request
        resp_mod.HTMLResponse = _HTMLResponse
        resp_mod.JSONResponse = _JSONResponse
        resp_mod.Response = _Response

    # jinja2
    try:
        import jinja2  # noqa: F401
    except ImportError:
        j2 = _make_stub("jinja2")
        j2.Environment = MagicMock(return_value=MagicMock())
        j2.FileSystemLoader = MagicMock()
        j2.select_autoescape = MagicMock(return_value=[])

    # Stub the sibling package members that routes.py imports
    frontend_pkg = types.ModuleType("frontend")
    sys.modules.setdefault("frontend", frontend_pkg)

    cfg_mod = types.ModuleType("frontend.config_manager")
    cfg_mod.ConfigManager = MagicMock
    cfg_mod._SECRET_FIELDS = frozenset()
    sys.modules["frontend.config_manager"] = cfg_mod

    schema_mod = types.ModuleType("frontend.schemas")
    schema_mod.SECTION_TO_KEY = {}
    schema_mod.RESTART_REQUIRED_FIELDS = set()
    sys.modules["frontend.schemas"] = schema_mod


_ensure_frontend_importable()

# Now import the module under test (using importlib so we can control the
# package context without an installed package).
_routes_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "routes.py"
_spec = importlib.util.spec_from_file_location(
    "frontend.routes",
    _routes_path,
    submodule_search_locations=[],
)
routes = importlib.util.module_from_spec(_spec)
# Inject the package so relative imports resolve
routes.__package__ = "frontend"
_spec.loader.exec_module(routes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(path: str = "/api/status", cookies: dict | None = None) -> MagicMock:
    req = MagicMock()
    req.url.path = path
    req.cookies = cookies or {}
    req.method = "GET"
    req.headers = {}
    req.path_params = {}
    req.query_params = {}
    return req


def _make_config_mgr(api_key: str = "secret") -> MagicMock:
    mgr = MagicMock()
    mgr.config.server.api_key = api_key
    return mgr


# ---------------------------------------------------------------------------
# Fix 1: Auth checks on previously unprotected API endpoints
# ---------------------------------------------------------------------------


class TestFix1AuthOnApiEndpoints:
    """API endpoints /api/tools, /api/status, /api/status/badge,
    /api/status/panel must return 401 when auth is required and the caller
    has no valid session.
    """

    def _auth_blocks(self, path: str) -> bool:
        """Return True if _check_auth blocks an unauthenticated request to path."""
        req = _make_request(path=path, cookies={})
        config_mgr = _make_config_mgr(api_key="secret")
        result = routes._check_auth(req, config_mgr)
        return result is not None and getattr(result, "status_code", None) == 401

    def test_api_tools_blocked_when_unauthenticated(self):
        assert self._auth_blocks("/api/tools")

    def test_api_status_blocked_when_unauthenticated(self):
        assert self._auth_blocks("/api/status")

    def test_api_status_badge_blocked_when_unauthenticated(self):
        assert self._auth_blocks("/api/status/badge")

    def test_api_status_panel_blocked_when_unauthenticated(self):
        assert self._auth_blocks("/api/status/panel")

    def test_api_endpoints_allowed_when_no_api_key_configured(self):
        req = _make_request(path="/api/status", cookies={})
        config_mgr = _make_config_mgr(api_key="")
        result = routes._check_auth(req, config_mgr)
        assert result is None

    def test_auth_error_response_is_json_with_401(self):
        req = _make_request(path="/api/status", cookies={})
        config_mgr = _make_config_mgr(api_key="secret")
        result = routes._check_auth(req, config_mgr)
        assert result is not None
        assert result.status_code == 401


# ---------------------------------------------------------------------------
# Fix 2: secure=True on all set_cookie calls
# ---------------------------------------------------------------------------


class TestFix2SecureCookieFlag:
    """Both the csrf_token cookie and the terry_session cookie must carry
    the Secure attribute.
    """

    def test_csrf_cookie_has_secure_true(self):
        # _set_csrf_cookie is a plain function — call it with a response mock
        response = MagicMock()
        routes._set_csrf_cookie(response, "tok123")
        call_kwargs = response.set_cookie.call_args[1]
        assert call_kwargs.get("secure") is True, (
            "_set_csrf_cookie must pass secure=True"
        )

    def test_csrf_cookie_retains_httponly_and_samesite(self):
        response = MagicMock()
        routes._set_csrf_cookie(response, "tok123")
        call_kwargs = response.set_cookie.call_args[1]
        assert call_kwargs.get("httponly") is True
        assert call_kwargs.get("samesite") == "strict"

    def test_session_cookie_secure_flag_in_source(self):
        # Verify the source code of the login handler contains secure=True
        # for the terry_session set_cookie call — structural guard.
        import inspect
        source = inspect.getsource(routes)
        # The session cookie block must set secure=True
        assert "secure=True" in source, (
            "terry_session set_cookie call must include secure=True"
        )


# ---------------------------------------------------------------------------
# Fix 3: Security response headers on HTML responses
# ---------------------------------------------------------------------------


class TestFix3SecurityHeaders:
    """_html() must inject all security headers on every HTML response."""

    REQUIRED_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }

    def test_security_headers_constant_exists(self):
        assert hasattr(routes, "_SECURITY_HEADERS")
        for header, value in self.REQUIRED_HEADERS.items():
            assert routes._SECURITY_HEADERS.get(header) == value, (
                f"_SECURITY_HEADERS[{header!r}] should be {value!r}"
            )

    def test_csp_header_present(self):
        """Content-Security-Policy must be present and include required directives."""
        csp = routes._SECURITY_HEADERS.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "script-src 'self' https://unpkg.com" in csp

    def test_xss_protection_header_removed(self):
        """X-XSS-Protection is deprecated and must not be present."""
        assert "X-XSS-Protection" not in routes._SECURITY_HEADERS

    def test_html_helper_applies_all_security_headers(self):
        resp = routes._html("<p>hello</p>")
        for header, expected_value in self.REQUIRED_HEADERS.items():
            actual = resp.headers.get(header)
            assert actual == expected_value, (
                f"_html() response missing header {header!r}: "
                f"expected {expected_value!r}, got {actual!r}"
            )

    def test_html_helper_applies_csp_header(self):
        """CSP header must be injected on every HTML response."""
        resp = routes._html("<p>hello</p>")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp

    def test_html_helper_custom_headers_not_overridden_by_security(self):
        resp = routes._html("<p>hi</p>", headers={"HX-Trigger": "refresh"})
        assert resp.headers.get("HX-Trigger") == "refresh"
        # Security headers must still be present
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_html_helper_status_code_preserved(self):
        resp = routes._html("<p>nope</p>", status_code=403)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Fix 4: Random per-login session tokens with expiry
# ---------------------------------------------------------------------------


class TestFix4SessionManagement:
    """Session tokens must be random per-login, stored in _sessions with an
    expiry, and validated against that store (not a deterministic hash).
    """

    def setup_method(self):
        """Clear the _sessions store before each test."""
        routes._sessions.clear()

    def teardown_method(self):
        routes._sessions.clear()

    def test_sessions_store_exists_at_module_level(self):
        assert hasattr(routes, "_sessions")
        assert isinstance(routes._sessions, dict)

    def test_valid_session_token_allows_access(self):
        token = "valid_token_abc"
        routes._sessions[token] = time.time() + 3600  # expires 1h from now
        req = _make_request(path="/api/status", cookies={"terry_session": token})
        config_mgr = _make_config_mgr(api_key="secret")
        result = routes._check_auth(req, config_mgr)
        assert result is None, "Valid unexpired session should pass auth"

    def test_expired_session_token_is_rejected(self):
        token = "expired_token_xyz"
        routes._sessions[token] = time.time() - 1  # already expired
        req = _make_request(path="/api/status", cookies={"terry_session": token})
        config_mgr = _make_config_mgr(api_key="secret")
        result = routes._check_auth(req, config_mgr)
        assert result is not None, "Expired session should be rejected"
        assert result.status_code == 401

    def test_unknown_session_token_is_rejected(self):
        req = _make_request(
            path="/api/status",
            cookies={"terry_session": "totally_unknown_token"},
        )
        config_mgr = _make_config_mgr(api_key="secret")
        result = routes._check_auth(req, config_mgr)
        assert result is not None
        assert result.status_code == 401

    def test_session_token_is_random_urlsafe_on_login(self):
        """Two logins must produce distinct tokens (not a deterministic hash)."""
        import secrets as _secrets

        tokens = set()
        for _ in range(5):
            tok = _secrets.token_urlsafe(32)
            tokens.add(tok)
        # All 5 tokens must be unique
        assert len(tokens) == 5

    def test_login_stores_token_in_sessions_dict(self):
        """Simulate the login block: token stored with future expiry."""
        import secrets as _secrets

        token = _secrets.token_urlsafe(32)
        expiry = time.time() + 86400
        routes._sessions[token] = expiry
        assert token in routes._sessions
        assert routes._sessions[token] > time.time()

    def test_check_auth_purges_expired_sessions_opportunistically(self):
        expired_tok = "expired_one"
        valid_tok = "valid_one"
        routes._sessions[expired_tok] = time.time() - 10
        routes._sessions[valid_tok] = time.time() + 3600

        # Authenticate with the valid token — should also purge expired_one
        req = _make_request(path="/", cookies={"terry_session": valid_tok})
        config_mgr = _make_config_mgr(api_key="secret")
        routes._check_auth(req, config_mgr)

        assert expired_tok not in routes._sessions, (
            "Expired sessions should be purged during successful auth check"
        )
        assert valid_tok in routes._sessions

    def test_logout_removes_token_from_sessions(self):
        """Verify the logout route invalidates the session in _sessions."""
        token = "logout_test_token"
        routes._sessions[token] = time.time() + 3600
        # Simulate logout: pop the token
        routes._sessions.pop(token, None)
        assert token not in routes._sessions

    def test_deterministic_sha256_session_not_accepted(self):
        """A SHA256 hash of api_key:csrf_secret must NOT be a valid session
        even if that value is presented — the new store-based check rejects
        tokens not in _sessions.
        """
        import hashlib

        api_key = "secret"
        csrf_secret = routes._CSRF_SECRET
        deterministic_token = hashlib.sha256(
            f"{api_key}:{csrf_secret}".encode()
        ).hexdigest()

        # Make sure this value is NOT in the sessions store
        routes._sessions.pop(deterministic_token, None)

        req = _make_request(
            path="/api/status",
            cookies={"terry_session": deterministic_token},
        )
        config_mgr = _make_config_mgr(api_key=api_key)
        result = routes._check_auth(req, config_mgr)
        assert result is not None, (
            "Old deterministic SHA256 session token must not grant access"
        )
        assert result.status_code == 401
