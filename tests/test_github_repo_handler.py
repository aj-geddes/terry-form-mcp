#!/usr/bin/env python3
"""
Comprehensive tests for github_repo_handler.py

Covers:
- _get_repo_path(): path generation, owner/repo validation, special characters
- _sanitize_output(): token stripping from git URLs, clean text passthrough
- _validate_branch_name(): valid names, flag injection, path traversal, special chars
- clone_or_update_repo(): invalid branch rejection, mock subprocess clone/update paths
- list_terraform_files(): path traversal blocked, normal operation with mocked filesystem
- get_terraform_config(): path traversal blocked, content analysis
- prepare_terraform_workspace(): path traversal blocked, workspace preparation
- cleanup_old_repos(): basic operation with mocked filesystem
"""

import asyncio
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github_repo_handler import GitHubRepoHandler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_auth():
    """Create a mock GitHubAppAuth that returns a fake token."""
    auth = MagicMock()
    auth.get_installation_token.return_value = "ghp_fake_token_1234567890"
    auth.get_authenticated_headers.return_value = {
        "Authorization": "Bearer ghp_fake_token_1234567890",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return auth


@pytest.fixture
def handler(tmp_path, mock_auth):
    """Create a GitHubRepoHandler with a real temporary workspace root."""
    return GitHubRepoHandler(auth=mock_auth, workspace_root=str(tmp_path))


@pytest.fixture
def handler_with_repo(handler, tmp_path):
    """Create a handler with a pre-existing repository directory on disk."""
    repo_dir = tmp_path / "github-repos" / "test-owner_test-repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    return handler, repo_dir


# ---------------------------------------------------------------------------
# 1. _get_repo_path()
# ---------------------------------------------------------------------------


class TestGetRepoPath:
    """Tests for the _get_repo_path method."""

    def test_returns_correct_path_format(self, handler, tmp_path):
        """Path should be workspace_root/github-repos/owner_repo."""
        result = handler._get_repo_path("myowner", "myrepo")
        expected = tmp_path / "github-repos" / "myowner_myrepo"
        assert result == expected

    def test_handles_hyphenated_owner(self, handler, tmp_path):
        """Owner names with hyphens should be accepted."""
        result = handler._get_repo_path("my-owner", "repo")
        expected = tmp_path / "github-repos" / "my-owner_repo"
        assert result == expected

    def test_handles_underscore_in_names(self, handler, tmp_path):
        """Underscores in owner and repo names should be accepted."""
        result = handler._get_repo_path("my_owner", "my_repo")
        expected = tmp_path / "github-repos" / "my_owner_my_repo"
        assert result == expected

    def test_handles_dots_in_repo_name(self, handler, tmp_path):
        """Dots in repository names should be accepted (e.g., terraform.aws)."""
        result = handler._get_repo_path("owner", "terraform.aws")
        expected = tmp_path / "github-repos" / "owner_terraform.aws"
        assert result == expected

    def test_rejects_owner_with_special_chars(self, handler):
        """Owner names containing special characters should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository owner name"):
            handler._get_repo_path("owner/evil", "repo")

    def test_rejects_owner_with_spaces(self, handler):
        """Owner names with spaces should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository owner name"):
            handler._get_repo_path("my owner", "repo")

    def test_rejects_owner_with_dots(self, handler):
        """Owner names with dots should raise ValueError (dots not allowed in owner)."""
        with pytest.raises(ValueError, match="Invalid repository owner name"):
            handler._get_repo_path("my.owner", "repo")

    def test_rejects_repo_with_slash(self, handler):
        """Repo names with slashes should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository name"):
            handler._get_repo_path("owner", "repo/evil")

    def test_rejects_repo_with_semicolon(self, handler):
        """Repo names with semicolons should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository name"):
            handler._get_repo_path("owner", "repo;rm -rf /")

    def test_rejects_empty_owner(self, handler):
        """Empty owner string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository owner name"):
            handler._get_repo_path("", "repo")

    def test_rejects_empty_repo(self, handler):
        """Empty repo string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository name"):
            handler._get_repo_path("owner", "")

    def test_rejects_owner_with_backtick(self, handler):
        """Backtick injection in owner should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository owner name"):
            handler._get_repo_path("`whoami`", "repo")

    def test_rejects_repo_with_dollar_sign(self, handler):
        """Dollar sign injection in repo should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repository name"):
            handler._get_repo_path("owner", "$(evil)")

    def test_numeric_owner_and_repo(self, handler, tmp_path):
        """Purely numeric names should be accepted."""
        result = handler._get_repo_path("12345", "67890")
        expected = tmp_path / "github-repos" / "12345_67890"
        assert result == expected

    def test_returns_path_object(self, handler):
        """Return type should be a Path instance."""
        result = handler._get_repo_path("owner", "repo")
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# 2. _sanitize_output()
# ---------------------------------------------------------------------------


class TestSanitizeOutput:
    """Tests for the _sanitize_output method."""

    def test_strips_token_from_https_url(self, handler):
        """Token embedded in HTTPS clone URL should be replaced with ***."""
        text = "Cloning https://x-access-token:ghp_secret123@github.com/owner/repo.git"
        result = handler._sanitize_output(text)
        assert "ghp_secret123" not in result
        assert "https://***@github.com/owner/repo.git" in result

    def test_strips_token_from_basic_auth_url(self, handler):
        """Basic auth credentials should be stripped from URLs."""
        text = "remote: https://user:password@github.com/owner/repo.git"
        result = handler._sanitize_output(text)
        assert "password" not in result
        assert "https://***@" in result

    def test_clean_text_unchanged(self, handler):
        """Text without credentials should pass through unchanged."""
        text = "Already up to date.\nNothing to commit."
        result = handler._sanitize_output(text)
        assert result == text

    def test_empty_string(self, handler):
        """Empty string should be returned as-is."""
        assert handler._sanitize_output("") == ""

    def test_multiple_tokens_in_output(self, handler):
        """Multiple token-bearing URLs in the same output should all be sanitized."""
        text = (
            "Fetching https://token1@github.com/a/b.git\n"
            "Pushing https://token2@github.com/c/d.git"
        )
        result = handler._sanitize_output(text)
        assert "token1" not in result
        assert "token2" not in result
        assert result.count("https://***@") == 2

    def test_preserves_plain_https_url(self, handler):
        """HTTPS URLs without embedded credentials should not be modified."""
        text = "Cloning https://github.com/owner/repo.git"
        result = handler._sanitize_output(text)
        assert result == text

    def test_long_token_stripped(self, handler):
        """A long/complex token string should be fully stripped."""
        token = "ghs_ABCDEFghijklmnop1234567890abcdef"
        text = f"https://x-access-token:{token}@github.com/o/r.git"
        result = handler._sanitize_output(text)
        assert token not in result


# ---------------------------------------------------------------------------
# 3. _validate_branch_name()
# ---------------------------------------------------------------------------


class TestValidateBranchName:
    """Tests for the _validate_branch_name method."""

    # -- Valid branch names -------------------------------------------------

    def test_simple_branch_name(self, handler):
        """A simple branch name like 'main' should pass."""
        assert handler._validate_branch_name("main") is True

    def test_branch_with_slash(self, handler):
        """Feature branches with slashes should pass (e.g., feature/my-branch)."""
        assert handler._validate_branch_name("feature/my-branch") is True

    def test_branch_with_dots(self, handler):
        """Branch names with dots should pass (e.g., release/v1.2.3)."""
        assert handler._validate_branch_name("release/v1.2.3") is True

    def test_branch_with_underscores(self, handler):
        """Branch names with underscores should pass."""
        assert handler._validate_branch_name("my_feature_branch") is True

    def test_branch_with_hyphens(self, handler):
        """Branch names with hyphens should pass."""
        assert handler._validate_branch_name("fix-bug-123") is True

    def test_numeric_branch(self, handler):
        """Purely numeric branch names should pass."""
        assert handler._validate_branch_name("12345") is True

    # -- Flag injection blocked ---------------------------------------------

    def test_rejects_leading_dash(self, handler):
        """Branch starting with '-' could be a git flag injection; must be rejected."""
        assert handler._validate_branch_name("-b") is False

    def test_rejects_double_dash_flag(self, handler):
        """Double-dash git flags must be rejected."""
        assert handler._validate_branch_name("--upload-pack") is False

    def test_rejects_flag_with_equals(self, handler):
        """Flag-style arguments with equals sign must be rejected."""
        assert handler._validate_branch_name("--exec=evil") is False

    # -- Path traversal blocked ---------------------------------------------

    def test_rejects_double_dot(self, handler):
        """Branch names containing '..' should be rejected (path traversal)."""
        assert handler._validate_branch_name("feature/../etc/passwd") is False

    def test_rejects_bare_double_dot(self, handler):
        """Bare '..' should be rejected."""
        assert handler._validate_branch_name("..") is False

    def test_rejects_double_dot_at_start(self, handler):
        """'..' at the beginning of a branch name should be rejected."""
        assert handler._validate_branch_name("../main") is False

    # -- Special characters rejected ----------------------------------------

    def test_rejects_space(self, handler):
        """Branch names with spaces should be rejected."""
        assert handler._validate_branch_name("my branch") is False

    def test_rejects_backtick(self, handler):
        """Backtick injection should be rejected."""
        assert handler._validate_branch_name("`whoami`") is False

    def test_rejects_dollar_sign(self, handler):
        """Dollar sign injection should be rejected."""
        assert handler._validate_branch_name("$(evil)") is False

    def test_rejects_semicolon(self, handler):
        """Semicolons that could chain commands should be rejected."""
        assert handler._validate_branch_name("main;rm -rf /") is False

    def test_rejects_pipe(self, handler):
        """Pipe characters should be rejected."""
        assert handler._validate_branch_name("main|cat /etc/passwd") is False

    def test_rejects_ampersand(self, handler):
        """Ampersand characters should be rejected."""
        assert handler._validate_branch_name("main&&evil") is False

    def test_rejects_tilde(self, handler):
        """Tilde characters should be rejected."""
        assert handler._validate_branch_name("~user") is False

    def test_rejects_caret(self, handler):
        """Caret characters should be rejected."""
        assert handler._validate_branch_name("HEAD^") is False

    def test_rejects_colon(self, handler):
        """Colon characters should be rejected."""
        assert handler._validate_branch_name("refs:heads/main") is False

    def test_rejects_empty_string(self, handler):
        """An empty branch name should be rejected (no match on regex)."""
        assert handler._validate_branch_name("") is False


# ---------------------------------------------------------------------------
# 4. _run_git_command()
# ---------------------------------------------------------------------------


class TestRunGitCommand:
    """Tests for the _run_git_command async method."""

    @pytest.mark.asyncio
    async def test_successful_command(self, handler, tmp_path):
        """A successful git command returns success=True with stdout."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"output data", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await handler._run_git_command(
                ["git", "status"], tmp_path
            )

            assert result["success"] is True
            assert result["stdout"] == "output data"
            assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_failed_command(self, handler, tmp_path):
        """A failing git command returns success=False with stderr."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"fatal: not a git repo")
            mock_process.returncode = 128
            mock_exec.return_value = mock_process

            result = await handler._run_git_command(
                ["git", "status"], tmp_path
            )

            assert result["success"] is False
            assert "not a git repo" in result["stderr"]
            assert result["returncode"] == 128

    @pytest.mark.asyncio
    async def test_sanitizes_output_tokens(self, handler, tmp_path):
        """Tokens in stdout/stderr should be sanitized."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                b"Cloning https://x-access-token:secret@github.com/o/r.git",
                b"",
            )
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await handler._run_git_command(
                ["git", "clone", "url"], tmp_path
            )

            assert "secret" not in result["stdout"]
            assert "***" in result["stdout"]

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, handler, tmp_path):
        """A timed-out git command should return a timeout error."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.side_effect = asyncio.TimeoutError()
            mock_process.kill = MagicMock()
            mock_process.wait = AsyncMock()
            mock_exec.return_value = mock_process

            result = await handler._run_git_command(
                ["git", "clone", "url"], tmp_path
            )

            assert result["success"] is False
            assert "timed out" in result["stderr"].lower()
            assert result["returncode"] == -1

    @pytest.mark.asyncio
    async def test_exception_returns_error(self, handler, tmp_path):
        """An unexpected exception during execution should return an error."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = OSError("No such file or directory")

            result = await handler._run_git_command(
                ["git", "status"], tmp_path
            )

            assert result["success"] is False
            assert "No such file or directory" in result["stderr"]
            assert result["returncode"] == -1

    @pytest.mark.asyncio
    async def test_uses_minimal_env(self, handler, tmp_path):
        """The subprocess should be called with a minimal environment."""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (b"", b"")
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            await handler._run_git_command(["git", "status"], tmp_path)

            call_kwargs = mock_exec.call_args
            env = call_kwargs.kwargs["env"]
            assert "GIT_TERMINAL_PROMPT" in env
            assert env["GIT_TERMINAL_PROMPT"] == "0"
            # Should only contain HOME, PATH, GIT_TERMINAL_PROMPT
            assert set(env.keys()) == {"HOME", "PATH", "GIT_TERMINAL_PROMPT"}


# ---------------------------------------------------------------------------
# 5. clone_or_update_repo()
# ---------------------------------------------------------------------------


class TestCloneOrUpdateRepo:
    """Tests for the clone_or_update_repo async method."""

    @pytest.mark.asyncio
    async def test_invalid_branch_returns_error(self, handler):
        """An invalid branch name should return an error without executing git."""
        result = await handler.clone_or_update_repo(
            "owner", "repo", branch="--upload-pack=evil"
        )
        assert "error" in result
        assert "Invalid branch name" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_branch_with_double_dot(self, handler):
        """A branch containing '..' should be rejected."""
        result = await handler.clone_or_update_repo(
            "owner", "repo", branch="../etc/passwd"
        )
        assert "error" in result
        assert "Invalid branch name" in result["error"]

    @pytest.mark.asyncio
    async def test_clone_new_repo(self, handler, mock_auth):
        """Cloning a new repo should call git clone and return success."""
        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": True,
                "stdout": "Cloning into...",
                "stderr": "",
                "returncode": 0,
            }

            result = await handler.clone_or_update_repo("owner", "repo")

            assert result["success"] is True
            assert result["action"] == "cloned"
            assert "path" in result

            # Verify git clone was called
            call_args = mock_run.call_args[0][0]
            assert "git" in call_args
            assert "clone" in call_args

    @pytest.mark.asyncio
    async def test_clone_with_branch(self, handler, mock_auth):
        """Cloning with a branch should include -b flag in clone command."""
        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": True,
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            }

            result = await handler.clone_or_update_repo(
                "owner", "repo", branch="develop"
            )

            assert result["success"] is True
            assert result["branch"] == "develop"

            call_args = mock_run.call_args[0][0]
            assert "-b" in call_args
            assert "develop" in call_args

    @pytest.mark.asyncio
    async def test_clone_failure_returns_error(self, handler, mock_auth):
        """Failed clone should return error with sanitized URL."""
        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": False,
                "stdout": "",
                "stderr": "fatal: repository not found",
                "returncode": 128,
            }

            result = await handler.clone_or_update_repo("owner", "repo")

            assert "error" in result
            assert "Failed to clone" in result["error"]
            assert "clone_url_sanitized" in result
            assert "github.com/owner/repo" in result["clone_url_sanitized"]

    @pytest.mark.asyncio
    async def test_update_existing_repo(self, handler_with_repo, mock_auth):
        """Updating an existing repo should fetch and return updated action."""
        handler, repo_dir = handler_with_repo

        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": True,
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            }

            result = await handler.clone_or_update_repo("test-owner", "test-repo")

            assert result["success"] is True
            assert result["action"] == "updated"

            # First call should be fetch --all --prune
            first_call_args = mock_run.call_args_list[0][0][0]
            assert "fetch" in first_call_args
            assert "--all" in first_call_args

    @pytest.mark.asyncio
    async def test_update_with_branch_checkout(self, handler_with_repo, mock_auth):
        """Updating with a branch should attempt checkout after fetch."""
        handler, repo_dir = handler_with_repo

        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": True,
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            }

            result = await handler.clone_or_update_repo(
                "test-owner", "test-repo", branch="develop"
            )

            assert result["success"] is True
            assert result["branch"] == "develop"

            # Should have called: fetch, checkout, pull
            assert mock_run.call_count >= 2
            checkout_call = mock_run.call_args_list[1][0][0]
            assert "checkout" in checkout_call
            assert "develop" in checkout_call

    @pytest.mark.asyncio
    async def test_force_reclone(self, handler_with_repo, mock_auth):
        """force=True should remove existing dir and clone fresh."""
        handler, repo_dir = handler_with_repo

        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": True,
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            }

            result = await handler.clone_or_update_repo(
                "test-owner", "test-repo", force=True
            )

            assert result["success"] is True
            assert result["action"] == "cloned"

            # Verify clone was called (not fetch)
            call_args = mock_run.call_args[0][0]
            assert "clone" in call_args

    @pytest.mark.asyncio
    async def test_update_fetch_failure(self, handler_with_repo, mock_auth):
        """Failed fetch during update should return error."""
        handler, repo_dir = handler_with_repo

        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": False,
                "stdout": "",
                "stderr": "fatal: could not read from remote",
                "returncode": 128,
            }

            result = await handler.clone_or_update_repo("test-owner", "test-repo")

            assert "error" in result
            assert "Failed to fetch" in result["error"]

    @pytest.mark.asyncio
    async def test_no_branch_returns_default(self, handler, mock_auth):
        """When no branch is specified, result should show 'default'."""
        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": True,
                "stdout": "",
                "stderr": "",
                "returncode": 0,
            }

            result = await handler.clone_or_update_repo("owner", "repo")

            assert result["branch"] == "default"


# ---------------------------------------------------------------------------
# 5b. Token exposure in clone_or_update_repo() exception paths
# ---------------------------------------------------------------------------


class TestTokenNotExposedOnCloneError:
    """Security tests: installation token must never appear in any error response.

    The installation token is embedded in the git clone URL as
    ``https://x-access-token:{token}@github.com/...``.  If a subprocess
    exception surfaces (e.g. OSError from create_subprocess_exec) and the
    exception message contains the raw URL, the token could leak through
    the ``stderr`` field returned by ``_run_git_command`` and then through
    the ``error`` field returned by ``clone_or_update_repo``.
    """

    TOKEN = "ghp_fake_token_1234567890"

    def _result_contains_token(self, result: dict, token: str) -> bool:
        """Check every string value in the result dict for the token."""
        for value in result.values():
            if isinstance(value, str) and token in value:
                return True
        return False

    @pytest.mark.asyncio
    async def test_token_not_in_error_when_subprocess_raises_oserror(
        self, handler, mock_auth
    ):
        """Token must not appear in the result when create_subprocess_exec raises OSError.

        Some OS error messages include the command arguments in their text,
        which would expose the token-bearing clone URL.  The handler must
        sanitize before returning.
        """
        token = self.TOKEN
        # Simulate an OSError whose message includes the token-bearing URL
        # (e.g. "No such file or directory: 'git'" from a misconfigured system
        # where the full argv is embedded in the exception string).
        error_message = (
            f"[Errno 2] No such file or directory — "
            f"cmd=['git','clone','https://x-access-token:{token}@github.com/owner/repo.git']"
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = OSError(error_message)

            result = await handler.clone_or_update_repo("owner", "repo")

        assert "success" not in result or result.get("success") is False
        assert not self._result_contains_token(result, token), (
            f"Installation token '{token}' was found in clone_or_update_repo result: {result}"
        )

    @pytest.mark.asyncio
    async def test_token_not_in_error_when_subprocess_raises_generic_exception(
        self, handler, mock_auth
    ):
        """Token must not appear in the result when any Exception is raised from subprocess.

        A generic RuntimeError or ValueError that somehow includes the clone
        URL must not expose the token.
        """
        token = self.TOKEN
        error_message = (
            f"Subprocess setup failed for "
            f"https://x-access-token:{token}@github.com/owner/repo.git"
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = RuntimeError(error_message)

            result = await handler.clone_or_update_repo("owner", "repo")

        assert not self._result_contains_token(result, token), (
            f"Installation token found in result after RuntimeError: {result}"
        )

    @pytest.mark.asyncio
    async def test_sanitized_url_used_in_clone_failure_error_field(
        self, handler, mock_auth
    ):
        """The 'error' field on clone failure must use the sanitized URL, not the token URL."""
        token = self.TOKEN

        with patch.object(handler, "_run_git_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "success": False,
                "stdout": "",
                "stderr": "fatal: repository not found",
                "returncode": 128,
            }

            result = await handler.clone_or_update_repo("owner", "repo")

        assert token not in str(result), (
            f"Installation token found in clone failure result: {result}"
        )
        # The sanitized URL (no token) should appear instead
        assert "clone_url_sanitized" in result
        assert token not in result["clone_url_sanitized"]
        assert "github.com/owner/repo" in result["clone_url_sanitized"]

    @pytest.mark.asyncio
    async def test_run_git_command_sanitizes_exception_message(self, handler, tmp_path):
        """_run_git_command must sanitize the token from exception messages.

        When create_subprocess_exec raises an exception whose str()
        representation contains the token-bearing URL, _run_git_command
        must strip it before returning in the 'stderr' field.
        """
        token = self.TOKEN
        raw_exception = OSError(
            f"failed: https://x-access-token:{token}@github.com/o/r.git"
        )

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = raw_exception

            result = await handler._run_git_command(["git", "clone", "url"], tmp_path)

        assert result["success"] is False
        assert token not in result.get("stderr", ""), (
            f"Token found in _run_git_command stderr: {result['stderr']!r}"
        )


# ---------------------------------------------------------------------------
# 6. list_terraform_files()
# ---------------------------------------------------------------------------


class TestListTerraformFiles:
    """Tests for the list_terraform_files async method."""

    @pytest.mark.asyncio
    async def test_repo_not_found(self, handler):
        """Listing files for a non-existent repo should return error."""
        result = await handler.list_terraform_files("owner", "repo")
        assert "error" in result
        assert "not found locally" in result["error"]

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, handler_with_repo):
        """Path traversal via '..' should be blocked."""
        handler, repo_dir = handler_with_repo

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", path="../../etc"
        )
        assert "error" in result
        assert "traversal" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_path_not_found(self, handler_with_repo):
        """Listing a non-existent subdirectory should return error."""
        handler, repo_dir = handler_with_repo

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", path="nonexistent"
        )
        assert "error" in result
        assert "Path not found" in result["error"]

    @pytest.mark.asyncio
    async def test_lists_tf_files(self, handler_with_repo):
        """Should list .tf files in the repository directory."""
        handler, repo_dir = handler_with_repo

        # Create some terraform files
        (repo_dir / "main.tf").write_text('resource "aws_instance" "example" {}')
        (repo_dir / "variables.tf").write_text('variable "region" {}')
        (repo_dir / "README.md").write_text("# Not a TF file")

        result = await handler.list_terraform_files("test-owner", "test-repo")

        assert result["success"] is True
        assert result["count"] == 2
        file_names = [f["name"] for f in result["files"]]
        assert "main.tf" in file_names
        assert "variables.tf" in file_names
        assert "README.md" not in file_names

    @pytest.mark.asyncio
    async def test_lists_tf_files_in_subdirectory(self, handler_with_repo):
        """Should list .tf files in a subdirectory."""
        handler, repo_dir = handler_with_repo

        subdir = repo_dir / "modules" / "vpc"
        subdir.mkdir(parents=True)
        (subdir / "main.tf").write_text('resource "aws_vpc" "main" {}')
        (repo_dir / "root.tf").write_text('module "vpc" {}')

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", path="modules/vpc"
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["files"][0]["name"] == "main.tf"

    @pytest.mark.asyncio
    async def test_empty_directory(self, handler_with_repo):
        """An empty repository directory should return count=0."""
        handler, repo_dir = handler_with_repo

        result = await handler.list_terraform_files("test-owner", "test-repo")

        assert result["success"] is True
        assert result["count"] == 0
        assert result["files"] == []

    @pytest.mark.asyncio
    async def test_file_metadata_returned(self, handler_with_repo):
        """Each file entry should include path, name, size, and modified."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "main.tf").write_text("# terraform config\n" * 10)

        result = await handler.list_terraform_files("test-owner", "test-repo")

        assert result["count"] == 1
        file_info = result["files"][0]
        assert "path" in file_info
        assert "name" in file_info
        assert "size" in file_info
        assert "modified" in file_info
        assert file_info["name"] == "main.tf"
        assert file_info["size"] > 0

    @pytest.mark.asyncio
    async def test_recursive_listing(self, handler_with_repo):
        """Terraform files in nested directories should be found (rglob)."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "main.tf").write_text("# root")
        nested = repo_dir / "modules" / "networking"
        nested.mkdir(parents=True)
        (nested / "vpc.tf").write_text("# nested")

        result = await handler.list_terraform_files("test-owner", "test-repo")

        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_results_sorted_by_path(self, handler_with_repo):
        """Results should be sorted by relative path."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "z_last.tf").write_text("# z")
        (repo_dir / "a_first.tf").write_text("# a")

        result = await handler.list_terraform_files("test-owner", "test-repo")

        paths = [f["path"] for f in result["files"]]
        assert paths == sorted(paths)


# ---------------------------------------------------------------------------
# 7. get_terraform_config()
# ---------------------------------------------------------------------------


class TestGetTerraformConfig:
    """Tests for the get_terraform_config async method."""

    @pytest.mark.asyncio
    async def test_repo_not_found(self, handler):
        """Getting config from a non-existent repo should return error."""
        result = await handler.get_terraform_config("owner", "repo", "infra")
        assert "error" in result
        assert "not found locally" in result["error"]

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, handler_with_repo):
        """Path traversal via '..' should be blocked."""
        handler, repo_dir = handler_with_repo

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", "../../etc"
        )
        assert "error" in result
        assert "traversal" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_config_path_not_found(self, handler_with_repo):
        """Non-existent config path should return error."""
        handler, repo_dir = handler_with_repo

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", "nonexistent"
        )
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_detects_backend(self, handler_with_repo):
        """Should detect backend configuration in .tf files."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "backend.tf").write_text(
            'terraform {\n  backend "s3" {\n    bucket = "my-bucket"\n  }\n}'
        )

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert result["has_backend"] is True

    @pytest.mark.asyncio
    async def test_detects_variables(self, handler_with_repo):
        """Should detect variable definitions."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "variables.tf").write_text(
            'variable "region" {\n  default = "us-east-1"\n}'
        )

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert result["has_variables"] is True

    @pytest.mark.asyncio
    async def test_detects_outputs(self, handler_with_repo):
        """Should detect output definitions."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "outputs.tf").write_text(
            'output "vpc_id" {\n  value = aws_vpc.main.id\n}'
        )

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert result["has_outputs"] is True

    @pytest.mark.asyncio
    async def test_detects_providers(self, handler_with_repo):
        """Should detect and extract provider names."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "providers.tf").write_text(
            'provider "aws" {\n  region = "us-east-1"\n}\n\n'
            'provider "google" {\n  project = "my-project"\n}'
        )

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert "aws" in result["providers"]
        assert "google" in result["providers"]

    @pytest.mark.asyncio
    async def test_detects_modules_directory(self, handler_with_repo):
        """Should detect module subdirectories."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "main.tf").write_text("# root config")
        modules_dir = repo_dir / "modules"
        (modules_dir / "vpc").mkdir(parents=True)
        (modules_dir / "ecs").mkdir(parents=True)

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert set(result["modules"]) == {"vpc", "ecs"}

    @pytest.mark.asyncio
    async def test_lists_terraform_files(self, handler_with_repo):
        """Should list all .tf file names in the config directory."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "main.tf").write_text("# main")
        (repo_dir / "variables.tf").write_text("# vars")
        (repo_dir / "README.md").write_text("# readme")

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert "main.tf" in result["terraform_files"]
        assert "variables.tf" in result["terraform_files"]
        assert "README.md" not in result["terraform_files"]

    @pytest.mark.asyncio
    async def test_detects_common_files(self, handler_with_repo):
        """Should detect terraform.tfvars and .terraform.lock.hcl."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "main.tf").write_text("# main")
        (repo_dir / "terraform.tfvars").write_text('region = "us-east-1"')
        (repo_dir / ".terraform.lock.hcl").write_text("# lock")

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert result.get("has_terraform_tfvars") is True
        assert result.get("has__terraform_lock_hcl") is True

    @pytest.mark.asyncio
    async def test_no_backend_no_variables_no_outputs(self, handler_with_repo):
        """Empty config should have all flags False."""
        handler, repo_dir = handler_with_repo

        (repo_dir / "main.tf").write_text("# just a comment")

        result = await handler.get_terraform_config(
            "test-owner", "test-repo", ""
        )

        assert result["success"] is True
        assert result["has_backend"] is False
        assert result["has_variables"] is False
        assert result["has_outputs"] is False
        assert result["providers"] == []


# ---------------------------------------------------------------------------
# 8. prepare_terraform_workspace()
# ---------------------------------------------------------------------------


class TestPrepareTerraformWorkspace:
    """Tests for the prepare_terraform_workspace async method."""

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, handler_with_repo, mock_auth):
        """Path traversal in config_path should be blocked."""
        handler, repo_dir = handler_with_repo

        # Mock clone_or_update_repo to succeed
        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "../../etc"
            )

            assert "error" in result
            assert "traversal" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_clone_error_propagated(self, handler, mock_auth):
        """If clone_or_update_repo fails, error should propagate."""
        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"error": "Failed to clone repository"}

            result = await handler.prepare_terraform_workspace(
                "owner", "repo", "infra"
            )

            assert "error" in result
            assert "Failed to clone" in result["error"]

    @pytest.mark.asyncio
    async def test_config_path_not_found(self, handler_with_repo, mock_auth):
        """Non-existent config path should return error after clone succeeds."""
        handler, repo_dir = handler_with_repo

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "nonexistent"
            )

            assert "error" in result
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_successful_workspace_preparation(self, handler_with_repo, mock_auth, tmp_path):
        """Successful preparation should copy files to workspace directory."""
        handler, repo_dir = handler_with_repo

        # Create terraform files in repo
        infra_dir = repo_dir / "infra"
        infra_dir.mkdir()
        (infra_dir / "main.tf").write_text('resource "aws_instance" "web" {}')
        (infra_dir / "variables.tf").write_text('variable "region" {}')

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "infra"
            )

            assert result["success"] is True
            assert "workspace_path" in result
            assert "workspace_name" in result

            # Verify files were copied
            workspace_path = Path(result["workspace_path"])
            assert workspace_path.exists()
            assert (workspace_path / "main.tf").exists()
            assert (workspace_path / "variables.tf").exists()

    @pytest.mark.asyncio
    async def test_custom_workspace_name(self, handler_with_repo, mock_auth):
        """Custom workspace_name should be used for the workspace directory."""
        handler, repo_dir = handler_with_repo

        # Create a minimal config dir
        (repo_dir / "main.tf").write_text("# minimal")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "", workspace_name="custom-ws"
            )

            assert result["success"] is True
            assert result["workspace_name"] == "custom-ws"
            assert "custom-ws" in result["workspace_path"]

    @pytest.mark.asyncio
    async def test_overwrites_existing_workspace(self, handler_with_repo, mock_auth, tmp_path):
        """If workspace already exists, it should be removed and re-created."""
        handler, repo_dir = handler_with_repo

        # Create terraform files
        (repo_dir / "main.tf").write_text("# v2 content")

        # Pre-create the workspace directory with old content
        workspace_dir = tmp_path / "terraform-workspaces" / "custom-ws"
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "old_file.tf").write_text("# old content")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "", workspace_name="custom-ws"
            )

            assert result["success"] is True
            workspace_path = Path(result["workspace_path"])
            # Old file should be gone, new file should exist
            assert not (workspace_path / "old_file.tf").exists()
            assert (workspace_path / "main.tf").exists()


# ---------------------------------------------------------------------------
# 9. cleanup_old_repos()
# ---------------------------------------------------------------------------


class TestCleanupOldRepos:
    """Tests for the cleanup_old_repos async method."""

    @pytest.mark.asyncio
    async def test_no_repos_dir(self, mock_auth, tmp_path):
        """When repos directory does not exist, should return success with 0 cleaned."""
        # Create handler with workspace, but delete the repos dir
        handler = GitHubRepoHandler(auth=mock_auth, workspace_root=str(tmp_path))
        shutil.rmtree(handler.repos_dir)

        result = await handler.cleanup_old_repos(days=7)

        assert result["success"] is True
        assert result["cleaned"] == 0

    @pytest.mark.asyncio
    async def test_no_old_repos(self, handler, tmp_path):
        """When all repos are recent, none should be cleaned."""
        # Create a fresh repo directory
        repo_dir = tmp_path / "github-repos" / "recent_repo"
        repo_dir.mkdir(parents=True)

        result = await handler.cleanup_old_repos(days=7)

        assert result["success"] is True
        assert result["cleaned"] == 0
        assert repo_dir.exists()

    @pytest.mark.asyncio
    async def test_old_repos_cleaned(self, handler, tmp_path):
        """Repos older than the cutoff should be removed."""
        repos_dir = tmp_path / "github-repos"

        # Create an old repo directory
        old_repo = repos_dir / "old_repo"
        old_repo.mkdir(parents=True)

        # Set access time to 30 days ago
        old_time = time.time() - (30 * 24 * 3600)
        os.utime(str(old_repo), (old_time, old_time))

        result = await handler.cleanup_old_repos(days=7)

        assert result["success"] is True
        assert result["cleaned"] == 1
        assert "old_repo" in result["repositories"]
        assert not old_repo.exists()

    @pytest.mark.asyncio
    async def test_mixed_old_and_new_repos(self, handler, tmp_path):
        """Only old repos should be cleaned; recent ones should remain."""
        repos_dir = tmp_path / "github-repos"

        # Create an old repo
        old_repo = repos_dir / "old_repo"
        old_repo.mkdir(parents=True)
        old_time = time.time() - (30 * 24 * 3600)
        os.utime(str(old_repo), (old_time, old_time))

        # Create a recent repo
        new_repo = repos_dir / "new_repo"
        new_repo.mkdir(parents=True)

        result = await handler.cleanup_old_repos(days=7)

        assert result["success"] is True
        assert result["cleaned"] == 1
        assert "old_repo" in result["repositories"]
        assert not old_repo.exists()
        assert new_repo.exists()

    @pytest.mark.asyncio
    async def test_empty_repos_dir(self, handler, tmp_path):
        """An empty repos directory should result in 0 cleaned."""
        result = await handler.cleanup_old_repos(days=7)

        assert result["success"] is True
        assert result["cleaned"] == 0
        assert result["repositories"] == []

    @pytest.mark.asyncio
    async def test_cleanup_message_format(self, handler, tmp_path):
        """The result message should mention the number of days."""
        result = await handler.cleanup_old_repos(days=14)

        assert result["success"] is True
        assert "14 days" in result["message"]


# ---------------------------------------------------------------------------
# 10. get_repository_info()
# ---------------------------------------------------------------------------


class TestGetRepositoryInfo:
    """Tests for the get_repository_info async method."""

    @pytest.mark.asyncio
    async def test_successful_api_call(self, handler, mock_auth):
        """Successful GitHub API response should return structured repo info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "my-repo",
            "full_name": "owner/my-repo",
            "description": "A test repo",
            "private": False,
            "default_branch": "main",
            "language": "HCL",
            "size": 1024,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-06-01T00:00:00Z",
            "has_issues": True,
            "has_wiki": True,
            "archived": False,
            "topics": ["terraform", "infrastructure"],
            "clone_url": "https://github.com/owner/my-repo.git",
            "html_url": "https://github.com/owner/my-repo",
        }

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "my-repo")

        assert result["success"] is True
        assert result["name"] == "my-repo"
        assert result["full_name"] == "owner/my-repo"
        assert result["default_branch"] == "main"
        assert "terraform" in result["topics"]

    @pytest.mark.asyncio
    async def test_api_404_returns_error(self, handler, mock_auth):
        """A 404 response should return an error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "nonexistent")

        assert "error" in result
        assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_api_exception_returns_error(self, handler, mock_auth):
        """A network exception should return an error."""
        import requests as req

        with patch(
            "requests.get",
            side_effect=req.exceptions.RequestException("Connection refused"),
        ):
            result = await handler.get_repository_info("owner", "repo")

        assert "error" in result
        assert "Connection refused" in result["error"]

    @pytest.mark.asyncio
    async def test_uses_authenticated_headers(self, handler, mock_auth):
        """The API call should use authenticated headers from GitHubAppAuth."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "repo",
            "full_name": "owner/repo",
            "description": "",
            "private": True,
            "default_branch": "main",
            "language": "HCL",
            "size": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "has_issues": True,
            "has_wiki": False,
            "archived": False,
            "topics": [],
            "clone_url": "https://github.com/owner/repo.git",
            "html_url": "https://github.com/owner/repo",
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            await handler.get_repository_info("owner", "repo")

            call_kwargs = mock_get.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
            assert "Authorization" in headers
            assert "Bearer" in headers["Authorization"]


# ---------------------------------------------------------------------------
# 11. Security fix: workspace_name validation in prepare_terraform_workspace()
# ---------------------------------------------------------------------------


class TestPrepareWorkspaceNameValidation:
    """Tests for workspace_name format and path traversal validation."""

    @pytest.mark.asyncio
    async def test_workspace_name_path_traversal_blocked(
        self, handler_with_repo, mock_auth
    ):
        """workspace_name containing '..' must be rejected to prevent traversal."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# minimal")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "", workspace_name="../../evil"
            )

        assert "error" in result
        assert "workspace_name" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_workspace_name_slash_blocked(
        self, handler_with_repo, mock_auth
    ):
        """workspace_name containing '/' must be rejected."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# minimal")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "", workspace_name="valid/evil"
            )

        assert "error" in result
        assert "workspace_name" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_workspace_name_special_chars_blocked(
        self, handler_with_repo, mock_auth
    ):
        """workspace_name with shell-special characters must be rejected."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# minimal")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "", workspace_name="ws;rm -rf /"
            )

        assert "error" in result
        assert "workspace_name" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_workspace_name_valid_alphanumeric(
        self, handler_with_repo, mock_auth
    ):
        """workspace_name with alphanumeric, hyphens, and underscores must be accepted."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# minimal")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "", workspace_name="my-ws_01"
            )

        assert result.get("success") is True
        assert result["workspace_name"] == "my-ws_01"

    @pytest.mark.asyncio
    async def test_workspace_name_absolute_path_blocked(
        self, handler_with_repo, mock_auth
    ):
        """workspace_name that resolves outside workspace_root must be rejected."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# minimal")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            result = await handler.prepare_terraform_workspace(
                "test-owner", "test-repo", "", workspace_name="../escape"
            )

        assert "error" in result
        assert "workspace_name" in result["error"].lower()


# ---------------------------------------------------------------------------
# 12. Security fix: pattern allowlist in list_terraform_files()
# ---------------------------------------------------------------------------


class TestListTerraformFilesPatternAllowlist:
    """Tests for pattern allowlist validation in list_terraform_files."""

    @pytest.mark.asyncio
    async def test_disallowed_pattern_rejected(self, handler_with_repo):
        """An arbitrary glob pattern outside the allowlist must be rejected."""
        handler, repo_dir = handler_with_repo

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*.py"
        )

        assert "error" in result
        assert "Invalid pattern" in result["error"]

    @pytest.mark.asyncio
    async def test_malicious_pattern_rejected(self, handler_with_repo):
        """A pattern with path traversal characters must be rejected."""
        handler, repo_dir = handler_with_repo

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="../../*"
        )

        assert "error" in result
        assert "Invalid pattern" in result["error"]

    @pytest.mark.asyncio
    async def test_shell_injection_pattern_rejected(self, handler_with_repo):
        """A pattern with shell metacharacters must be rejected."""
        handler, repo_dir = handler_with_repo

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*;rm -rf /"
        )

        assert "error" in result
        assert "Invalid pattern" in result["error"]

    @pytest.mark.asyncio
    async def test_tf_pattern_allowed(self, handler_with_repo):
        """The default '*.tf' pattern must be accepted."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# tf")

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*.tf"
        )

        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_tfvars_pattern_allowed(self, handler_with_repo):
        """The '*.tfvars' pattern must be accepted."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "prod.tfvars").write_text('region = "us-east-1"')

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*.tfvars"
        )

        assert result.get("success") is True
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_hcl_pattern_allowed(self, handler_with_repo):
        """The '*.hcl' pattern must be accepted."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "config.hcl").write_text("# hcl")

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*.hcl"
        )

        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_json_pattern_allowed(self, handler_with_repo):
        """The '*.json' pattern must be accepted."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "config.json").write_text("{}")

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*.json"
        )

        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_tfvars_json_pattern_allowed(self, handler_with_repo):
        """The '*.tfvars.json' pattern must be accepted."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "prod.tfvars.json").write_text("{}")

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*.tfvars.json"
        )

        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_error_message_lists_allowed_patterns(self, handler_with_repo):
        """Error message for invalid pattern must list the allowed patterns."""
        handler, repo_dir = handler_with_repo

        result = await handler.list_terraform_files(
            "test-owner", "test-repo", pattern="*.sh"
        )

        assert "error" in result
        # Error should mention allowed patterns so callers know what to use
        assert "*.tf" in result["error"] or "Allowed" in result["error"]


# ---------------------------------------------------------------------------
# Fix 3: get_terraform_config file read error handling
# ---------------------------------------------------------------------------


class TestGetTerraformConfigFileReadErrors:
    """Tests that unreadable or invalid-encoding .tf files are skipped gracefully."""

    @pytest.mark.asyncio
    async def test_oserror_on_read_skips_file(self, handler_with_repo):
        """An OSError reading a .tf file should be logged and skipped, not crash."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "good.tf").write_text('variable "region" {}')
        (repo_dir / "bad.tf").write_text("# will be mocked as unreadable")

        def _mock_read_text(self_path, encoding="utf-8"):
            if self_path.name == "bad.tf":
                raise OSError("permission denied")
            return self_path.read_bytes().decode(encoding)

        with patch.object(Path, "read_text", _mock_read_text):
            result = await handler.get_terraform_config("test-owner", "test-repo", "")

        # Should succeed and include the good file
        assert result.get("success") is True
        assert "good.tf" in result["terraform_files"]
        # bad.tf is listed as a file (from glob) but read is skipped
        # The key invariant: no crash, good file still analysed
        assert result["has_variables"] is True

    @pytest.mark.asyncio
    async def test_unicode_decode_error_skips_file(self, handler_with_repo):
        """A UnicodeDecodeError reading a .tf file should be logged and skipped."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "good.tf").write_text('output "id" { value = 1 }')
        # Write a binary file with a .tf extension to trigger decode error
        bad_tf = repo_dir / "binary.tf"
        bad_tf.write_bytes(b"\xff\xfe\x00invalid\x80binary")

        result = await handler.get_terraform_config("test-owner", "test-repo", "")

        # Should succeed without crashing
        assert result.get("success") is True
        assert "good.tf" in result["terraform_files"]
        assert result["has_outputs"] is True


# ---------------------------------------------------------------------------
# Fix 4: prepare_terraform_workspace shutil error handling
# ---------------------------------------------------------------------------


class TestPrepareWorkspaceShutilErrors:
    """Tests that OSErrors from shutil.rmtree / shutil.copytree are handled."""

    @pytest.mark.asyncio
    async def test_rmtree_oserror_returns_error(self, handler_with_repo, mock_auth, tmp_path):
        """An OSError from shutil.rmtree should return an error dict, not crash."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# main")

        # Pre-create the workspace so rmtree is triggered
        workspace_dir = tmp_path / "terraform-workspaces" / "target-ws"
        workspace_dir.mkdir(parents=True)

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            with patch("shutil.rmtree", side_effect=OSError("rmtree failed")):
                result = await handler.prepare_terraform_workspace(
                    "test-owner", "test-repo", "", workspace_name="target-ws"
                )

        assert "error" in result
        assert "rmtree failed" in result["error"] or "workspace" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_copytree_oserror_returns_error(self, handler_with_repo, mock_auth):
        """An OSError from shutil.copytree should return an error dict, not crash."""
        handler, repo_dir = handler_with_repo
        (repo_dir / "main.tf").write_text("# main")

        with patch.object(
            handler, "clone_or_update_repo", new_callable=AsyncMock
        ) as mock_clone:
            mock_clone.return_value = {"success": True}

            with patch("shutil.copytree", side_effect=OSError("disk full")):
                result = await handler.prepare_terraform_workspace(
                    "test-owner", "test-repo", "", workspace_name="fresh-ws"
                )

        assert "error" in result
        assert "disk full" in result["error"] or "workspace" in result["error"].lower()


# ---------------------------------------------------------------------------
# Fix 5 & 6: get_repository_info optional field safety and specific exceptions
# ---------------------------------------------------------------------------


class TestGetRepositoryInfoFieldSafety:
    """Tests that optional fields use .get() and required fields are validated."""

    @pytest.mark.asyncio
    async def test_missing_description_defaults_to_empty(self, handler, mock_auth):
        """Missing 'description' in API response should default to empty string."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "repo",
            "full_name": "owner/repo",
            # description intentionally absent
            "private": False,
            "default_branch": "main",
            "language": "HCL",
            "size": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "has_issues": True,
            "has_wiki": False,
            "archived": False,
            "topics": [],
            "clone_url": "https://github.com/owner/repo.git",
            "html_url": "https://github.com/owner/repo",
        }

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "repo")

        assert result.get("success") is True
        assert result["description"] == ""

    @pytest.mark.asyncio
    async def test_missing_language_defaults_to_unknown(self, handler, mock_auth):
        """Missing 'language' in API response should default to 'Unknown'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "repo",
            "full_name": "owner/repo",
            "description": "A repo",
            "private": False,
            "default_branch": "main",
            # language intentionally absent
            "size": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "has_issues": True,
            "has_wiki": False,
            "archived": False,
            "topics": [],
            "clone_url": "https://github.com/owner/repo.git",
            "html_url": "https://github.com/owner/repo",
        }

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "repo")

        assert result.get("success") is True
        assert result["language"] == "Unknown"

    @pytest.mark.asyncio
    async def test_missing_topics_defaults_to_empty_list(self, handler, mock_auth):
        """Missing 'topics' in API response should default to []."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "repo",
            "full_name": "owner/repo",
            "description": "",
            "private": False,
            "default_branch": "main",
            "language": "HCL",
            "size": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "has_issues": True,
            "has_wiki": False,
            "archived": False,
            # topics intentionally absent
            "clone_url": "https://github.com/owner/repo.git",
            "html_url": "https://github.com/owner/repo",
        }

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "repo")

        assert result.get("success") is True
        assert result["topics"] == []

    @pytest.mark.asyncio
    async def test_missing_required_field_returns_error(self, handler, mock_auth):
        """Missing required field 'name' in API response should return an error, not KeyError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # 'name' intentionally missing — required field
            "full_name": "owner/repo",
            "private": False,
            "default_branch": "main",
            "size": 100,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "has_issues": True,
            "has_wiki": False,
            "archived": False,
            "clone_url": "https://github.com/owner/repo.git",
            "html_url": "https://github.com/owner/repo",
        }

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "repo")

        assert "error" in result


class TestGetRepositoryInfoSpecificExceptions:
    """Tests that get_repository_info handles specific exception types."""

    @pytest.mark.asyncio
    async def test_http_error_returns_error(self, handler, mock_auth):
        """requests.exceptions.HTTPError should return error dict."""
        import requests as req

        with patch(
            "requests.get",
            side_effect=req.exceptions.HTTPError("403 Forbidden"),
        ):
            result = await handler.get_repository_info("owner", "repo")

        assert "error" in result
        assert "403 Forbidden" in result["error"] or "Failed" in result["error"]

    @pytest.mark.asyncio
    async def test_request_exception_returns_error(self, handler, mock_auth):
        """requests.exceptions.RequestException should return error dict."""
        import requests as req

        with patch(
            "requests.get",
            side_effect=req.exceptions.RequestException("connection reset"),
        ):
            result = await handler.get_repository_info("owner", "repo")

        assert "error" in result
        assert "connection reset" in result["error"] or "Failed" in result["error"]

    @pytest.mark.asyncio
    async def test_json_decode_error_returns_error(self, handler, mock_auth):
        """json.JSONDecodeError from response.json() should return error dict."""
        import json

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("bad json", "", 0)

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "repo")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_key_error_returns_error(self, handler, mock_auth):
        """KeyError from missing required field should return error dict, not propagate."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Return empty dict — all field accesses will raise KeyError
        mock_response.json.return_value = {}

        with patch("requests.get", return_value=mock_response):
            result = await handler.get_repository_info("owner", "repo")

        assert "error" in result


# ---------------------------------------------------------------------------
# _sanitize_workspace_name() — exhaustive tests (RED phase first)
# ---------------------------------------------------------------------------


class TestSanitizeWorkspaceName:
    """Exhaustive tests for the _sanitize_workspace_name static method.

    Covers every category from the task specification plus boundary cases.
    All tests operate on the static method directly.
    """

    # ------------------------------------------------------------------
    # Simple / already-valid inputs
    # ------------------------------------------------------------------

    def test_simple_main_tf(self):
        """A plain filename with an extension produces a valid name with dot replaced."""
        result = GitHubRepoHandler._sanitize_workspace_name("main.tf")
        assert result == "main_tf"

    def test_already_valid_simple(self):
        """An already-valid name passes through unchanged."""
        result = GitHubRepoHandler._sanitize_workspace_name("simple_name")
        assert result == "simple_name"

    def test_numbers_preserved(self):
        """Purely alphanumeric names are returned unchanged."""
        result = GitHubRepoHandler._sanitize_workspace_name("project123")
        assert result == "project123"

    def test_single_char(self):
        """A single valid character is returned as-is."""
        result = GitHubRepoHandler._sanitize_workspace_name("a")
        assert result == "a"

    def test_hyphens_preserved(self):
        """Hyphens are valid and must be preserved."""
        result = GitHubRepoHandler._sanitize_workspace_name("my-project")
        assert result == "my-project"

    def test_underscores_preserved(self):
        """Underscores in an already-clean name are preserved."""
        result = GitHubRepoHandler._sanitize_workspace_name("my_project")
        assert result == "my_project"

    # ------------------------------------------------------------------
    # Dot / slash handling (typical path inputs)
    # ------------------------------------------------------------------

    def test_path_dots_become_underscores(self):
        """Dots in paths are replaced with underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("modules/vpc/main.tf")
        assert result == "modules_vpc_main_tf"

    def test_spaces_become_underscores(self):
        """Spaces are replaced with underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("my project/main.tf")
        assert result == "my_project_main_tf"

    def test_mixed_valid_invalid(self):
        """Mixed valid/invalid chars: hyphens preserved, dots/slashes become underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("my-project_v2.0/modules")
        assert result == "my-project_v2_0_modules"

    # ------------------------------------------------------------------
    # Unicode
    # ------------------------------------------------------------------

    def test_unicode_chars_become_underscores(self):
        """Unicode characters outside ASCII set are replaced with underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("módulo/main.tf")
        assert result == "m_dulo_main_tf"

    # ------------------------------------------------------------------
    # Security / traversal inputs
    # ------------------------------------------------------------------

    def test_double_dots_path_traversal(self):
        """Path traversal '../../etc/passwd' becomes safe underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("../../etc/passwd")
        assert result == "etc_passwd"

    # ------------------------------------------------------------------
    # Collapsing consecutive special chars
    # ------------------------------------------------------------------

    def test_consecutive_dots_collapsed(self):
        """Multiple consecutive dots collapse to a single underscore."""
        result = GitHubRepoHandler._sanitize_workspace_name("a...b///c")
        assert result == "a_b_c"

    def test_consecutive_special_chars(self):
        """Multiple mixed special chars in a row collapse to one underscore."""
        result = GitHubRepoHandler._sanitize_workspace_name("a@#$b")
        assert result == "a_b"

    # ------------------------------------------------------------------
    # Fallback for empty / whitespace / all-special-char inputs
    # ------------------------------------------------------------------

    def test_empty_string_fallback(self):
        """Empty string falls back to 'workspace'."""
        result = GitHubRepoHandler._sanitize_workspace_name("")
        assert result == "workspace"

    def test_all_special_chars_fallback(self):
        """String of only special chars falls back to 'workspace'."""
        result = GitHubRepoHandler._sanitize_workspace_name("@#$%^&*()")
        assert result == "workspace"

    def test_underscore_only_fallback(self):
        """String of only underscores strips to empty, falls back to 'workspace'."""
        result = GitHubRepoHandler._sanitize_workspace_name("___")
        assert result == "workspace"

    def test_dots_only_fallback(self):
        """String of only dots becomes all underscores then strips to 'workspace'."""
        result = GitHubRepoHandler._sanitize_workspace_name("...")
        assert result == "workspace"

    # ------------------------------------------------------------------
    # Stripping leading/trailing invalid chars
    # ------------------------------------------------------------------

    def test_leading_trailing_dots_stripped(self):
        """Leading and trailing dots are removed after conversion."""
        result = GitHubRepoHandler._sanitize_workspace_name(".hidden.dir.")
        assert result == "hidden_dir"

    def test_leading_trailing_slashes_stripped(self):
        """Leading and trailing slashes are removed."""
        result = GitHubRepoHandler._sanitize_workspace_name("/path/to/config/")
        assert result == "path_to_config"

    # ------------------------------------------------------------------
    # Backslash / Windows paths
    # ------------------------------------------------------------------

    def test_backslashes_become_underscores(self):
        """Windows-style backslashes are replaced with underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("modules\\vpc")
        assert result == "modules_vpc"

    # ------------------------------------------------------------------
    # Whitespace variants
    # ------------------------------------------------------------------

    def test_tab_char_becomes_underscore(self):
        """Tab characters are replaced with underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("mod\tvpc")
        assert result == "mod_vpc"

    def test_newline_char_becomes_underscore(self):
        """Newline characters are replaced with underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("mod\nvpc")
        assert result == "mod_vpc"

    # ------------------------------------------------------------------
    # Null bytes
    # ------------------------------------------------------------------

    def test_null_byte_becomes_underscore(self):
        """Null bytes are replaced with underscores."""
        result = GitHubRepoHandler._sanitize_workspace_name("mod\x00vpc")
        assert result == "mod_vpc"

    # ------------------------------------------------------------------
    # Length truncation
    # ------------------------------------------------------------------

    def test_long_name_truncated_to_128(self):
        """Names longer than 128 chars are truncated."""
        long_name = "a" * 200
        result = GitHubRepoHandler._sanitize_workspace_name(long_name)
        assert len(result) == 128
        assert result == "a" * 128

    def test_exact_128_char_boundary(self):
        """A name of exactly 128 chars is not truncated."""
        name = "a" * 128
        result = GitHubRepoHandler._sanitize_workspace_name(name)
        assert result == name
        assert len(result) == 128

    def test_129_chars_truncated(self):
        """A name of 129 chars is truncated to 128."""
        name = "b" * 129
        result = GitHubRepoHandler._sanitize_workspace_name(name)
        assert len(result) == 128

    def test_truncation_after_sanitize_not_before(self):
        """Truncation is applied to the sanitized string, not the raw input.

        200-char raw string with embedded dots -- after sanitization collapses
        to fewer underscores. Result must still be <= 128.
        """
        raw = ("ab." * 50)[:200]  # 200-char raw with dots
        result = GitHubRepoHandler._sanitize_workspace_name(raw)
        assert len(result) <= 128


# ---------------------------------------------------------------------------
# prepare_terraform_workspace: auto-generated name uses _sanitize_workspace_name
# ---------------------------------------------------------------------------


class TestPrepareWorkspaceAutoGeneratedName:
    """Tests that prepare_terraform_workspace uses _sanitize_workspace_name
    for auto-generated workspace names (when workspace_name=None).

    Constraint: user-supplied names still go through the strict regex check.
    """

    @pytest.mark.asyncio
    async def test_auto_name_with_dotted_config_path(self, handler, tmp_path):
        """Config path with dots produces a valid sanitized workspace name."""
        repo_dir = tmp_path / "github-repos" / "owner_repo"
        config_src = repo_dir / "modules" / "vpc"
        config_src.mkdir(parents=True)
        (config_src / "main.tf").write_text('resource "aws_vpc" "main" {}')

        with patch.object(
            handler,
            "clone_or_update_repo",
            new_callable=AsyncMock,
            return_value={"success": True, "action": "cloned"},
        ):
            result = await handler.prepare_terraform_workspace(
                owner="owner",
                repo="repo",
                config_path="modules/vpc",
                workspace_name=None,
            )

        assert result.get("success") is True
        ws_name = result["workspace_name"]
        import re
        assert re.match(r'^[a-zA-Z0-9_\-]+$', ws_name), (
            f"Auto-generated name {ws_name!r} contains invalid characters"
        )

    @pytest.mark.asyncio
    async def test_user_supplied_valid_name_accepted(self, handler, tmp_path):
        """A valid user-supplied workspace name bypasses sanitization."""
        repo_dir = tmp_path / "github-repos" / "owner_repo"
        config_src = repo_dir / "infra"
        config_src.mkdir(parents=True)
        (config_src / "main.tf").write_text('resource "aws_s3_bucket" "b" {}')

        with patch.object(
            handler,
            "clone_or_update_repo",
            new_callable=AsyncMock,
            return_value={"success": True, "action": "cloned"},
        ):
            result = await handler.prepare_terraform_workspace(
                owner="owner",
                repo="repo",
                config_path="infra",
                workspace_name="my_custom_workspace",
            )

        assert result.get("success") is True
        assert result["workspace_name"] == "my_custom_workspace"

    @pytest.mark.asyncio
    async def test_user_supplied_invalid_name_rejected(self, handler, tmp_path):
        """A user-supplied name with dots is rejected by strict regex."""
        repo_dir = tmp_path / "github-repos" / "owner_repo"
        config_src = repo_dir / "infra"
        config_src.mkdir(parents=True)
        (config_src / "main.tf").write_text("")

        with patch.object(
            handler,
            "clone_or_update_repo",
            new_callable=AsyncMock,
            return_value={"success": True, "action": "cloned"},
        ):
            result = await handler.prepare_terraform_workspace(
                owner="owner",
                repo="repo",
                config_path="infra",
                workspace_name="bad.name.with.dots",
            )

        assert "error" in result
        assert "Invalid workspace_name" in result["error"]
