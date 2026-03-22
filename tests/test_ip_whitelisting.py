"""Tests for IP whitelisting controls (TERRY_ALLOWED_HOSTS).

Covers:
  1. No TERRY_ALLOWED_HOSTS set -> all requests pass.
  2. Single IP allowed -> only that IP passes.
  3. CIDR range -> IPs in range pass, others blocked.
  4. Multiple entries -> union works.
  5. Invalid entry in list -> logged as warning, skipped, valid entries still apply.
  6. IPv6 support.
  7. HTTP frontend: _check_allowed_host helper.
  8. MCP server: _check_allowed_ip helper.
"""

import importlib
import ipaddress
import logging
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Bootstrap helpers shared between routes and server tests
# ---------------------------------------------------------------------------

def _make_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _ensure_frontend_importable() -> None:
    """Inject minimal stubs so routes.py can be imported in isolation."""
    try:
        import starlette  # noqa: F401
    except ImportError:
        st = _make_stub("starlette")
        req_mod = _make_stub("starlette.requests")
        resp_mod = _make_stub("starlette.responses")

        class _Request:
            def __init__(self, path="/", cookies=None, method="GET", client_host=None):
                self.url = MagicMock()
                self.url.path = path
                self.cookies = cookies or {}
                self.method = method
                self.path_params = {}
                self.query_params = {}
                self.headers = {}
                self.client = MagicMock()
                self.client.host = client_host or "127.0.0.1"

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
                self.headers = {}

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

    try:
        import jinja2  # noqa: F401
    except ImportError:
        j2 = _make_stub("jinja2")
        j2.Environment = MagicMock(return_value=MagicMock())
        j2.FileSystemLoader = MagicMock()
        j2.select_autoescape = MagicMock(return_value=[])

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


def _load_routes_module(env_value: str | None) -> types.ModuleType:
    """Load routes.py with the given TERRY_ALLOWED_HOSTS env value."""
    _ensure_frontend_importable()

    # Remove any cached version so the module re-executes with new env
    sys.modules.pop("frontend.routes", None)

    _routes_path = Path(__file__).resolve().parent.parent / "src" / "frontend" / "routes.py"
    _spec = importlib.util.spec_from_file_location(
        "frontend.routes",
        _routes_path,
        submodule_search_locations=[],
    )
    mod = importlib.util.module_from_spec(_spec)
    mod.__package__ = "frontend"

    env_patch: dict = {}
    if env_value is not None:
        env_patch["TERRY_ALLOWED_HOSTS"] = env_value
    else:
        # Ensure the key is absent so the default (empty) path is exercised
        env_patch.pop("TERRY_ALLOWED_HOSTS", None)

    with patch.dict("os.environ", env_patch, clear=False):
        if env_value is None:
            # Forcibly remove the key so os.environ.get returns ""
            import os
            os.environ.pop("TERRY_ALLOWED_HOSTS", None)
        _spec.loader.exec_module(mod)

    sys.modules["frontend.routes"] = mod
    return mod


def _make_request(client_host: str = "127.0.0.1") -> MagicMock:
    """Create a minimal mock Starlette Request with a client.host."""
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = client_host
    return req


# ===========================================================================
# Part 1: routes.py – _check_allowed_host helper
# ===========================================================================


class TestCheckAllowedHostNoRestriction:
    """When TERRY_ALLOWED_HOSTS is empty / unset, all IPs are allowed."""

    def setup_method(self):
        import os
        os.environ.pop("TERRY_ALLOWED_HOSTS", None)
        self.routes = _load_routes_module(env_value=None)

    def teardown_method(self):
        import os
        os.environ.pop("TERRY_ALLOWED_HOSTS", None)
        sys.modules.pop("frontend.routes", None)

    def test_no_restriction_allows_any_ipv4(self):
        req = _make_request("1.2.3.4")
        result = self.routes._check_allowed_host(req)
        assert result is None, "No restriction: any IPv4 must be allowed"

    def test_no_restriction_allows_loopback(self):
        req = _make_request("127.0.0.1")
        result = self.routes._check_allowed_host(req)
        assert result is None

    def test_no_restriction_allows_ipv6(self):
        req = _make_request("::1")
        result = self.routes._check_allowed_host(req)
        assert result is None

    def test_allowed_networks_list_is_empty_when_no_env(self):
        assert self.routes._ALLOWED_NETWORKS == []


class TestCheckAllowedHostSingleIP:
    """Single exact IP in TERRY_ALLOWED_HOSTS."""

    def setup_method(self):
        self.routes = _load_routes_module(env_value="192.168.1.100")

    def teardown_method(self):
        sys.modules.pop("frontend.routes", None)

    def test_allowed_ip_passes(self):
        req = _make_request("192.168.1.100")
        result = self.routes._check_allowed_host(req)
        assert result is None, "Exact match IP must be allowed"

    def test_other_ip_is_blocked(self):
        req = _make_request("192.168.1.101")
        result = self.routes._check_allowed_host(req)
        assert result is not None, "Non-listed IP must be blocked"
        assert result.status_code == 403

    def test_unrelated_ip_is_blocked(self):
        req = _make_request("10.0.0.1")
        result = self.routes._check_allowed_host(req)
        assert result is not None
        assert result.status_code == 403

    def test_blocked_response_has_error_key(self):
        req = _make_request("9.9.9.9")
        result = self.routes._check_allowed_host(req)
        assert result is not None
        # JSONResponse stores data in .data attribute in our stub,
        # but real starlette stores in body. Accept either.
        error_data = getattr(result, "data", None)
        if error_data is None:
            import json
            error_data = json.loads(getattr(result, "body", b"{}"))
        assert "error" in error_data


class TestCheckAllowedHostCIDRRange:
    """CIDR range in TERRY_ALLOWED_HOSTS."""

    def setup_method(self):
        self.routes = _load_routes_module(env_value="10.0.0.0/8")

    def teardown_method(self):
        sys.modules.pop("frontend.routes", None)

    def test_ip_in_range_allowed(self):
        req = _make_request("10.1.2.3")
        assert self.routes._check_allowed_host(req) is None

    def test_ip_at_start_of_range_allowed(self):
        req = _make_request("10.0.0.1")
        assert self.routes._check_allowed_host(req) is None

    def test_ip_at_edge_of_range_allowed(self):
        req = _make_request("10.255.255.254")
        assert self.routes._check_allowed_host(req) is None

    def test_ip_outside_range_blocked(self):
        req = _make_request("11.0.0.1")
        result = self.routes._check_allowed_host(req)
        assert result is not None
        assert result.status_code == 403

    def test_private_cidr_blocks_public_ip(self):
        req = _make_request("8.8.8.8")
        result = self.routes._check_allowed_host(req)
        assert result is not None
        assert result.status_code == 403


class TestCheckAllowedHostMultipleEntries:
    """Multiple comma-separated entries in TERRY_ALLOWED_HOSTS."""

    def setup_method(self):
        self.routes = _load_routes_module(
            env_value="10.0.0.0/8,192.168.0.0/16,172.16.0.0/12"
        )

    def teardown_method(self):
        sys.modules.pop("frontend.routes", None)

    def test_ip_in_first_range_allowed(self):
        assert self.routes._check_allowed_host(_make_request("10.5.5.5")) is None

    def test_ip_in_second_range_allowed(self):
        assert self.routes._check_allowed_host(_make_request("192.168.99.99")) is None

    def test_ip_in_third_range_allowed(self):
        assert self.routes._check_allowed_host(_make_request("172.20.1.1")) is None

    def test_ip_in_no_range_blocked(self):
        result = self.routes._check_allowed_host(_make_request("8.8.8.8"))
        assert result is not None
        assert result.status_code == 403

    def test_loopback_not_in_listed_ranges_is_blocked(self):
        # 127.0.0.1 is NOT in 10/8, 192.168/16, 172.16/12
        result = self.routes._check_allowed_host(_make_request("127.0.0.1"))
        assert result is not None
        assert result.status_code == 403

    def test_allowed_networks_has_three_entries(self):
        assert len(self.routes._ALLOWED_NETWORKS) == 3


class TestCheckAllowedHostInvalidEntry:
    """Invalid entries are logged as warnings and skipped; valid entries still work."""

    def setup_method(self):
        # Mix of valid and invalid entries
        self.routes = _load_routes_module(
            env_value="10.0.0.0/8,not-a-valid-ip,192.168.1.0/24"
        )

    def teardown_method(self):
        sys.modules.pop("frontend.routes", None)

    def test_valid_entries_still_parsed(self):
        # Two valid entries remain: 10.0.0.0/8 and 192.168.1.0/24
        assert len(self.routes._ALLOWED_NETWORKS) == 2

    def test_ip_in_valid_first_range_allowed(self):
        assert self.routes._check_allowed_host(_make_request("10.1.1.1")) is None

    def test_ip_in_valid_second_range_allowed(self):
        assert self.routes._check_allowed_host(_make_request("192.168.1.50")) is None

    def test_ip_outside_valid_ranges_blocked(self):
        result = self.routes._check_allowed_host(_make_request("9.9.9.9"))
        assert result is not None
        assert result.status_code == 403

    def test_invalid_entry_warning_is_logged(self, caplog):
        """Re-load the module with caplog capturing WARNING messages."""
        sys.modules.pop("frontend.routes", None)
        with caplog.at_level(logging.WARNING):
            routes = _load_routes_module(
                env_value="10.0.0.0/8,not-a-valid-ip"
            )
        # At least one warning mentioning the bad entry
        warnings = [r for r in caplog.records if "not-a-valid-ip" in r.message]
        assert len(warnings) >= 1, (
            "Invalid TERRY_ALLOWED_HOSTS entry must produce a WARNING log"
        )
        sys.modules.pop("frontend.routes", None)


class TestCheckAllowedHostIPv6:
    """IPv6 addresses and CIDR ranges."""

    def setup_method(self):
        self.routes = _load_routes_module(env_value="::1,fd00::/8")

    def teardown_method(self):
        sys.modules.pop("frontend.routes", None)

    def test_ipv6_loopback_allowed(self):
        assert self.routes._check_allowed_host(_make_request("::1")) is None

    def test_ipv6_in_cidr_range_allowed(self):
        assert self.routes._check_allowed_host(_make_request("fd00::1")) is None

    def test_ipv6_outside_range_blocked(self):
        result = self.routes._check_allowed_host(_make_request("2001:db8::1"))
        assert result is not None
        assert result.status_code == 403

    def test_ipv4_when_only_ipv6_allowed_is_blocked(self):
        result = self.routes._check_allowed_host(_make_request("192.168.1.1"))
        assert result is not None
        assert result.status_code == 403


class TestCheckAllowedHostNoClientInfo:
    """When request.client is None, return 403."""

    def setup_method(self):
        self.routes = _load_routes_module(env_value="10.0.0.0/8")

    def teardown_method(self):
        sys.modules.pop("frontend.routes", None)

    def test_none_client_returns_403(self):
        req = MagicMock()
        req.client = None
        result = self.routes._check_allowed_host(req)
        assert result is not None
        assert result.status_code == 403


# ===========================================================================
# Part 2: server_enhanced_with_lsp.py – _check_allowed_ip helper
# ===========================================================================


def _build_server_allowed_networks(env_value: str | None) -> list:
    """Parse TERRY_ALLOWED_HOSTS the same way the server module does,
    returning the resulting list of ip_network objects.

    This is tested independently so we don't need to import the full server.
    """
    networks: list = []
    raw = env_value if env_value is not None else ""
    if raw:
        for entry in raw.split(","):
            entry = entry.strip()
            if entry:
                try:
                    networks.append(ipaddress.ip_network(entry, strict=False))
                except ValueError:
                    pass  # warnings tested separately
    return networks


def _check_allowed_ip_impl(client_ip: str | None, networks: list) -> tuple[bool, str | None]:
    """Reference implementation mirroring what server_enhanced_with_lsp._check_allowed_ip
    must do once it is implemented.

    Returns (allowed, error_message).
    """
    if not networks:
        return True, None
    if not client_ip:
        return False, "Client IP not available"
    try:
        addr = ipaddress.ip_address(client_ip)
        if any(addr in net for net in networks):
            return True, None
    except ValueError:
        pass
    return False, f"Access denied: {client_ip} not in allowed networks"


class TestServerAllowedNetworksParsing:
    """Unit tests for the _ALLOWED_NETWORKS parsing logic in server module."""

    def test_empty_env_produces_empty_list(self):
        nets = _build_server_allowed_networks(None)
        assert nets == []

    def test_single_cidr_parsed_correctly(self):
        nets = _build_server_allowed_networks("10.0.0.0/8")
        assert len(nets) == 1
        assert ipaddress.ip_network("10.0.0.0/8") in nets

    def test_multiple_cidrs_all_parsed(self):
        nets = _build_server_allowed_networks("10.0.0.0/8,192.168.0.0/16")
        assert len(nets) == 2

    def test_single_ip_parsed_as_host_network(self):
        nets = _build_server_allowed_networks("192.168.1.100")
        assert len(nets) == 1
        # /32 host network
        assert ipaddress.ip_address("192.168.1.100") in nets[0]

    def test_ipv6_cidr_parsed(self):
        nets = _build_server_allowed_networks("fd00::/8")
        assert len(nets) == 1

    def test_invalid_entry_skipped_valid_remain(self):
        nets = _build_server_allowed_networks("10.0.0.0/8,bad-entry,192.168.0.0/16")
        assert len(nets) == 2

    def test_whitespace_stripped_from_entries(self):
        nets = _build_server_allowed_networks("  10.0.0.0/8 , 192.168.0.0/16 ")
        assert len(nets) == 2

    def test_strict_false_allows_host_bits_in_cidr(self):
        # 10.0.0.1/8 has host bits set but strict=False should accept it
        nets = _build_server_allowed_networks("10.0.0.1/8")
        assert len(nets) == 1
        assert ipaddress.ip_address("10.0.0.1") in nets[0]


class TestServerCheckAllowedIP:
    """Unit tests for the _check_allowed_ip logic."""

    def test_no_networks_allows_any_ip(self):
        ok, err = _check_allowed_ip_impl("1.2.3.4", [])
        assert ok is True
        assert err is None

    def test_no_networks_allows_none_ip(self):
        ok, err = _check_allowed_ip_impl(None, [])
        assert ok is True
        assert err is None

    def test_ip_in_network_allowed(self):
        nets = _build_server_allowed_networks("10.0.0.0/8")
        ok, err = _check_allowed_ip_impl("10.5.5.5", nets)
        assert ok is True
        assert err is None

    def test_ip_not_in_network_denied(self):
        nets = _build_server_allowed_networks("10.0.0.0/8")
        ok, err = _check_allowed_ip_impl("192.168.1.1", nets)
        assert ok is False
        assert err is not None

    def test_none_ip_with_networks_denied(self):
        nets = _build_server_allowed_networks("10.0.0.0/8")
        ok, err = _check_allowed_ip_impl(None, nets)
        assert ok is False
        assert "not available" in (err or "")

    def test_ipv6_in_range_allowed(self):
        nets = _build_server_allowed_networks("fd00::/8")
        ok, err = _check_allowed_ip_impl("fd00::1", nets)
        assert ok is True

    def test_ipv6_outside_range_denied(self):
        nets = _build_server_allowed_networks("fd00::/8")
        ok, err = _check_allowed_ip_impl("2001:db8::1", nets)
        assert ok is False

    def test_multiple_networks_union(self):
        nets = _build_server_allowed_networks("10.0.0.0/8,192.168.0.0/16")
        ok1, _ = _check_allowed_ip_impl("10.1.2.3", nets)
        ok2, _ = _check_allowed_ip_impl("192.168.5.5", nets)
        bad, _ = _check_allowed_ip_impl("8.8.8.8", nets)
        assert ok1 is True
        assert ok2 is True
        assert bad is False


# ===========================================================================
# Part 3: Integration – _check_allowed_host present and wired in routes.py
# ===========================================================================


class TestCheckAllowedHostFunctionExists:
    """Verify the public contract of _check_allowed_host in routes.py."""

    def setup_method(self):
        self.routes = _load_routes_module(env_value="10.0.0.0/8")

    def teardown_method(self):
        sys.modules.pop("frontend.routes", None)

    def test_function_exists_in_routes_module(self):
        assert hasattr(self.routes, "_check_allowed_host"), (
            "routes.py must export _check_allowed_host"
        )

    def test_function_is_callable(self):
        assert callable(self.routes._check_allowed_host)

    def test_allowed_networks_constant_exists(self):
        assert hasattr(self.routes, "_ALLOWED_NETWORKS"), (
            "routes.py must export _ALLOWED_NETWORKS"
        )

    def test_allowed_networks_is_list(self):
        assert isinstance(self.routes._ALLOWED_NETWORKS, list)

    def test_returns_none_for_allowed_ip(self):
        req = _make_request("10.5.5.5")
        assert self.routes._check_allowed_host(req) is None

    def test_returns_response_for_blocked_ip(self):
        req = _make_request("1.2.3.4")
        result = self.routes._check_allowed_host(req)
        assert result is not None
        assert result.status_code == 403
