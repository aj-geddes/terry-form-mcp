#!/usr/bin/env python3
"""
Tests for LSP client shutdown wired into the app_lifespan context manager.

Verifies that app_lifespan calls lsp_client.shutdown() after yield (the
teardown phase), logs success, and handles errors gracefully without
re-raising (non-fatal shutdown failure).
"""

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Isolate the server module import with minimal stubs.
# We snapshot and restore sys.modules to avoid leaking stubs.
# ---------------------------------------------------------------------------

_STUBBED_NAMES = ("fastmcp", "terraform_lsp_client", "terry-form-mcp", "mcp_request_validator")
_saved_modules = {name: sys.modules.get(name) for name in _STUBBED_NAMES}

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

# LSP stub — _lsp_client starts as None; individual tests override it
_lsp_stub = types.ModuleType("terraform_lsp_client")
_lsp_stub._lsp_client = None  # type: ignore[attr-defined]
sys.modules["terraform_lsp_client"] = _lsp_stub

_terry_stub = types.ModuleType("terry-form-mcp")
_terry_stub.run_terraform = MagicMock(return_value={})  # type: ignore[attr-defined]
sys.modules["terry-form-mcp"] = _terry_stub

_validator_stub = types.ModuleType("mcp_request_validator")
_MockValidator = MagicMock()
_MockValidator.return_value = MagicMock()
_validator_stub.MCPRequestValidator = _MockValidator  # type: ignore[attr-defined]
sys.modules["mcp_request_validator"] = _validator_stub

import server_enhanced_with_lsp  # noqa: E402  (must come after stubs)
from server_enhanced_with_lsp import app_lifespan  # noqa: E402

# Restore originals so we don't leak into later test modules
for _name in _STUBBED_NAMES:
    _orig = _saved_modules[_name]
    if _orig is None:
        sys.modules.pop(_name, None)
    else:
        sys.modules[_name] = _orig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _run_lifespan(server_stub=None):
    """Drive the lifespan context manager through start + stop."""
    if server_stub is None:
        server_stub = MagicMock()
    async with app_lifespan(server_stub):
        pass  # simulate the server running, then exit to trigger teardown


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLifespanLSPShutdown:
    """Verify LSP shutdown is wired into the lifespan teardown path."""

    @pytest.mark.asyncio
    async def test_shutdown_called_when_lsp_client_exists(self):
        """lsp_client.shutdown() is awaited when _lsp_client is not None."""
        mock_client = MagicMock()
        mock_client.shutdown = AsyncMock()

        with patch.object(
            server_enhanced_with_lsp.terraform_lsp_client,
            "_lsp_client",
            mock_client,
        ):
            await _run_lifespan()

        mock_client.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_not_called_when_lsp_client_is_none(self):
        """lsp_client.shutdown() is NOT called when _lsp_client is None."""
        with patch.object(
            server_enhanced_with_lsp.terraform_lsp_client,
            "_lsp_client",
            None,
        ):
            # Should not raise; no shutdown call expected
            await _run_lifespan()
        # No assertion needed — if shutdown were called on None it would raise
        # AttributeError and the test would fail.

    @pytest.mark.asyncio
    async def test_shutdown_logs_success(self, caplog):
        """A successful shutdown logs an info message."""
        import logging

        mock_client = MagicMock()
        mock_client.shutdown = AsyncMock()

        with patch.object(
            server_enhanced_with_lsp.terraform_lsp_client,
            "_lsp_client",
            mock_client,
        ):
            with caplog.at_level(logging.INFO, logger="server_enhanced_with_lsp"):
                await _run_lifespan()

        assert any(
            "LSP client shut down successfully" in record.message
            for record in caplog.records
        ), f"Expected success log not found. Records: {[r.message for r in caplog.records]}"

    @pytest.mark.asyncio
    async def test_shutdown_error_is_non_fatal(self):
        """A shutdown exception is caught and does not propagate."""
        mock_client = MagicMock()
        mock_client.shutdown = AsyncMock(side_effect=RuntimeError("terraform-ls died"))

        with patch.object(
            server_enhanced_with_lsp.terraform_lsp_client,
            "_lsp_client",
            mock_client,
        ):
            # Must NOT raise — error is non-fatal
            await _run_lifespan()

    @pytest.mark.asyncio
    async def test_shutdown_error_logs_warning(self, caplog):
        """A shutdown exception is logged as a warning."""
        import logging

        mock_client = MagicMock()
        mock_client.shutdown = AsyncMock(side_effect=OSError("pipe broken"))

        with patch.object(
            server_enhanced_with_lsp.terraform_lsp_client,
            "_lsp_client",
            mock_client,
        ):
            with caplog.at_level(logging.WARNING, logger="server_enhanced_with_lsp"):
                await _run_lifespan()

        assert any(
            "LSP client shutdown error" in record.message
            for record in caplog.records
        ), f"Expected warning log not found. Records: {[r.message for r in caplog.records]}"
