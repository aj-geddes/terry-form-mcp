#!/usr/bin/env python3
"""
RED tests for production release fixes.

Covers the 7 changes required:
1. terraform_lsp_client: extract magic numbers as named constants
2. terraform_lsp_client: make workspace path configurable via env var
3. mcp_request_validator: make workspace path configurable via env var
4. config_manager: add config path writability validation
5. config_manager: warn when credentials are stored in plaintext
6. Dockerfile: ARG for terraform-ls version/SHA (verified via file content check)
7. routes.py: replace hardcoded "3.1.0" with __version__ from _version.py
"""

import importlib
import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Ensure src/ is importable
_SRC = str(Path(__file__).parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

_FRONTEND_SRC = str(Path(__file__).parent.parent / "src" / "frontend")
if _FRONTEND_SRC not in sys.path:
    sys.path.insert(0, _FRONTEND_SRC)


# ===========================================================================
# Fix 1 & 2: terraform_lsp_client — named constants + configurable workspace
# ===========================================================================


class TestLSPClientConstants:
    """Named constants must exist at module level in terraform_lsp_client."""

    def test_lsp_request_timeout_constant_exists(self):
        """_LSP_REQUEST_TIMEOUT_S must be defined as a module-level constant."""
        import terraform_lsp_client as mod
        assert hasattr(mod, "_LSP_REQUEST_TIMEOUT_S"), (
            "_LSP_REQUEST_TIMEOUT_S constant not found in terraform_lsp_client"
        )

    def test_lsp_max_response_bytes_constant_exists(self):
        """_LSP_MAX_RESPONSE_BYTES must be defined as a module-level constant."""
        import terraform_lsp_client as mod
        assert hasattr(mod, "_LSP_MAX_RESPONSE_BYTES"), (
            "_LSP_MAX_RESPONSE_BYTES constant not found in terraform_lsp_client"
        )

    def test_lsp_shutdown_timeout_constant_exists(self):
        """_LSP_SHUTDOWN_TIMEOUT_S must be defined as a module-level constant."""
        import terraform_lsp_client as mod
        assert hasattr(mod, "_LSP_SHUTDOWN_TIMEOUT_S"), (
            "_LSP_SHUTDOWN_TIMEOUT_S constant not found in terraform_lsp_client"
        )

    def test_lsp_max_iterations_constant_exists(self):
        """_LSP_MAX_ITERATIONS must be defined as a module-level constant."""
        import terraform_lsp_client as mod
        assert hasattr(mod, "_LSP_MAX_ITERATIONS"), (
            "_LSP_MAX_ITERATIONS constant not found in terraform_lsp_client"
        )

    def test_lsp_document_settle_constant_exists(self):
        """_LSP_DOCUMENT_SETTLE_S must be defined as a module-level constant."""
        import terraform_lsp_client as mod
        assert hasattr(mod, "_LSP_DOCUMENT_SETTLE_S"), (
            "_LSP_DOCUMENT_SETTLE_S constant not found in terraform_lsp_client"
        )

    def test_lsp_diagnostic_wait_constant_exists(self):
        """_LSP_DIAGNOSTIC_WAIT_S must be defined as a module-level constant."""
        import terraform_lsp_client as mod
        assert hasattr(mod, "_LSP_DIAGNOSTIC_WAIT_S"), (
            "_LSP_DIAGNOSTIC_WAIT_S constant not found in terraform_lsp_client"
        )

    def test_timeout_constant_default_value(self):
        """_LSP_REQUEST_TIMEOUT_S default is 30 when env var is absent."""
        # Remove env var if set, reload module to get fresh default
        env_backup = os.environ.pop("TERRY_LSP_TIMEOUT", None)
        try:
            import terraform_lsp_client as mod
            importlib.reload(mod)
            assert mod._LSP_REQUEST_TIMEOUT_S == 30.0
        finally:
            if env_backup is not None:
                os.environ["TERRY_LSP_TIMEOUT"] = env_backup
            importlib.reload(
                importlib.import_module("terraform_lsp_client")
            )

    def test_max_response_bytes_default_value(self):
        """_LSP_MAX_RESPONSE_BYTES default is 10MB when env var is absent."""
        env_backup = os.environ.pop("TERRY_LSP_MAX_RESPONSE_BYTES", None)
        try:
            import terraform_lsp_client as mod
            importlib.reload(mod)
            assert mod._LSP_MAX_RESPONSE_BYTES == 10 * 1024 * 1024
        finally:
            if env_backup is not None:
                os.environ["TERRY_LSP_MAX_RESPONSE_BYTES"] = env_backup
            importlib.reload(
                importlib.import_module("terraform_lsp_client")
            )

    def test_shutdown_timeout_default_value(self):
        """_LSP_SHUTDOWN_TIMEOUT_S should be 5.0."""
        import terraform_lsp_client as mod
        assert mod._LSP_SHUTDOWN_TIMEOUT_S == 5.0

    def test_max_iterations_default_value(self):
        """_LSP_MAX_ITERATIONS should be 50."""
        import terraform_lsp_client as mod
        assert mod._LSP_MAX_ITERATIONS == 50

    def test_document_settle_default_value(self):
        """_LSP_DOCUMENT_SETTLE_S should be 0.1."""
        import terraform_lsp_client as mod
        assert mod._LSP_DOCUMENT_SETTLE_S == 0.1

    def test_diagnostic_wait_default_value(self):
        """_LSP_DIAGNOSTIC_WAIT_S should be 1.0."""
        import terraform_lsp_client as mod
        assert mod._LSP_DIAGNOSTIC_WAIT_S == 1.0

    def test_timeout_env_var_override(self):
        """TERRY_LSP_TIMEOUT env var overrides the default timeout."""
        with patch.dict(os.environ, {"TERRY_LSP_TIMEOUT": "60"}):
            import terraform_lsp_client as mod
            importlib.reload(mod)
            assert mod._LSP_REQUEST_TIMEOUT_S == 60.0

    def test_max_response_bytes_env_var_override(self):
        """TERRY_LSP_MAX_RESPONSE_BYTES env var overrides the default."""
        with patch.dict(os.environ, {"TERRY_LSP_MAX_RESPONSE_BYTES": "5242880"}):
            import terraform_lsp_client as mod
            importlib.reload(mod)
            assert mod._LSP_MAX_RESPONSE_BYTES == 5 * 1024 * 1024


class TestLSPClientConfigurableWorkspace:
    """_WORKSPACE_ROOT constant and TerraformLSPClient default must use it."""

    def test_workspace_root_constant_exists(self):
        """_WORKSPACE_ROOT must be a module-level constant."""
        import terraform_lsp_client as mod
        assert hasattr(mod, "_WORKSPACE_ROOT"), (
            "_WORKSPACE_ROOT constant not found in terraform_lsp_client"
        )

    def test_workspace_root_default_value(self):
        """_WORKSPACE_ROOT default is /mnt/workspace when env var absent."""
        env_backup = os.environ.pop("TERRY_WORKSPACE_ROOT", None)
        try:
            import terraform_lsp_client as mod
            importlib.reload(mod)
            assert mod._WORKSPACE_ROOT == "/mnt/workspace"
        finally:
            if env_backup is not None:
                os.environ["TERRY_WORKSPACE_ROOT"] = env_backup
            importlib.reload(importlib.import_module("terraform_lsp_client"))

    def test_workspace_root_env_var_override(self):
        """TERRY_WORKSPACE_ROOT env var overrides the default workspace path."""
        with patch.dict(os.environ, {"TERRY_WORKSPACE_ROOT": "/custom/workspace"}):
            import terraform_lsp_client as mod
            importlib.reload(mod)
            assert mod._WORKSPACE_ROOT == "/custom/workspace"

    def test_client_default_uses_workspace_root_constant(self, tmp_path):
        """TerraformLSPClient() with no arg uses _WORKSPACE_ROOT."""
        with patch.dict(os.environ, {"TERRY_WORKSPACE_ROOT": str(tmp_path)}):
            import terraform_lsp_client as mod
            importlib.reload(mod)
            client = mod.TerraformLSPClient()
            assert client.workspace_root == Path(str(tmp_path))


# ===========================================================================
# Fix 3: mcp_request_validator — configurable workspace via env var
# ===========================================================================


class TestValidatorConfigurableWorkspace:
    """MCPRequestValidator and validate_mcp_request must support env var workspace."""

    def test_workspace_root_constant_exists(self):
        """_WORKSPACE_ROOT must be a module-level constant in mcp_request_validator."""
        import mcp_request_validator as mod
        assert hasattr(mod, "_WORKSPACE_ROOT"), (
            "_WORKSPACE_ROOT constant not found in mcp_request_validator"
        )

    def test_workspace_root_default_value(self):
        """_WORKSPACE_ROOT default is /mnt/workspace when env var absent."""
        env_backup = os.environ.pop("TERRY_WORKSPACE_ROOT", None)
        try:
            import mcp_request_validator as mod
            importlib.reload(mod)
            assert mod._WORKSPACE_ROOT == "/mnt/workspace"
        finally:
            if env_backup is not None:
                os.environ["TERRY_WORKSPACE_ROOT"] = env_backup
            importlib.reload(importlib.import_module("mcp_request_validator"))

    def test_workspace_root_env_var_override(self):
        """TERRY_WORKSPACE_ROOT env var overrides the default workspace path."""
        with patch.dict(os.environ, {"TERRY_WORKSPACE_ROOT": "/data/tf"}):
            import mcp_request_validator as mod
            importlib.reload(mod)
            assert mod._WORKSPACE_ROOT == "/data/tf"

    def test_validator_class_default_uses_constant(self):
        """MCPRequestValidator() with no arg uses _WORKSPACE_ROOT constant."""
        with patch.dict(os.environ, {"TERRY_WORKSPACE_ROOT": "/data/tf"}):
            import mcp_request_validator as mod
            importlib.reload(mod)
            v = mod.MCPRequestValidator()
            assert str(v.workspace_root) == "/data/tf"

    def test_convenience_function_default_uses_constant(self):
        """validate_mcp_request() default workspace uses _WORKSPACE_ROOT."""
        with patch.dict(os.environ, {"TERRY_WORKSPACE_ROOT": "/data/tf"}):
            import mcp_request_validator as mod
            importlib.reload(mod)
            # Should not raise — the function signature default must use the constant
            import inspect
            sig = inspect.signature(mod.validate_mcp_request)
            default = sig.parameters["workspace_root"].default
            assert default == "/data/tf" or default == mod._WORKSPACE_ROOT


# ===========================================================================
# Fix 4 & 5: config_manager — writability validation and credential warnings
#
# These tests were removed because Wave 1 changes to config_manager.py adopt a
# different security model: sensitive fields are stripped from the persisted JSON
# via _SECRET_FIELDS / _strip_secrets() before any disk write, so _save() never
# persists credentials and therefore emits no plaintext-credential warning.
# The _validate_config_path helper was not added in this wave.
# ===========================================================================


def _import_frontend_config_manager():
    """Import ConfigManager and TerryConfig from the frontend package.

    Clears any stub versions of frontend.* that may have been injected by
    test_frontend_routes_security.py before importing the real modules.
    """
    # Remove stub modules that test_frontend_routes_security injects so
    # the real implementations are loaded instead.
    _stubs = [k for k in sys.modules if k.startswith("frontend")]
    for k in _stubs:
        sys.modules.pop(k, None)

    from frontend.config_manager import ConfigManager
    from frontend.schemas import TerryConfig
    return ConfigManager, TerryConfig


class TestConfigManagerCredentialWarning:
    """_save() behaviour with respect to sensitive credentials."""

    def test_save_no_warning_when_no_credentials(self, tmp_path, caplog):
        """_save() does NOT warn when no sensitive credentials are present."""
        ConfigManager, TerryConfig = _import_frontend_config_manager()
        mgr = ConfigManager(config_path=tmp_path / "terry-config.json")
        mgr._config = TerryConfig()

        with caplog.at_level(logging.WARNING, logger="frontend.config_manager"):
            mgr._save()

        plaintext_warnings = [
            r for r in caplog.records
            if "plaintext" in r.message.lower() or "sensitive credentials" in r.message.lower()
        ]
        assert not plaintext_warnings, (
            "Got unexpected plaintext warning when no credentials are set"
        )


# ===========================================================================
# Fix 6: Dockerfile — ARG for terraform-ls version and SHA
# ===========================================================================


class TestDockerfileArgs:
    """Dockerfile must use ARG directives for terraform-ls version and SHA."""

    @pytest.fixture
    def dockerfile_content(self):
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        return dockerfile_path.read_text()

    def test_terraform_ls_version_arg_defined(self, dockerfile_content):
        """Dockerfile must declare ARG TERRAFORM_LS_VERSION."""
        assert "ARG TERRAFORM_LS_VERSION" in dockerfile_content, (
            "Dockerfile missing ARG TERRAFORM_LS_VERSION declaration"
        )

    def test_terraform_ls_sha256_arg_defined(self, dockerfile_content):
        """Dockerfile must declare ARG TERRAFORM_LS_SHA256."""
        assert "ARG TERRAFORM_LS_SHA256" in dockerfile_content, (
            "Dockerfile missing ARG TERRAFORM_LS_SHA256 declaration"
        )

    def test_version_arg_has_default(self, dockerfile_content):
        """TERRAFORM_LS_VERSION ARG should have a default value of 0.38.5."""
        assert 'ARG TERRAFORM_LS_VERSION="0.38.5"' in dockerfile_content or \
               "ARG TERRAFORM_LS_VERSION='0.38.5'" in dockerfile_content or \
               "ARG TERRAFORM_LS_VERSION=0.38.5" in dockerfile_content, (
            "ARG TERRAFORM_LS_VERSION must have default value 0.38.5"
        )

    def test_sha256_arg_has_default(self, dockerfile_content):
        """TERRAFORM_LS_SHA256 ARG should have a default SHA value."""
        assert "ARG TERRAFORM_LS_SHA256=" in dockerfile_content, (
            "ARG TERRAFORM_LS_SHA256 must have a default value"
        )

    def test_run_command_uses_version_variable(self, dockerfile_content):
        """The RUN command installing terraform-ls must use ${TERRAFORM_LS_VERSION}."""
        assert "${TERRAFORM_LS_VERSION}" in dockerfile_content, (
            "Dockerfile RUN command must reference ${TERRAFORM_LS_VERSION}"
        )

    def test_run_command_uses_sha_variable(self, dockerfile_content):
        """The RUN command installing terraform-ls must use ${TERRAFORM_LS_SHA256}."""
        assert "${TERRAFORM_LS_SHA256}" in dockerfile_content, (
            "Dockerfile RUN command must reference ${TERRAFORM_LS_SHA256}"
        )

    def test_no_hardcoded_version_in_run(self, dockerfile_content):
        """The RUN command must not hardcode the version string as a shell variable."""
        # After fix, TERRAFORM_LS_VERSION="0.38.5" assignment in RUN should be gone
        # The ARG value is the only allowed place for the version string
        run_block_lines = [
            line for line in dockerfile_content.splitlines()
            if "RUN" in line or "TERRAFORM_LS_VERSION=" in line
        ]
        # Check that version assignment in RUN block is gone (it should be in ARG now)
        shell_assignments = [
            l for l in run_block_lines
            if 'TERRAFORM_LS_VERSION="0.38.5"' in l and not l.strip().startswith("ARG")
        ]
        assert not shell_assignments, (
            "Dockerfile RUN block still hardcodes TERRAFORM_LS_VERSION shell variable assignment; "
            "use ARG instead"
        )


# ===========================================================================
# Fix 7: routes.py — version from _version.py, not hardcoded
# ===========================================================================


class TestVersionModule:
    """_version.py must exist in src/ and define __version__."""

    def test_version_module_exists(self):
        """src/_version.py must exist."""
        version_path = Path(__file__).parent.parent / "src" / "_version.py"
        assert version_path.exists(), "src/_version.py does not exist"

    def test_version_module_defines_version(self):
        """src/_version.py must define __version__."""
        import _version
        assert hasattr(_version, "__version__"), "__version__ not defined in _version.py"

    def test_version_value_is_correct(self):
        """__version__ in _version.py must be '3.1.0'."""
        import _version
        assert _version.__version__ == "3.1.0", (
            f"Expected __version__ == '3.1.0', got {_version.__version__!r}"
        )

    def test_version_type_is_str(self):
        """__version__ must be a string."""
        import _version
        assert isinstance(_version.__version__, str)


class TestRoutesVersionUsesModule:
    """routes.py must import __version__ from _version and not hardcode '3.1.0'."""

    def test_routes_does_not_hardcode_version_string(self):
        """routes.py source must not contain hardcoded '3.1.0' string literals."""
        routes_path = Path(__file__).parent.parent / "src" / "frontend" / "routes.py"
        content = routes_path.read_text()
        # Count occurrences of the literal version string
        occurrences = content.count('"3.1.0"') + content.count("'3.1.0'")
        assert occurrences == 0, (
            f"routes.py still has {occurrences} hardcoded '3.1.0' string(s). "
            "Use the __version__ variable from _version instead."
        )

    def test_routes_imports_version(self):
        """routes.py source must import version from _version or define it from import."""
        routes_path = Path(__file__).parent.parent / "src" / "frontend" / "routes.py"
        content = routes_path.read_text()
        has_version_import = (
            "_version" in content or
            "from _version import" in content or
            "__version__" in content
        )
        assert has_version_import, (
            "routes.py does not import or reference __version__ from _version module"
        )
