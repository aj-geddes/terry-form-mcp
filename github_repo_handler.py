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
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

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

    async def _run_git_command(self, cmd: List[str], cwd: Path) -> Dict[str, Any]:
        """Run a git command asynchronously with security hardening"""
        try:
            # Security: Use shell=False and command list
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},  # Disable git prompts
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": process.returncode,
            }

        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

    async def clone_or_update_repo(
        self, owner: str, repo: str, branch: Optional[str] = None, force: bool = False
    ) -> Dict[str, Any]:
        """Clone a repository or update it if it already exists"""
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

    async def list_terraform_files(
        self, owner: str, repo: str, path: str = "", pattern: str = "*.tf"
    ) -> Dict[str, Any]:
        """List Terraform files in a repository"""
        repo_path = self._get_repo_path(owner, repo)

        if not repo_path.exists():
            return {
                "error": "Repository not found locally. Clone it first with github_clone_repo"
            }

        search_path = repo_path / path if path else repo_path

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
    ) -> Dict[str, Any]:
        """Get information about a Terraform configuration in a repository"""
        repo_path = self._get_repo_path(owner, repo)

        if not repo_path.exists():
            return {
                "error": "Repository not found locally. Clone it first with github_clone_repo"
            }

        config_dir = repo_path / config_path if config_path else repo_path

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
                content = tf_file.read_text()
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
        workspace_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Prepare a Terraform workspace from a GitHub repository"""
        # First ensure the repository is cloned/updated
        clone_result = await self.clone_or_update_repo(owner, repo)

        if "error" in clone_result:
            return clone_result

        repo_path = self._get_repo_path(owner, repo)
        source_path = repo_path / config_path if config_path else repo_path

        if not source_path.exists():
            return {"error": f"Configuration path not found: {config_path}"}

        # Create workspace directory
        workspace_name = (
            workspace_name or f"{owner}_{repo}_{config_path.replace('/', '_')}"
        )
        workspace_path = self.workspace_root / "terraform-workspaces" / workspace_name

        # Copy configuration to workspace
        if workspace_path.exists():
            shutil.rmtree(workspace_path)

        shutil.copytree(source_path, workspace_path)

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

    async def get_repository_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get information about a GitHub repository"""
        import requests

        headers = self.auth.get_authenticated_headers()
        url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                return {
                    "error": f"Failed to get repository info: {response.status_code} - {response.text}"
                }

            repo_data = response.json()

            # Extract relevant information
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

        except Exception as e:
            return {"error": f"Failed to get repository info: {str(e)}"}

    async def cleanup_old_repos(self, days: int = 7) -> Dict[str, Any]:
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
