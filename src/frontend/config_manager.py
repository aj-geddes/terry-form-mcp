"""Config persistence: JSON file + environment variable bridge.

Startup: env vars seed the config file (if it doesn't exist) -> config file is source of truth.
UI Save: validate (Pydantic) -> atomic write (tmp + rename) -> apply to os.environ / singletons.

Security: Fields listed in _SECRET_FIELDS are stripped to empty strings before any disk write.
Credentials submitted via the UI are applied to os.environ only (current process lifetime).
"""

import json
import logging
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any

from .schemas import (
    SECTION_MODELS,
    SECTION_TO_KEY,
    SENSITIVE_FIELDS,
    TerryConfig,
)

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(os.environ.get("TERRY_CONFIG_PATH", "/app/config/terry-config.json"))

# Mapping from config keys to environment variable names
_ENV_MAP = {
    "server.transport": "MCP_TRANSPORT",
    "server.host": "HOST",
    "server.port": "PORT",
    "server.api_key": "TERRY_FORM_API_KEY",
    "github.app_id": "GITHUB_APP_ID",
    "github.private_key_path": "GITHUB_APP_PRIVATE_KEY_PATH",
    "github.installation_id": "GITHUB_APP_INSTALLATION_ID",
    "github.webhook_secret": "GITHUB_APP_WEBHOOK_SECRET",
    "terraform_cloud.token": "TF_API_TOKEN",
    "cloud_credentials.aws.access_key_id": "AWS_ACCESS_KEY_ID",
    "cloud_credentials.aws.secret_access_key": "AWS_SECRET_ACCESS_KEY",
    "cloud_credentials.aws.session_token": "AWS_SESSION_TOKEN",
    "cloud_credentials.aws.region": "AWS_DEFAULT_REGION",
    "cloud_credentials.gcp.credentials_file": "GOOGLE_APPLICATION_CREDENTIALS",
    "cloud_credentials.gcp.project": "GCLOUD_PROJECT",
    "cloud_credentials.gcp.region": "CLOUDSDK_COMPUTE_REGION",
    "cloud_credentials.azure.subscription_id": "ARM_SUBSCRIPTION_ID",
    "cloud_credentials.azure.tenant_id": "ARM_TENANT_ID",
    "cloud_credentials.azure.client_id": "ARM_CLIENT_ID",
    "cloud_credentials.azure.client_secret": "ARM_CLIENT_SECRET",
    "rate_limits.terraform": "TERRY_RATE_LIMIT_TERRAFORM",
    "rate_limits.github": "TERRY_RATE_LIMIT_GITHUB",
    "rate_limits.tf_cloud": "TERRY_RATE_LIMIT_TF_CLOUD",
    "rate_limits.default": "TERRY_RATE_LIMIT_DEFAULT",
    "terraform_options.tf_log": "TF_LOG",
    "terraform_options.max_operation_timeout": "MAX_OPERATION_TIMEOUT",
}

# Reverse map: env var -> config key
_REVERSE_ENV_MAP = {v: k for k, v in _ENV_MAP.items()}

# Dotted paths that must never be persisted to disk.
# These fields are stripped to empty strings before json.dump and written
# only to os.environ via _apply_to_env().
_SECRET_FIELDS: frozenset = frozenset(
    {
        "cloud_credentials.aws.secret_access_key",
        "cloud_credentials.aws.access_key_id",
        "cloud_credentials.azure.client_secret",
        "cloud_credentials.azure.client_id",
        "cloud_credentials.gcp.credentials_json",
        "terraform_cloud.token",
        "github.webhook_secret",
    }
)


class ConfigManager:
    """Manages terry-form-mcp configuration with file persistence."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or CONFIG_PATH
        self._config: TerryConfig | None = None

    def load(self) -> TerryConfig:
        """Load config from file, or seed from env vars on first boot."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self._config = TerryConfig.model_validate(data)
                logger.info(f"Config loaded from {self.config_path}")
                return self._config
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
                # Fall through to seed from env

        # Seed from environment variables
        self._config = self._seed_from_env()
        self._save()
        logger.info("Config seeded from environment variables")
        return self._config

    @property
    def config(self) -> TerryConfig:
        if self._config is None:
            self.load()
        return self._config

    def get_section(self, section: str) -> dict[str, Any]:
        """Get a configuration section as a dict."""
        config_key = SECTION_TO_KEY.get(section, section)
        section_obj = getattr(self.config, config_key, None)
        if section_obj is None:
            raise ValueError(f"Unknown config section: {section}")
        return section_obj.model_dump()

    def get_section_masked(self, section: str) -> dict[str, Any]:
        """Get a configuration section with sensitive values masked."""
        data = self.get_section(section)
        config_key = SECTION_TO_KEY.get(section, section)
        return self._mask_sensitive(data, config_key)

    def update_section(
        self, section: str, data: dict[str, Any], rate_limiter=None
    ) -> dict[str, Any]:
        """Validate and update a configuration section.

        Returns the validated section data.
        Raises ValueError on validation failure.
        """
        config_key = SECTION_TO_KEY.get(section, section)
        model_cls = SECTION_MODELS.get(section)
        if model_cls is None:
            raise ValueError(f"Unknown config section: {section}")

        # Preserve existing sensitive values if the field is empty (not submitted)
        current = self.get_section(section)
        merged = self._merge_sensitive(current, data, config_key)

        # Validate
        validated = model_cls.model_validate(merged)

        # Update the config object
        setattr(self._config, config_key, validated)

        # Atomic write (secrets stripped inside _save)
        self._save()

        # Apply to environment variables (credentials stay in-process only)
        self._apply_to_env(config_key, validated.model_dump())

        # Live-reload rate limiter if applicable
        if section == "rate-limits" and rate_limiter is not None:
            new_limits = validated.model_dump()
            rate_limiter.update_limits(new_limits)
            logger.info(f"Rate limits updated live: {new_limits}")

        logger.info(f"Config section '{section}' updated")
        return validated.model_dump()

    def get_all(self) -> dict[str, Any]:
        """Get the full config as a dict."""
        return self.config.model_dump()

    def get_or_create_csrf_secret(self) -> str:
        """Return the CSRF secret, following env-var > persisted > generated priority.

        Priority order:
        1. TERRY_CSRF_SECRET environment variable (highest priority).
        2. Persisted value from the config file.
        3. Freshly generated secret that is then persisted for future restarts.

        The generated secret is 32 random bytes encoded as a 64-character hex string.
        """
        env_secret = os.environ.get("TERRY_CSRF_SECRET")
        if env_secret:
            return env_secret

        # Try persisted value
        persisted = self.config.server_internal.csrf_secret
        if persisted:
            return persisted

        # Generate a new secret and persist it
        new_secret = secrets.token_hex(32)
        self.config.server_internal.csrf_secret = new_secret
        self._save()
        logger.info("Generated and persisted new CSRF secret")
        return new_secret

    def _seed_from_env(self) -> TerryConfig:
        """Build a TerryConfig from current environment variables."""
        data: dict[str, Any] = {}
        for config_key, env_var in _ENV_MAP.items():
            value = os.environ.get(env_var)
            if value is not None:
                self._set_nested(data, config_key, value)
        try:
            return TerryConfig.model_validate(data)
        except Exception:
            logger.warning("Failed to validate env-seeded config, using defaults")
            return TerryConfig()

    def _save(self) -> None:
        """Atomic write: write to temp file then rename.

        Sensitive fields (listed in _SECRET_FIELDS) are stripped to empty
        strings before writing.  The in-memory config object is not mutated.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.config.model_dump()
        sanitized = self._strip_secrets(data)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=self.config_path.parent, suffix=".tmp"
            )
            with os.fdopen(fd, "w") as f:
                json.dump(sanitized, f, indent=2)
            os.replace(tmp_path, self.config_path)
            # Best-effort chmod 600
            try:
                os.chmod(self.config_path, 0o600)
            except OSError:
                pass
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def _apply_to_env(self, config_key: str, data: dict[str, Any]) -> None:
        """Push config values to os.environ so existing code picks them up.

        Credentials are written ONLY to the current process environment and
        are never persisted to the config file.
        """
        flat = self._flatten(data, config_key)
        has_credential = False
        for dotted_key, value in flat.items():
            env_var = _ENV_MAP.get(dotted_key)
            if env_var:
                str_value = str(value) if value is not None else ""
                if str_value:
                    os.environ[env_var] = str_value
                    if dotted_key in _SECRET_FIELDS:
                        has_credential = True
                elif env_var in os.environ:
                    del os.environ[env_var]

        if has_credential:
            logger.warning(
                "Credentials applied to current process only. "
                "For persistence, use environment variables or Kubernetes secrets."
            )

    @staticmethod
    def _strip_secrets(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Return a copy of data with all _SECRET_FIELDS replaced by empty strings.

        The original dict is not mutated.
        """
        result: dict[str, Any] = {}
        for key, val in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(val, dict):
                result[key] = ConfigManager._strip_secrets(val, full_key)
            elif full_key in _SECRET_FIELDS:
                result[key] = ""
            else:
                result[key] = val
        return result

    def _merge_sensitive(
        self, current: dict[str, Any], incoming: dict[str, Any], prefix: str
    ) -> dict[str, Any]:
        """Keep existing secret values when incoming field is empty."""
        merged = dict(incoming)
        for key, val in current.items():
            full_key = f"{prefix}.{key}"
            if isinstance(val, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_sensitive(val, merged[key], full_key)
            elif full_key in SENSITIVE_FIELDS:
                # If incoming is empty/None, keep current value
                if not merged.get(key):
                    merged[key] = val
        return merged

    def _mask_sensitive(self, data: dict[str, Any], prefix: str) -> dict[str, Any]:
        """Replace sensitive values with masked versions."""
        masked = {}
        for key, val in data.items():
            full_key = f"{prefix}.{key}"
            if isinstance(val, dict):
                masked[key] = self._mask_sensitive(val, full_key)
            elif full_key in SENSITIVE_FIELDS and val:
                # Show last 4 chars
                s = str(val)
                masked[key] = (
                    f"{'*' * max(0, len(s) - 4)}{s[-4:]}" if len(s) > 4 else "****"
                )
            else:
                masked[key] = val
        return masked

    @staticmethod
    def _set_nested(data: dict[str, Any], dotted_key: str, value: Any) -> None:
        """Set a value in a nested dict using dotted key notation."""
        keys = dotted_key.split(".")
        d = data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        # Attempt type coercion for numeric values
        try:
            value = int(value)
        except (ValueError, TypeError):
            pass
        d[keys[-1]] = value

    @staticmethod
    def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Flatten nested dict to dotted keys."""
        items: dict[str, Any] = {}
        for key, val in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(val, dict):
                items.update(ConfigManager._flatten(val, full_key))
            else:
                items[full_key] = val
        return items
