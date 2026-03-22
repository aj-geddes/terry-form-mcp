#!/usr/bin/env python3
"""
Tests for secrets-on-disk elimination.

RED -> GREEN -> REFACTOR cycle for:
1. _SECRET_FIELDS constant listing dotted paths never persisted to disk
2. _save() strips all secret fields before writing JSON
3. _apply_to_env() writes credentials only to os.environ, not disk
4. Plaintext credentials warning removed from _save()
5. Non-secret settings continue to persist normally
"""

import copy
import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Import the modules under test.
# conftest.py inserts src/ into sys.path, so direct imports work.
# ---------------------------------------------------------------------------
from frontend.config_manager import ConfigManager, _SECRET_FIELDS
from frontend.schemas import TerryConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(tmp_path: Path) -> ConfigManager:
    """Return a ConfigManager backed by a temp file, seeded from defaults."""
    mgr = ConfigManager(config_path=tmp_path / "terry-config.json")
    mgr._config = TerryConfig()
    return mgr


def _saved_json(mgr: ConfigManager) -> dict:
    """Force a _save() and return what was written to disk."""
    mgr._save()
    return json.loads(mgr.config_path.read_text())


# ---------------------------------------------------------------------------
# 1. _SECRET_FIELDS constant exists and contains the required paths
# ---------------------------------------------------------------------------

class TestSecretFieldsConstant:
    """_SECRET_FIELDS is exported from config_manager and lists all secret paths."""

    REQUIRED_PATHS = {
        "cloud_credentials.aws.secret_access_key",
        "cloud_credentials.aws.access_key_id",
        "cloud_credentials.azure.client_secret",
        "cloud_credentials.azure.client_id",
        "cloud_credentials.gcp.credentials_json",
        "terraform_cloud.token",
        "github.webhook_secret",
    }

    def test_secret_fields_constant_is_importable(self):
        """_SECRET_FIELDS must be importable from config_manager."""
        from frontend.config_manager import _SECRET_FIELDS
        assert _SECRET_FIELDS is not None

    def test_secret_fields_is_a_set_or_frozenset(self):
        assert isinstance(_SECRET_FIELDS, (set, frozenset))

    def test_aws_secret_access_key_is_in_secret_fields(self):
        assert "cloud_credentials.aws.secret_access_key" in _SECRET_FIELDS

    def test_aws_access_key_id_is_in_secret_fields(self):
        assert "cloud_credentials.aws.access_key_id" in _SECRET_FIELDS

    def test_azure_client_secret_is_in_secret_fields(self):
        assert "cloud_credentials.azure.client_secret" in _SECRET_FIELDS

    def test_azure_client_id_is_in_secret_fields(self):
        assert "cloud_credentials.azure.client_id" in _SECRET_FIELDS

    def test_gcp_credentials_json_is_in_secret_fields(self):
        assert "cloud_credentials.gcp.credentials_json" in _SECRET_FIELDS

    def test_terraform_cloud_token_is_in_secret_fields(self):
        assert "terraform_cloud.token" in _SECRET_FIELDS

    def test_github_webhook_secret_is_in_secret_fields(self):
        assert "github.webhook_secret" in _SECRET_FIELDS

    def test_all_required_paths_present(self):
        missing = self.REQUIRED_PATHS - _SECRET_FIELDS
        assert not missing, f"Missing from _SECRET_FIELDS: {missing}"


# ---------------------------------------------------------------------------
# 2. _save() strips secret fields before writing to disk
# ---------------------------------------------------------------------------

class TestSaveStripsSecrets:
    """_save() must never write secret values to the JSON config file."""

    def test_aws_secret_access_key_not_in_saved_file(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._config.cloud_credentials.aws.secret_access_key = "SUPER_SECRET_KEY"
        data = _saved_json(mgr)
        assert data["cloud_credentials"]["aws"]["secret_access_key"] == ""

    def test_aws_access_key_id_not_in_saved_file(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._config.cloud_credentials.aws.access_key_id = "AKIAIOSFODNN7EXAMPLE"
        data = _saved_json(mgr)
        assert data["cloud_credentials"]["aws"]["access_key_id"] == ""

    def test_azure_client_secret_not_in_saved_file(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._config.cloud_credentials.azure.client_secret = "azure-secret-value"
        data = _saved_json(mgr)
        assert data["cloud_credentials"]["azure"]["client_secret"] == ""

    def test_azure_client_id_not_in_saved_file(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._config.cloud_credentials.azure.client_id = "some-client-id"
        data = _saved_json(mgr)
        assert data["cloud_credentials"]["azure"]["client_id"] == ""

    def test_terraform_cloud_token_not_in_saved_file(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._config.terraform_cloud.token = "tf-token-abc123"
        data = _saved_json(mgr)
        assert data["terraform_cloud"]["token"] == ""

    def test_github_webhook_secret_not_in_saved_file(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._config.github.webhook_secret = "gh-webhook-secret"
        data = _saved_json(mgr)
        assert data["github"]["webhook_secret"] == ""

    def test_gcp_credentials_json_not_in_saved_file(self, tmp_path):
        """GCP credentials_json field is stripped; credentials_file (a path) is not."""
        mgr = _make_manager(tmp_path)
        # credentials_json is a secret inline credential; credentials_file is just a path
        if hasattr(mgr._config.cloud_credentials.gcp, "credentials_json"):
            mgr._config.cloud_credentials.gcp.credentials_json = '{"type":"service_account"}'
            data = _saved_json(mgr)
            assert data["cloud_credentials"]["gcp"]["credentials_json"] == ""

    def test_in_memory_config_retains_secret_after_save(self, tmp_path):
        """_save() must not mutate the in-memory config object."""
        mgr = _make_manager(tmp_path)
        mgr._config.terraform_cloud.token = "tf-token-abc123"
        mgr._save()
        # In-memory value must be unchanged
        assert mgr._config.terraform_cloud.token == "tf-token-abc123"

    def test_non_secret_fields_persist_normally(self, tmp_path):
        """Non-secret settings (host, port, rate limits) must still be saved."""
        mgr = _make_manager(tmp_path)
        mgr._config.server.host = "192.168.1.50"
        mgr._config.server.port = 9090
        mgr._config.rate_limits.terraform = 15
        data = _saved_json(mgr)
        assert data["server"]["host"] == "192.168.1.50"
        assert data["server"]["port"] == 9090
        assert data["rate_limits"]["terraform"] == 15

    def test_github_app_id_persists_normally(self, tmp_path):
        """github.app_id is not a secret and must be saved."""
        mgr = _make_manager(tmp_path)
        mgr._config.github.app_id = "123456"
        data = _saved_json(mgr)
        assert data["github"]["app_id"] == "123456"

    def test_multiple_secrets_all_stripped_in_one_save(self, tmp_path):
        """All secrets are stripped in a single _save() call."""
        mgr = _make_manager(tmp_path)
        mgr._config.cloud_credentials.aws.secret_access_key = "KEY1"
        mgr._config.cloud_credentials.azure.client_secret = "KEY2"
        mgr._config.terraform_cloud.token = "KEY3"
        mgr._config.github.webhook_secret = "KEY4"
        data = _saved_json(mgr)
        assert data["cloud_credentials"]["aws"]["secret_access_key"] == ""
        assert data["cloud_credentials"]["azure"]["client_secret"] == ""
        assert data["terraform_cloud"]["token"] == ""
        assert data["github"]["webhook_secret"] == ""


# ---------------------------------------------------------------------------
# 3. _apply_to_env() writes credentials only to os.environ, not disk
# ---------------------------------------------------------------------------

class TestApplyToEnvCredentialHandling:
    """When credentials are submitted, they go to os.environ only."""

    def test_apply_to_env_sets_tf_api_token_in_environ(self, tmp_path):
        mgr = _make_manager(tmp_path)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TF_API_TOKEN", None)
            mgr._apply_to_env("terraform_cloud", {"token": "live-token-xyz"})
            assert os.environ.get("TF_API_TOKEN") == "live-token-xyz"

    def test_apply_to_env_sets_aws_secret_in_environ(self, tmp_path):
        mgr = _make_manager(tmp_path)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            mgr._apply_to_env("cloud_credentials", {
                "aws": {"secret_access_key": "mysecret", "access_key_id": "", "session_token": "", "region": ""},
                "gcp": {},
                "azure": {},
            })
            assert os.environ.get("AWS_SECRET_ACCESS_KEY") == "mysecret"

    def test_apply_to_env_logs_warning_for_credentials(self, tmp_path, caplog):
        """A warning must be logged when credential fields are applied to env."""
        mgr = _make_manager(tmp_path)
        with caplog.at_level(logging.WARNING, logger="frontend.config_manager"):
            mgr._apply_to_env("terraform_cloud", {"token": "live-token-xyz"})
        warning_text = " ".join(caplog.messages)
        assert "current process" in warning_text.lower() or "environment" in warning_text.lower()

    def test_apply_to_env_does_not_trigger_save(self, tmp_path):
        """_apply_to_env() itself must not write to disk (no side-effect save)."""
        mgr = _make_manager(tmp_path)
        config_file = mgr.config_path
        mgr._apply_to_env("terraform_cloud", {"token": "live-token-xyz"})
        # File should not exist (we never called _save())
        assert not config_file.exists()


# ---------------------------------------------------------------------------
# 4. Plaintext credentials warning removed from _save()
# ---------------------------------------------------------------------------

class TestPlaintextWarningRemoved:
    """_save() must NOT emit the old 'plaintext' credentials warning."""

    def test_no_plaintext_warning_when_saving_with_credentials(self, tmp_path, caplog):
        """After stripping, no need to warn about plaintext storage."""
        mgr = _make_manager(tmp_path)
        mgr._config.cloud_credentials.aws.secret_access_key = "SUPER_SECRET"
        mgr._config.terraform_cloud.token = "tf-token"
        with caplog.at_level(logging.WARNING, logger="frontend.config_manager"):
            mgr._save()
        for msg in caplog.messages:
            assert "plaintext" not in msg.lower(), (
                f"Unexpected plaintext warning found: {msg!r}"
            )

    def test_no_plaintext_warning_for_empty_config(self, tmp_path, caplog):
        """No plaintext warning even when config is entirely default."""
        mgr = _make_manager(tmp_path)
        with caplog.at_level(logging.WARNING, logger="frontend.config_manager"):
            mgr._save()
        for msg in caplog.messages:
            assert "plaintext" not in msg.lower()


# ---------------------------------------------------------------------------
# 5. update_section() end-to-end: credentials go to env, not disk
# ---------------------------------------------------------------------------

class TestUpdateSectionSecretsFlow:
    """update_section() for credential sections applies secrets to env only."""

    def test_update_terraform_cloud_does_not_persist_token(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._save()  # seed the file first
        with patch.dict(os.environ, {}, clear=False):
            mgr.update_section("terraform-cloud", {"token": "secret-token-999"})
        data = json.loads(mgr.config_path.read_text())
        assert data["terraform_cloud"]["token"] == ""

    def test_update_terraform_cloud_sets_env_var(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr._save()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TF_API_TOKEN", None)
            mgr.update_section("terraform-cloud", {"token": "secret-token-999"})
            assert os.environ.get("TF_API_TOKEN") == "secret-token-999"

    def test_update_server_host_persists_to_disk(self, tmp_path):
        """Non-secret server settings must still persist."""
        mgr = _make_manager(tmp_path)
        mgr._save()
        mgr.update_section("server", {"host": "10.0.0.5", "port": 9000, "transport": "streamable-http"})
        data = json.loads(mgr.config_path.read_text())
        assert data["server"]["host"] == "10.0.0.5"
        assert data["server"]["port"] == 9000
