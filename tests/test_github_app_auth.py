#!/usr/bin/env python3
"""
Comprehensive tests for github_app_auth.py

Covers:
- GitHubAppConfig.from_env(): env var loading, key file loading, validation
- GitHubAppAuth._generate_jwt(): JWT creation, claims, algorithm
- get_installation_token(): API interaction, caching, expiry, errors
- get_authenticated_headers(): header structure
- list_installations(): API interaction, error handling
- get_installation_repos(): single page, pagination, error handling
- verify_webhook(): HMAC-SHA256 signature verification
"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from github_app_auth import GitHubAppAuth, GitHubAppConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rsa_private_key():
    """Generate a real RSA private key for JWT tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


@pytest.fixture
def rsa_public_key(rsa_private_key):
    """Derive the public key from the RSA private key fixture."""
    private_key = serialization.load_pem_private_key(
        rsa_private_key.encode("utf-8"), password=None
    )
    public_key = private_key.public_key()
    return public_key


@pytest.fixture
def app_config(rsa_private_key):
    """Create a GitHubAppConfig with a real RSA private key."""
    return GitHubAppConfig(
        app_id="123456",
        private_key=rsa_private_key,
        installation_id="78901234",
        webhook_secret="test-webhook-secret",
    )


@pytest.fixture
def auth(app_config):
    """Create a GitHubAppAuth instance with a valid config."""
    return GitHubAppAuth(app_config)


# ---------------------------------------------------------------------------
# 1. GitHubAppConfig.from_env()
# ---------------------------------------------------------------------------


class TestGitHubAppConfigFromEnv:
    """Tests for GitHubAppConfig.from_env() classmethod."""

    def test_valid_config_from_env_vars(self, rsa_private_key):
        """Config loads correctly when app_id and private_key are set in env."""
        env = {
            "GITHUB_APP_ID": "99999",
            "GITHUB_APP_PRIVATE_KEY": rsa_private_key,
            "GITHUB_APP_WEBHOOK_SECRET": "s3cret",
            "GITHUB_APP_INSTALLATION_ID": "55555",
        }
        with patch.dict("os.environ", env, clear=True):
            config = GitHubAppConfig.from_env()

        assert config.app_id == "99999"
        assert config.private_key == rsa_private_key
        assert config.webhook_secret == "s3cret"
        assert config.installation_id == "55555"

    def test_valid_config_from_key_file(self, rsa_private_key, tmp_path):
        """Config loads the private key from a file when path is provided."""
        key_file = tmp_path / "app.pem"
        key_file.write_text(rsa_private_key)
        key_file.chmod(0o600)

        env = {
            "GITHUB_APP_ID": "11111",
            "GITHUB_APP_PRIVATE_KEY_PATH": str(key_file),
        }
        with patch.dict("os.environ", env, clear=True):
            config = GitHubAppConfig.from_env()

        assert config.app_id == "11111"
        assert config.private_key == rsa_private_key

    def test_missing_app_id_raises_value_error(self):
        """ValueError is raised when GITHUB_APP_ID is not set."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GITHUB_APP_ID"):
                GitHubAppConfig.from_env()

    def test_missing_private_key_and_path_raises_value_error(self):
        """ValueError is raised when neither key nor key path is provided."""
        env = {"GITHUB_APP_ID": "12345"}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="GITHUB_APP_PRIVATE_KEY"):
                GitHubAppConfig.from_env()

    def test_key_file_not_found_raises_value_error(self, tmp_path):
        """ValueError is raised when the specified key file does not exist."""
        env = {
            "GITHUB_APP_ID": "12345",
            "GITHUB_APP_PRIVATE_KEY_PATH": str(tmp_path / "nonexistent.pem"),
        }
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="Private key file not found"):
                GitHubAppConfig.from_env()

    def test_loose_file_permissions_triggers_warning(
        self, rsa_private_key, tmp_path, caplog
    ):
        """A warning is logged when the key file has overly permissive mode."""
        key_file = tmp_path / "app.pem"
        key_file.write_text(rsa_private_key)
        key_file.chmod(0o644)

        env = {
            "GITHUB_APP_ID": "12345",
            "GITHUB_APP_PRIVATE_KEY_PATH": str(key_file),
        }
        with patch.dict("os.environ", env, clear=True):
            import logging

            with caplog.at_level(logging.WARNING, logger="github_app_auth"):
                config = GitHubAppConfig.from_env()

        assert "loose permissions" in caplog.text
        # Config should still load despite the warning
        assert config.app_id == "12345"

    def test_private_key_literal_newlines_replaced(self):
        """Literal \\n sequences in the private key are replaced with newlines."""
        fake_key = "-----BEGIN RSA PRIVATE KEY-----\\nABC\\n-----END RSA PRIVATE KEY-----"
        env = {
            "GITHUB_APP_ID": "12345",
            "GITHUB_APP_PRIVATE_KEY": fake_key,
        }
        with patch.dict("os.environ", env, clear=True):
            config = GitHubAppConfig.from_env()

        assert "\\n" not in config.private_key
        assert "\n" in config.private_key

    def test_optional_fields_default_to_none(self, rsa_private_key):
        """installation_id and webhook_secret default to None when not set."""
        env = {
            "GITHUB_APP_ID": "12345",
            "GITHUB_APP_PRIVATE_KEY": rsa_private_key,
        }
        with patch.dict("os.environ", env, clear=True):
            config = GitHubAppConfig.from_env()

        assert config.installation_id is None
        assert config.webhook_secret is None


# ---------------------------------------------------------------------------
# 2. GitHubAppAuth._generate_jwt()
# ---------------------------------------------------------------------------


class TestGenerateJWT:
    """Tests for GitHubAppAuth._generate_jwt()."""

    def test_returns_valid_jwt_string(self, auth):
        """_generate_jwt() returns a non-empty string."""
        token = auth._generate_jwt()

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT has 3 dot-separated parts
        assert len(token.split(".")) == 3

    def test_jwt_contains_correct_claims(self, auth, rsa_public_key):
        """JWT payload contains iss, iat, and exp with correct values."""
        before = int(time.time())
        token = auth._generate_jwt()
        after = int(time.time())

        decoded = jwt.decode(
            token,
            rsa_public_key,
            algorithms=["RS256"],
            options={"verify_exp": False},
        )

        assert decoded["iss"] == "123456"
        # iat is set to 60 seconds in the past
        assert before - 60 <= decoded["iat"] <= after - 60
        # exp is 10 minutes from now
        assert before + 600 <= decoded["exp"] <= after + 600

    def test_jwt_signed_with_rs256(self, auth, rsa_public_key):
        """JWT can be decoded with the matching public key using RS256."""
        token = auth._generate_jwt()

        # This will raise if algorithm or key doesn't match
        decoded = jwt.decode(
            token,
            rsa_public_key,
            algorithms=["RS256"],
        )

        assert "iss" in decoded

    def test_jwt_header_algorithm(self, auth):
        """JWT header specifies RS256 algorithm."""
        token = auth._generate_jwt()
        header = jwt.get_unverified_header(token)

        assert header["alg"] == "RS256"


# ---------------------------------------------------------------------------
# 3. get_installation_token()
# ---------------------------------------------------------------------------


class TestGetInstallationToken:
    """Tests for GitHubAppAuth.get_installation_token()."""

    def test_successful_token_retrieval(self, auth):
        """A successful API call returns the installation token."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_test_installation_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }

        with patch("github_app_auth.requests.post", return_value=mock_response):
            token = auth.get_installation_token("78901234")

        assert token == "ghs_test_installation_token"

    def test_caches_token_on_subsequent_calls(self, auth):
        """A cached token is reused without making another API call."""
        future_expiry = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_cached_token",
            "expires_at": future_expiry,
        }

        with patch("github_app_auth.requests.post", return_value=mock_response) as mock_post:
            token1 = auth.get_installation_token("78901234")
            token2 = auth.get_installation_token("78901234")

        assert token1 == "ghs_cached_token"
        assert token2 == "ghs_cached_token"
        # API should only be called once due to caching
        assert mock_post.call_count == 1

    def test_cache_miss_when_token_expired(self, auth):
        """A new token is fetched when the cached one is near expiry."""
        # Pre-populate cache with a token that expires very soon
        auth._installation_tokens["78901234"] = {
            "token": "ghs_old_token",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=2)
            ).isoformat(),
        }

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_fresh_token",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(hours=1)
            ).isoformat(),
        }

        with patch("github_app_auth.requests.post", return_value=mock_response):
            token = auth.get_installation_token("78901234")

        assert token == "ghs_fresh_token"

    def test_http_error_raises_runtime_error(self, auth):
        """RuntimeError is raised on non-201 API responses."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Bad credentials"

        with patch("github_app_auth.requests.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="HTTP 401"):
                auth.get_installation_token("78901234")

    def test_no_installation_id_raises_value_error(self):
        """ValueError is raised when no installation_id is provided or configured."""
        config = GitHubAppConfig(
            app_id="123456",
            private_key="fake-key",
            installation_id=None,
        )
        auth = GitHubAppAuth(config)

        with pytest.raises(ValueError, match="No installation ID"):
            auth.get_installation_token()

    def test_uses_default_installation_id(self, auth):
        """Uses config.installation_id when no explicit ID is passed."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_default_id_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }

        with patch("github_app_auth.requests.post", return_value=mock_response) as mock_post:
            token = auth.get_installation_token()

        assert token == "ghs_default_id_token"
        # Verify it used the config's installation_id in the URL
        call_url = mock_post.call_args[0][0]
        assert "78901234" in call_url


# ---------------------------------------------------------------------------
# 4. get_authenticated_headers()
# ---------------------------------------------------------------------------


class TestGetAuthenticatedHeaders:
    """Tests for GitHubAppAuth.get_authenticated_headers()."""

    def test_returns_authorization_bearer_header(self, auth):
        """Headers include Authorization with Bearer token."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_header_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }

        with patch("github_app_auth.requests.post", return_value=mock_response):
            headers = auth.get_authenticated_headers("78901234")

        assert headers["Authorization"] == "Bearer ghs_header_token"

    def test_returns_accept_header_for_github_api(self, auth):
        """Headers include the GitHub API Accept header."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_accept_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }

        with patch("github_app_auth.requests.post", return_value=mock_response):
            headers = auth.get_authenticated_headers("78901234")

        assert headers["Accept"] == "application/vnd.github+json"

    def test_returns_api_version_header(self, auth):
        """Headers include the X-GitHub-Api-Version header."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_version_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }

        with patch("github_app_auth.requests.post", return_value=mock_response):
            headers = auth.get_authenticated_headers("78901234")

        assert headers["X-GitHub-Api-Version"] == "2022-11-28"


# ---------------------------------------------------------------------------
# 5. list_installations()
# ---------------------------------------------------------------------------


class TestListInstallations:
    """Tests for GitHubAppAuth.list_installations()."""

    def test_successful_listing(self, auth):
        """Returns the list of installations from the API."""
        mock_installations = [
            {"id": 1, "account": {"login": "org1"}},
            {"id": 2, "account": {"login": "org2"}},
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_installations

        with patch("github_app_auth.requests.get", return_value=mock_response):
            result = auth.list_installations()

        assert result == mock_installations
        assert len(result) == 2

    def test_http_error_raises_runtime_error(self, auth):
        """RuntimeError is raised on non-200 API responses."""
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("github_app_auth.requests.get", return_value=mock_response):
            with pytest.raises(RuntimeError, match="HTTP 403"):
                auth.list_installations()

    def test_empty_installations_list(self, auth):
        """An empty list is returned when there are no installations."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch("github_app_auth.requests.get", return_value=mock_response):
            result = auth.list_installations()

        assert result == []


# ---------------------------------------------------------------------------
# 6. get_installation_repos()
# ---------------------------------------------------------------------------


class TestGetInstallationRepos:
    """Tests for GitHubAppAuth.get_installation_repos()."""

    def _mock_token_response(self):
        """Helper to create a mock response for get_installation_token."""
        mock = MagicMock()
        mock.status_code = 201
        mock.json.return_value = {
            "token": "ghs_repos_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        return mock

    def test_single_page_of_repos(self, auth):
        """Returns repos from a single-page API response."""
        repos = [{"name": "repo1"}, {"name": "repo2"}]

        mock_repos_response = MagicMock()
        mock_repos_response.status_code = 200
        mock_repos_response.json.return_value = {"repositories": repos}
        mock_repos_response.links = {}

        token_response = self._mock_token_response()

        with patch("github_app_auth.requests.post", return_value=token_response):
            with patch(
                "github_app_auth.requests.get", return_value=mock_repos_response
            ):
                result = auth.get_installation_repos("78901234")

        assert result == repos
        assert len(result) == 2

    def test_multi_page_pagination(self, auth):
        """Follows pagination links to collect repos from multiple pages."""
        page1_repos = [{"name": "repo1"}]
        page2_repos = [{"name": "repo2"}]

        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.json.return_value = {"repositories": page1_repos}
        page1_response.links = {
            "next": {"url": "https://api.github.com/installation/repositories?page=2"}
        }

        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.json.return_value = {"repositories": page2_repos}
        page2_response.links = {}

        token_response = self._mock_token_response()

        with patch("github_app_auth.requests.post", return_value=token_response):
            with patch(
                "github_app_auth.requests.get",
                side_effect=[page1_response, page2_response],
            ):
                result = auth.get_installation_repos("78901234")

        assert len(result) == 2
        assert result[0]["name"] == "repo1"
        assert result[1]["name"] == "repo2"

    def test_http_error_raises_runtime_error(self, auth):
        """RuntimeError is raised when the repos API returns an error."""
        mock_repos_response = MagicMock()
        mock_repos_response.status_code = 500

        token_response = self._mock_token_response()

        with patch("github_app_auth.requests.post", return_value=token_response):
            with patch(
                "github_app_auth.requests.get", return_value=mock_repos_response
            ):
                with pytest.raises(RuntimeError, match="HTTP 500"):
                    auth.get_installation_repos("78901234")

    def test_empty_repositories_key(self, auth):
        """Returns empty list when no repositories are present."""
        mock_repos_response = MagicMock()
        mock_repos_response.status_code = 200
        mock_repos_response.json.return_value = {"repositories": []}
        mock_repos_response.links = {}

        token_response = self._mock_token_response()

        with patch("github_app_auth.requests.post", return_value=token_response):
            with patch(
                "github_app_auth.requests.get", return_value=mock_repos_response
            ):
                result = auth.get_installation_repos("78901234")

        assert result == []


# ---------------------------------------------------------------------------
# 7. verify_webhook()
# ---------------------------------------------------------------------------


class TestVerifyWebhook:
    """Tests for GitHubAppAuth.verify_webhook()."""

    def test_valid_signature_returns_true(self, auth):
        """A correctly signed payload is accepted."""
        payload = b'{"action": "opened"}'
        expected_sig = "sha256=" + hmac.HMAC(
            key=b"test-webhook-secret", msg=payload, digestmod=hashlib.sha256
        ).hexdigest()

        result = auth.verify_webhook(payload, expected_sig)

        assert result is True

    def test_invalid_signature_returns_false(self, auth):
        """An incorrect signature is rejected."""
        payload = b'{"action": "opened"}'
        wrong_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

        result = auth.verify_webhook(payload, wrong_sig)

        assert result is False

    def test_missing_webhook_secret_returns_false(self, rsa_private_key):
        """Returns False when no webhook secret is configured."""
        config = GitHubAppConfig(
            app_id="123456",
            private_key=rsa_private_key,
            webhook_secret=None,
        )
        auth = GitHubAppAuth(config)
        payload = b'{"action": "opened"}'

        result = auth.verify_webhook(payload, "sha256=abc123")

        assert result is False

    def test_malformed_signature_returns_false(self, auth):
        """A signature without the sha256= prefix is rejected."""
        payload = b'{"action": "opened"}'
        # Compute a valid hex digest but with wrong prefix
        valid_hex = hmac.HMAC(
            key=b"test-webhook-secret", msg=payload, digestmod=hashlib.sha256
        ).hexdigest()

        result = auth.verify_webhook(payload, valid_hex)

        assert result is False

    def test_empty_signature_returns_false(self, auth):
        """An empty signature string is rejected."""
        payload = b'{"action": "opened"}'

        result = auth.verify_webhook(payload, "")

        assert result is False

    def test_different_payload_different_signature(self, auth):
        """A valid signature for a different payload is rejected."""
        payload = b'{"action": "opened"}'
        different_payload = b'{"action": "closed"}'

        sig_for_different = "sha256=" + hmac.HMAC(
            key=b"test-webhook-secret", msg=different_payload, digestmod=hashlib.sha256
        ).hexdigest()

        result = auth.verify_webhook(payload, sig_for_different)

        assert result is False

    def test_valid_empty_payload(self, auth):
        """Verification works correctly with an empty payload."""
        payload = b""
        expected_sig = "sha256=" + hmac.HMAC(
            key=b"test-webhook-secret", msg=payload, digestmod=hashlib.sha256
        ).hexdigest()

        result = auth.verify_webhook(payload, expected_sig)

        assert result is True


# ---------------------------------------------------------------------------
# 8. _get_headers() (internal helper)
# ---------------------------------------------------------------------------


class TestGetHeaders:
    """Tests for GitHubAppAuth._get_headers() internal method."""

    def test_headers_with_jwt(self, auth):
        """When use_jwt=True, headers include a Bearer JWT token."""
        headers = auth._get_headers(use_jwt=True)

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_headers_without_jwt(self, auth):
        """When use_jwt=False, headers do not include Authorization."""
        headers = auth._get_headers(use_jwt=False)

        assert "Authorization" not in headers
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"


# ---------------------------------------------------------------------------
# Fix 1 & 2: Network error handling and retry logic
# ---------------------------------------------------------------------------


class TestNetworkErrorHandling:
    """Tests for network error handling on requests.post / requests.get calls."""

    # --- get_installation_token ---

    def test_connection_error_raises_runtime_error(self, auth):
        """ConnectionError during get_installation_token raises RuntimeError with message."""
        import requests as req

        with patch(
            "github_app_auth.requests.post",
            side_effect=req.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(RuntimeError, match="Cannot reach GitHub API"):
                auth.get_installation_token("78901234")

    def test_timeout_raises_runtime_error(self, auth):
        """Timeout during get_installation_token raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.post",
            side_effect=req.exceptions.Timeout(),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                auth.get_installation_token("78901234")

    def test_request_exception_raises_runtime_error(self, auth):
        """Generic RequestException during get_installation_token raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.post",
            side_effect=req.exceptions.RequestException("bad"),
        ):
            with pytest.raises(RuntimeError, match="GitHub API request failed"):
                auth.get_installation_token("78901234")

    # --- list_installations ---

    def test_list_installations_connection_error(self, auth):
        """ConnectionError during list_installations raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.get",
            side_effect=req.exceptions.ConnectionError("refused"),
        ):
            with pytest.raises(RuntimeError, match="Cannot reach GitHub API"):
                auth.list_installations()

    def test_list_installations_timeout(self, auth):
        """Timeout during list_installations raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.get",
            side_effect=req.exceptions.Timeout(),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                auth.list_installations()

    def test_list_installations_request_exception(self, auth):
        """Generic RequestException during list_installations raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.get",
            side_effect=req.exceptions.RequestException("err"),
        ):
            with pytest.raises(RuntimeError, match="GitHub API request failed"):
                auth.list_installations()

    # --- get_installation_repos ---

    def _mock_token_response(self):
        mock = MagicMock()
        mock.status_code = 201
        mock.json.return_value = {
            "token": "ghs_repos_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        return mock

    def test_get_repos_connection_error(self, auth):
        """ConnectionError during get_installation_repos raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.post", return_value=self._mock_token_response()
        ):
            with patch(
                "github_app_auth.requests.get",
                side_effect=req.exceptions.ConnectionError("refused"),
            ):
                with pytest.raises(RuntimeError, match="Cannot reach GitHub API"):
                    auth.get_installation_repos("78901234")

    def test_get_repos_timeout(self, auth):
        """Timeout during get_installation_repos raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.post", return_value=self._mock_token_response()
        ):
            with patch(
                "github_app_auth.requests.get",
                side_effect=req.exceptions.Timeout(),
            ):
                with pytest.raises(RuntimeError, match="timed out"):
                    auth.get_installation_repos("78901234")

    def test_get_repos_request_exception(self, auth):
        """Generic RequestException during get_installation_repos raises RuntimeError."""
        import requests as req

        with patch(
            "github_app_auth.requests.post", return_value=self._mock_token_response()
        ):
            with patch(
                "github_app_auth.requests.get",
                side_effect=req.exceptions.RequestException("err"),
            ):
                with pytest.raises(RuntimeError, match="GitHub API request failed"):
                    auth.get_installation_repos("78901234")


class TestRetryLogic:
    """Tests for exponential backoff retry on transient HTTP errors."""

    def _mock_token_response(self):
        mock = MagicMock()
        mock.status_code = 201
        mock.json.return_value = {
            "token": "ghs_retry_token",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        return mock

    def test_get_installation_token_retries_on_429(self, auth):
        """get_installation_token retries on 429 and succeeds on 3rd attempt."""
        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 201
        success.json.return_value = {
            "token": "ghs_ok",
            "expires_at": "2099-01-01T00:00:00Z",
        }

        with patch("github_app_auth.requests.post", side_effect=[rate_limited, rate_limited, success]):
            with patch("time.sleep"):  # Suppress actual sleep in tests
                token = auth.get_installation_token("78901234")

        assert token == "ghs_ok"

    def test_get_installation_token_retries_on_503(self, auth):
        """get_installation_token retries on 503 and succeeds."""
        unavailable = MagicMock()
        unavailable.status_code = 503

        success = MagicMock()
        success.status_code = 201
        success.json.return_value = {
            "token": "ghs_ok",
            "expires_at": "2099-01-01T00:00:00Z",
        }

        with patch("github_app_auth.requests.post", side_effect=[unavailable, success]):
            with patch("time.sleep"):
                token = auth.get_installation_token("78901234")

        assert token == "ghs_ok"

    def test_get_installation_token_gives_up_after_3_retries(self, auth):
        """get_installation_token raises RuntimeError after 3 consecutive 429s."""
        rate_limited = MagicMock()
        rate_limited.status_code = 429

        with patch("github_app_auth.requests.post", return_value=rate_limited):
            with patch("time.sleep"):
                with pytest.raises(RuntimeError):
                    auth.get_installation_token("78901234")

    def test_list_installations_retries_on_500(self, auth):
        """list_installations retries on 500 and succeeds on next attempt."""
        server_error = MagicMock()
        server_error.status_code = 500

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = [{"id": 1}]

        with patch("github_app_auth.requests.get", side_effect=[server_error, success]):
            with patch("time.sleep"):
                result = auth.list_installations()

        assert result == [{"id": 1}]

    def test_get_installation_repos_retries_on_502(self, auth):
        """get_installation_repos retries on 502 and succeeds."""
        bad_gateway = MagicMock()
        bad_gateway.status_code = 502

        success_repos = MagicMock()
        success_repos.status_code = 200
        success_repos.json.return_value = {"repositories": [{"name": "repo1"}]}
        success_repos.links = {}

        with patch(
            "github_app_auth.requests.post", return_value=self._mock_token_response()
        ):
            with patch(
                "github_app_auth.requests.get",
                side_effect=[bad_gateway, success_repos],
            ):
                with patch("time.sleep"):
                    result = auth.get_installation_repos("78901234")

        assert len(result) == 1
        assert result[0]["name"] == "repo1"
