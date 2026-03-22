#!/usr/bin/env python3
"""
GitHub Repository Handler
Manages cloning, updating, and accessing GitHub repositories for Terraform configurations.

Security hardened:
- Path validation to prevent traversal attacks
- Safe subprocess execution
- Repository isolation in workspace
"""

import asyncio
import logging
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from github_app_auth import GitHubAppAuth

logger = logging.getLogger(__name__)


class GitHubRepoHandler:
    """Handles GitHub repository operations for Terraform configurations"""

    def __init__(self, auth: GitHubAppAuth, workspace_root: str = "/mnt/workspace"):
        self.auth = auth
        self.workspace_root = Path(workspace_root)
        self.repos_dir = self.workspace_root / "github-repos"
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def _get_repo_path(self, owner: str, repo: str) -> Path:
        """Get the local path for a repository"""
        # Security: Validate owner and repo names
        if not owner.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid repository owner name: {owner}")
        if not repo.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError(f"Invalid repository name: {repo}")

        return self.repos_dir / f"{owner}_{repo}"

    @staticmethod
    def _sanitize_workspace_name(raw: str) -> str:
        """Sanitize a string for use as a workspace name.

        Replaces dots, slashes, spaces, and other special chars with underscores.
        Collapses multiple consecutive underscores into one.
        Strips leading and trailing underscores.
        Truncates to 128 chars.
        Falls back to 'workspace' if the result is empty.
        """
        sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('_')
        sanitized = sanitized[:128]
        return sanitized or "workspace"

    def _sanitize_output(self, text: str) -> str:
        """Remove tokens and credentials from git command output"""
        return re.sub(r'https://[^@]+@', 'https://***@', text)

    async def _run_git_command(self, cmd: list[str], cwd: Path) -> dict[str, Any]:
        """Run a git command asynchronously with security hardening"""
        try:
            # Security: Use shell=False and command list
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={
                    "HOME": os.environ.get("HOME", "/tmp"),
                    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "GIT_TERMINAL_PROMPT": "0",
                },  # Minimal env — disable git prompts, prevent credential leaks
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=120
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.error("Git command timed out after 120 seconds")
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "Git command timed out after 120 seconds",
                    "returncode": -1,
                }

            return {
                "success": process.returncode == 0,
                "stdout": self._sanitize_output(stdout.decode("utf-8", errors="replace")),
                "stderr": self._sanitize_output(stderr.decode("utf-8", errors="replace")),
                "returncode": process.returncode,
            }

        except Exception as e:
            sanitized_error = self._sanitize_output(str(e))
            logger.error(f"Git command failed: {sanitized_error}")
            return {"success": False, "stdout": "", "stderr": sanitized_error, "returncode": -1}

    def _validate_branch_name(self, branch: str) -> bool:
        """Validate branch name to prevent git flag injection"""
        if branch.startswith("-"):
            return False
        if not re.match(r'^[a-zA-Z0-9_./-]+$', branch):
            return False
        if ".." in branch:
            return False
        return True

    async def clone_or_update_repo(
        self, owner: str, repo: str, branch: str | None = None, force: bool = False
    ) -> dict[str, Any]:
        """Clone a repository or update it if it already exists"""
        if branch and not self._validate_branch_name(branch):
            return {"error": f"Invalid branch name: {branch}"}

        repo_path = self._get_repo_path(owner, repo)

        # Construct clone URL with authentication token
        token = self.auth.get_installation_token()
        clone_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"

        if repo_path.exists() and not force:
            # Repository exists, update it
            logger.info(f"Updating existing repository: {owner}/{repo}")

            # Fetch latest changes
            result = await self._run_git_command(
                ["git", "fetch", "--all", "--prune"], repo_path
            )

            if not result["success"]:
                return {
                    "error": f"Failed to fetch updates: {result['stderr']}",
                    "path": str(repo_path),
                }

            # Checkout branch if specified
            if branch:
                result = await self._run_git_command(
                    ["git", "checkout", branch], repo_path
                )

                if not result["success"]:
                    # Try to checkout as new branch tracking remote
                    result = await self._run_git_command(
                        ["git", "checkout", "-b", branch, f"origin/{branch}"], repo_path
                    )

                if result["success"]:
                    # Pull latest changes
                    await self._run_git_command(["git", "pull", "--ff-only"], repo_path)

            return {
                "success": True,
                "action": "updated",
                "path": str(repo_path),
                "branch": branch or "default",
            }

        else:
            # Clone new repository
            if repo_path.exists() and force:
                logger.info(f"Force removing existing repository: {owner}/{repo}")
                shutil.rmtree(repo_path)

            logger.info(f"Cloning repository: {owner}/{repo}")

            cmd = ["git", "clone"]
            if branch:
                cmd.extend(["-b", branch])
            cmd.extend([clone_url, str(repo_path)])

            result = await self._run_git_command(cmd, self.repos_dir)

            if not result["success"]:
                return {
                    "error": f"Failed to clone repository: {result['stderr']}",
                    "clone_url_sanitized": f"https://github.com/{owner}/{repo}.git",
                }

            return {
                "success": True,
                "action": "cloned",
                "path": str(repo_path),
                "branch": branch or "default",
            }

    ALLOWED_FILE_PATTERNS = {"*.tf", "*.tfvars", "*.hcl", "*.json", "*.tfvars.json"}

    async def list_terraform_files(
        self, owner: str, repo: str, path: str = "", pattern: str = "*.tf"
    ) -> dict[str, Any]:
        """List Terraform files in a repository"""
        if pattern not in self.ALLOWED_FILE_PATTERNS:
            return {
                "error": (
                    f"Invalid pattern. Allowed: "
                    f"{', '.join(sorted(self.ALLOWED_FILE_PATTERNS))}"
                )
            }

        repo_path = self._get_repo_path(owner, repo)

        if not repo_path.exists():
            return {
                "error": "Repository not found locally. Clone it first with github_clone_repo"
            }

        search_path = repo_path / path if path else repo_path

        # Validate path stays within repo directory
        if not search_path.resolve().is_relative_to(repo_path.resolve()):
            return {"error": "Invalid path: traversal outside repository is not allowed"}

        if not search_path.exists():
            return {"error": f"Path not found in repository: {path}"}

        # Find all matching files
        tf_files = []
        for file_path in search_path.rglob(pattern):
            if file_path.is_file():
                relative_path = file_path.relative_to(repo_path)
                tf_files.append(
                    {
                        "path": str(relative_path),
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat(),
                    }
                )

        return {
            "success": True,
            "repository": f"{owner}/{repo}",
            "search_path": path or "/",
            "pattern": pattern,
            "files": sorted(tf_files, key=lambda x: x["path"]),
            "count": len(tf_files),
        }

    async def get_terraform_config(
        self, owner: str, repo: str, config_path: str
    ) -> dict[str, Any]:
        """Get information about a Terraform configuration in a repository"""
        repo_path = self._get_repo_path(owner, repo)

        if not repo_path.exists():
            return {
                "error": "Repository not found locally. Clone it first with github_clone_repo"
            }

        config_dir = repo_path / config_path if config_path else repo_path

        # Validate path stays within repo directory
        if not config_dir.resolve().is_relative_to(repo_path.resolve()):
            return {"error": "Invalid path: traversal outside repository is not allowed"}

        if not config_dir.exists():
            return {"error": f"Configuration path not found: {config_path}"}

        # Analyze the Terraform configuration
        info = {
            "repository": f"{owner}/{repo}",
            "config_path": config_path or "/",
            "terraform_files": [],
            "has_backend": False,
            "has_variables": False,
            "has_outputs": False,
            "modules": [],
            "providers": [],
        }

        # List all .tf files
        for tf_file in config_dir.glob("*.tf"):
            if tf_file.is_file():
                info["terraform_files"].append(tf_file.name)

                # Quick content analysis
                try:
                    content = tf_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as e:
                    logger.warning(f"Cannot read {tf_file}: {e}")
                    continue
                if "backend " in content:
                    info["has_backend"] = True
                if "variable " in content:
                    info["has_variables"] = True
                if "output " in content:
                    info["has_outputs"] = True
                if "provider " in content and tf_file.name not in info["providers"]:
                    # Extract provider names (simple regex would be better but keeping it simple)
                    for line in content.split("\n"):
                        if 'provider "' in line:
                            provider = line.split('"')[1]
                            if provider not in info["providers"]:
                                info["providers"].append(provider)

        # Check for modules
        modules_dir = config_dir / "modules"
        if modules_dir.exists():
            info["modules"] = [d.name for d in modules_dir.iterdir() if d.is_dir()]

        # Check for common files
        for file_name in ["terraform.tfvars", ".terraform.lock.hcl", "README.md"]:
            if (config_dir / file_name).exists():
                info[f'has_{file_name.replace(".", "_")}'] = True

        return {"success": True, **info}

    async def prepare_terraform_workspace(
        self,
        owner: str,
        repo: str,
        config_path: str,
        workspace_name: str | None = None,
    ) -> dict[str, Any]:
        """Prepare a Terraform workspace from a GitHub repository"""
        # First ensure the repository is cloned/updated
        clone_result = await self.clone_or_update_repo(owner, repo)

        if "error" in clone_result:
            return clone_result

        repo_path = self._get_repo_path(owner, repo)
        source_path = repo_path / config_path if config_path else repo_path

        # Validate path stays within repo directory
        if not source_path.resolve().is_relative_to(repo_path.resolve()):
            return {"error": "Invalid path: traversal outside repository is not allowed"}

        if not source_path.exists():
            return {"error": f"Configuration path not found: {config_path}"}

        # Create workspace directory
        if not workspace_name:
            raw_name = f"{owner}_{repo}_{config_path.replace('/', '_')}"
            workspace_name = self._sanitize_workspace_name(raw_name)

        # Security: validate workspace_name format before constructing the path
        if not re.match(r'^[a-zA-Z0-9_\-]+$', workspace_name):
            return {"error": f"Invalid workspace_name: {workspace_name!r}. "
                             f"Only alphanumeric characters, hyphens, and underscores are allowed."}

        workspace_path = self.workspace_root / "terraform-workspaces" / workspace_name

        # Security: validate resolved path stays within workspace_root
        if not workspace_path.resolve().is_relative_to(self.workspace_root.resolve()):
            return {"error": f"Invalid workspace_name: {workspace_name!r}. "
                             f"Path traversal outside workspace root is not allowed."}

        # Copy configuration to workspace
        try:
            if workspace_path.exists():
                shutil.rmtree(workspace_path)

            shutil.copytree(source_path, workspace_path)
        except OSError as e:
            logger.error(f"Failed to prepare workspace {workspace_path}: {e}")
            return {"error": f"Failed to prepare workspace: {e}"}

        return {
            "success": True,
            "workspace_path": str(workspace_path),
            "workspace_name": workspace_name,
            "source": {
                "repository": f"{owner}/{repo}",
                "config_path": config_path or "/",
                "last_updated": datetime.now().isoformat(),
            },
        }

    async def get_repository_info(self, owner: str, repo: str) -> dict[str, Any]:
        """Get information about a GitHub repository"""
        import json

        import requests

        headers = self.auth.get_authenticated_headers()
        url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(
                    f"Failed to get repository info: {response.status_code} - {response.text}"
                )
                return {
                    "error": f"Failed to get repository info: HTTP {response.status_code}"
                }

            repo_data = response.json()

            # Validate required fields are present before accessing them
            required_fields = (
                "name",
                "full_name",
                "private",
                "default_branch",
                "size",
                "created_at",
                "updated_at",
                "has_issues",
                "has_wiki",
                "archived",
                "clone_url",
                "html_url",
            )
            missing = [f for f in required_fields if f not in repo_data]
            if missing:
                logger.error(f"GitHub API response missing required fields: {missing}")
                return {
                    "error": (
                        f"Failed to get repository info: "
                        f"API response missing fields: {missing}"
                    )
                }

            # Extract relevant information; use .get() for all optional fields
            return {
                "success": True,
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "description": repo_data.get("description", ""),
                "private": repo_data["private"],
                "default_branch": repo_data["default_branch"],
                "language": repo_data.get("language", "Unknown"),
                "size": repo_data["size"],
                "created_at": repo_data["created_at"],
                "updated_at": repo_data["updated_at"],
                "has_issues": repo_data["has_issues"],
                "has_wiki": repo_data["has_wiki"],
                "archived": repo_data["archived"],
                "topics": repo_data.get("topics", []),
                "clone_url": repo_data["clone_url"],
                "html_url": repo_data["html_url"],
            }

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error getting repository info: {e}")
            return {"error": f"Failed to get repository info: {e}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting repository info: {e}")
            return {"error": f"Failed to get repository info: {e}"}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in repository info response: {e}")
            return {"error": "Failed to get repository info: invalid JSON response"}
        except KeyError as e:
            logger.error(f"Unexpected missing key in repository info response: {e}")
            return {"error": f"Failed to get repository info: missing field {e}"}

    async def cleanup_old_repos(self, days: int = 7) -> dict[str, Any]:
        """Clean up repositories that haven't been accessed in specified days"""
        if not self.repos_dir.exists():
            return {
                "success": True,
                "cleaned": 0,
                "message": "No repositories directory found",
            }

        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned = []

        for repo_dir in self.repos_dir.iterdir():
            if repo_dir.is_dir():
                # Check last access time
                stat = repo_dir.stat()
                last_access = datetime.fromtimestamp(stat.st_atime)

                if last_access < cutoff_time:
                    logger.info(f"Removing old repository: {repo_dir.name}")
                    shutil.rmtree(repo_dir)
                    cleaned.append(repo_dir.name)

        return {
            "success": True,
            "cleaned": len(cleaned),
            "repositories": cleaned,
            "message": f"Cleaned {len(cleaned)} repositories older than {days} days",
        }
