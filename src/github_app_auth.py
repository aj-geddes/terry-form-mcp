#!/usr/bin/env python3
"""
GitHub App Authentication Module
Handles OAuth app authentication and token management for GitHub integration.

Security hardened:
- Secure token storage and handling
- JWT token generation with expiration
- Installation token caching with TTL
"""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import requests

logger = logging.getLogger(__name__)

GITHUB_API_VERSION = "2022-11-28"

# HTTP status codes that warrant a retry with exponential backoff
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_RETRY_ATTEMPTS = 3


@dataclass
class GitHubAppConfig:
    """Configuration for GitHub App authentication"""

    app_id: str
    private_key: str
    installation_id: str | None = None
    webhook_secret: str | None = None

    @classmethod
    def from_env(cls) -> "GitHubAppConfig":
        """Create config from environment variables"""
        app_id = os.environ.get("GITHUB_APP_ID")
        if not app_id:
            raise ValueError("GITHUB_APP_ID environment variable not set")

        # Try to load private key from file or environment
        private_key = None
        private_key_path = os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH")

        if private_key_path:
            key_path = Path(private_key_path)
            if not key_path.exists():
                raise ValueError(f"Private key file not found: {private_key_path}")
            # Validate file permissions (should be owner-read-only)
            file_mode = key_path.stat().st_mode & 0o777
            if file_mode & 0o077:
                logger.warning(
                    f"Private key file {private_key_path} has loose permissions "
                    f"({oct(file_mode)}). Recommend chmod 600."
                )
            private_key = key_path.read_text()
        else:
            private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")
            if not private_key:
                raise ValueError(
                    "Neither GITHUB_APP_PRIVATE_KEY nor GITHUB_APP_PRIVATE_KEY_PATH is set"
                )

        # Replace literal \n with actual newlines in private key
        private_key = private_key.replace("\\n", "\n")

        return cls(
            app_id=app_id,
            private_key=private_key,
            installation_id=os.environ.get("GITHUB_APP_INSTALLATION_ID"),
            webhook_secret=os.environ.get("GITHUB_APP_WEBHOOK_SECRET"),
        )


class GitHubAppAuth:
    """Handles GitHub App authentication and token management"""

    def __init__(self, config: GitHubAppConfig):
        self.config = config
        self._installation_tokens: dict[str, dict[str, Any]] = {}
        self.base_url = "https://api.github.com"

    def _generate_jwt(self) -> str:
        """Generate a JWT token for GitHub App authentication"""
        # GitHub Apps use RS256 algorithm
        now = int(time.time())

        payload = {
            "iat": now
            - 60,  # Issued at time (60 seconds in the past to allow for clock drift)
            "exp": now + (10 * 60),  # JWT expiration time (10 minutes from now)
            "iss": self.config.app_id,  # GitHub App ID
        }

        return jwt.encode(payload, self.config.private_key, algorithm="RS256")

    def _get_headers(self, use_jwt: bool = True) -> dict[str, str]:
        """Get headers for GitHub API requests"""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }

        if use_jwt:
            headers["Authorization"] = f"Bearer {self._generate_jwt()}"

        return headers

    def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        """Execute an HTTP request with exponential backoff on transient errors.

        Retries up to _MAX_RETRY_ATTEMPTS times on status codes in
        _RETRYABLE_STATUS_CODES (429, 500, 502, 503, 504).  Network-level
        exceptions are translated into RuntimeError immediately.
        """
        request_fn = getattr(requests, method)
        last_response: requests.Response | None = None

        for attempt in range(_MAX_RETRY_ATTEMPTS):
            try:
                response = request_fn(url, **kwargs)
            except requests.exceptions.ConnectionError as exc:
                logger.error(f"Network error reaching GitHub API: {exc}")
                raise RuntimeError(
                    "Cannot reach GitHub API. Check network connectivity."
                ) from exc
            except requests.exceptions.Timeout:
                logger.error("Timeout reaching GitHub API")
                raise RuntimeError("GitHub API request timed out.") from None
            except requests.exceptions.RequestException as exc:
                logger.error(f"GitHub API request failed: {exc}")
                raise RuntimeError("GitHub API request failed.") from exc

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                return response

            last_response = response
            wait = 2**attempt  # 1s, 2s, 4s
            logger.warning(
                f"GitHub API returned {response.status_code} (attempt "
                f"{attempt + 1}/{_MAX_RETRY_ATTEMPTS}). Retrying in {wait}s."
            )
            time.sleep(wait)

        # All retries exhausted — return the last response so callers can
        # inspect the status code and raise their own errors.
        return last_response  # type: ignore[return-value]

    def get_installation_token(self, installation_id: str | None = None) -> str:
        """Get an installation access token"""
        install_id = installation_id or self.config.installation_id
        if not install_id:
            raise ValueError("No installation ID provided")

        # Check if we have a cached token that's still valid
        if install_id in self._installation_tokens:
            token_data = self._installation_tokens[install_id]
            expires_at = datetime.fromisoformat(
                token_data["expires_at"].replace("Z", "+00:00")
            )

            # If token expires in more than 5 minutes, reuse it
            if expires_at > datetime.now(expires_at.tzinfo) + timedelta(minutes=5):
                logger.debug(f"Using cached installation token for {install_id}")
                return token_data["token"]

        # Generate new installation token
        logger.info(f"Generating new installation token for {install_id}")

        url = f"{self.base_url}/app/installations/{install_id}/access_tokens"
        response = self._request_with_retry(
            "post", url, headers=self._get_headers(use_jwt=True), timeout=30
        )

        if response.status_code != 201:
            logger.error(
                f"Failed to get installation token: HTTP {response.status_code}"
            )
            raise RuntimeError(
                f"Failed to get installation token: HTTP {response.status_code}"
            )

        token_data = response.json()

        # Cache the token
        self._installation_tokens[install_id] = token_data

        return token_data["token"]

    def get_authenticated_headers(
        self, installation_id: str | None = None
    ) -> dict[str, str]:
        """Get headers with installation access token"""
        token = self.get_installation_token(installation_id)

        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }

    def list_installations(self) -> list[dict[str, Any]]:
        """List all installations of this GitHub App"""
        url = f"{self.base_url}/app/installations"

        response = self._request_with_retry(
            "get", url, headers=self._get_headers(use_jwt=True), timeout=30
        )

        if response.status_code != 200:
            logger.error(f"Failed to list installations: {response.status_code}")
            raise RuntimeError(
                f"Failed to list installations: HTTP {response.status_code}"
            )

        return response.json()

    def get_installation_repos(
        self, installation_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get repositories accessible to an installation"""
        headers = self.get_authenticated_headers(installation_id)

        url = f"{self.base_url}/installation/repositories"
        all_repos = []

        while url:
            response = self._request_with_retry("get", url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to get installation repos: {response.status_code}")
                raise RuntimeError(
                    f"Failed to get installation repos: HTTP {response.status_code}"
                )

            data = response.json()
            all_repos.extend(data.get("repositories", []))

            # Check for pagination
            links = response.links
            url = links.get("next", {}).get("url")

        return all_repos

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify a GitHub webhook signature"""
        if not self.config.webhook_secret:
            logger.error("No webhook secret configured, rejecting webhook")
            return False

        import hashlib
        import hmac

        expected_signature = (
            "sha256="
            + hmac.HMAC(
                key=self.config.webhook_secret.encode(),
                msg=payload,
                digestmod=hashlib.sha256,
            ).hexdigest()
        )

        return hmac.compare_digest(expected_signature, signature)
