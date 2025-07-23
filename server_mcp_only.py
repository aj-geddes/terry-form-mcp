#!/usr/bin/env python3
"""
Terry-Form MCP Server - MCP Protocol Only
This server handles only the MCP protocol without any HTTP endpoints.
For use in multi-process deployments where MCP and HTTP are separated.

Security hardened according to Orca findings:
- All subprocess calls use shell=False
- Input validation and sanitization
- Path traversal protection
- JSON schema validation
"""

import os
import sys
import logging
import asyncio
from typing import Optional
from pathlib import Path

from fastmcp import FastMCP

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import existing modules
from internal.terraform.executor import TerraformExecutor
from internal.cloud.terraform_cloud_client import TerraformCloudClient
from internal.analytics.MODULE_INTELLIGENCE import ModuleIntelligence
from github_app_auth import GitHubAppAuth
from github_repo_handler import GitHubRepoHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP(
    name="terry-form-mcp",
    version="3.0.0"
)

# Security: Define allowed actions
ALLOWED_TERRAFORM_ACTIONS = {"init", "validate", "fmt", "plan"}
BLOCKED_ACTIONS = {"apply", "destroy", "import", "taint", "untaint"}

# Initialize components with security hardening
terraform_executor = TerraformExecutor()

# Security: Path validation helper
def validate_and_normalize_path(path: str, workspace_root: str = "/mnt/workspace") -> Optional[str]:
    """
    Validate and normalize path to prevent traversal attacks.
    Returns normalized path if valid, None if invalid.
    """
    try:
        # Handle special prefixes
        if path.startswith('github://') or path.startswith('workspace://'):
            return path  # These are handled by specific handlers

        # Convert to Path object
        workspace_base = Path(workspace_root)

        # If absolute path provided, ensure it's within workspace
        if path.startswith('/'):
            target_path = Path(path)
        else:
            target_path = workspace_base / path

        # Resolve to real path (follows symlinks, removes ../ etc)
        real_path = target_path.resolve()

        # Ensure path is within workspace
        try:
            real_path.relative_to(workspace_base.resolve())
            return str(real_path)
        except ValueError:
            logger.warning(f"Path traversal attempt blocked: {path} -> {real_path}")
            return None

    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return None

# Security: Variable validation helper
def validate_terraform_vars(vars: dict) -> tuple[bool, str]:
    """
    Validate Terraform variables for security.
    Returns (is_valid, error_message)
    """
    if not isinstance(vars, dict):
        return False, "Variables must be a dictionary"

    # Check each variable
    for key, value in vars.items():
        # Validate key format (alphanumeric, underscore, dash)
        if not isinstance(key, str) or not key.replace('_', '').replace('-', '').isalnum():
            return False, f"Invalid variable name: {key}"

        # Validate value (convert to string and check for shell metacharacters)
        str_value = str(value)
        dangerous_chars = ['$', '`', '\\', '"', "'", ';', '&', '|', '>', '<', '(', ')', '{', '}']
        if any(char in str_value for char in dangerous_chars):
            return False, f"Variable value contains dangerous characters: {key}"

    return True, ""

# GitHub App support (optional)
try:
    from github_app_auth import GitHubAppAuth, GitHubAppConfig
    from github_repo_handler import GitHubRepoHandler

    # Initialize GitHub App if configured
    GITHUB_AUTH = None
    REPO_HANDLER = None

    async def initialize_github_app():
        """Initialize GitHub App components if configured."""
        global GITHUB_AUTH, REPO_HANDLER

        try:
            config = GitHubAppConfig.from_env()
            GITHUB_AUTH = GitHubAppAuth(config)
            REPO_HANDLER = GitHubRepoHandler(GITHUB_AUTH)
            logger.info("GitHub App integration initialized successfully")
        except Exception as e:
            logger.info("GitHub App not configured: %s", e)
            logger.info("Running without GitHub integration")

except ImportError:
    logger.info("GitHub App modules not found, running without GitHub integration")
    GITHUB_AUTH = None
    REPO_HANDLER = None

    async def initialize_github_app():
        pass

# Terraform Cloud support (optional)
try:
    from internal.cloud.terraform_cloud_client import TerraformCloudClient
    from internal.cloud.terraform_CLOUD_TOOLS import CloudTools

    TF_CLOUD_CLIENT = None
    CLOUD_TOOLS = None

    def initialize_terraform_cloud():
        """Initialize Terraform Cloud components if configured."""
        global TF_CLOUD_CLIENT, CLOUD_TOOLS

        api_token = os.environ.get('TF_CLOUD_API_TOKEN')
        if api_token:
            TF_CLOUD_CLIENT = TerraformCloudClient(api_token)
            CLOUD_TOOLS = CloudTools(TF_CLOUD_CLIENT)
            logger.info("Terraform Cloud integration initialized")
        else:
            logger.info("Terraform Cloud API token not found, running without Cloud integration")

except ImportError:
    logger.info("Terraform Cloud modules not found, running without Cloud integration")
    TF_CLOUD_CLIENT = None
    CLOUD_TOOLS = None

    def initialize_terraform_cloud():
        pass

# Module Intelligence support (optional)
try:
    from internal.analytics.MODULE_INTELLIGENCE import ModuleIntelligence

    MODULE_INTELLIGENCE = None

    def initialize_MODULE_INTELLIGENCE():
        """Initialize Module Intelligence if available."""
        global MODULE_INTELLIGENCE

        try:
            MODULE_INTELLIGENCE = ModuleIntelligence()
            logger.info("Module Intelligence initialized")
        except Exception as e:
            logger.info("Module Intelligence initialization failed: %s", e)

except ImportError:
    logger.info("Module Intelligence not found, running without analytics")
    MODULE_INTELLIGENCE = None

    def initialize_MODULE_INTELLIGENCE():
        pass


# Core Terraform Tools with Security Hardening
@mcp.tool()
async def terry(
    path: str,
    actions: list[str] = None,
    vars: dict = None,
    auto_approve: bool = False,
    destroy: bool = False
) -> dict:
    """
    Execute Terraform commands with comprehensive output and security validation.

    Args:
        path: Path to Terraform configuration (supports workspace:// and github:// prefixes)
        actions: List of actions to perform (default: ["plan"])
        vars: Variables to pass to Terraform
        auto_approve: Whether to auto-approve (blocked for safety)
        destroy: Whether to destroy resources (blocked for safety)

    Returns:
        Execution results with detailed output
    """
    # Security: Block dangerous flags
    if auto_approve:
        return {'error': 'auto_approve is blocked for security reasons'}
    if destroy:
        return {'error': 'destroy action is blocked for security reasons'}

    # Default actions
    if actions is None:
        actions = ["plan"]

    # Security: Validate actions
    for action in actions:
        if action in BLOCKED_ACTIONS:
            return {'error': f'Action "{action}" is blocked for security reasons'}
        if action not in ALLOWED_TERRAFORM_ACTIONS:
            return {'error': f'Unknown action "{action}". Allowed: {", ".join(ALLOWED_TERRAFORM_ACTIONS)}'}

    # Security: Validate variables
    if vars:
        is_valid, error_msg = validate_terraform_vars(vars)
        if not is_valid:
            return {'error': f'Variable validation failed: {error_msg}'}

    # Handle special path prefixes
    if path.startswith('github://') and REPO_HANDLER:
        # Extract GitHub info from path
        # Format: github://owner/repo/path/to/config
        parts = path[9:].split('/', 2)
        if len(parts) < 2:
            return {'error': 'Invalid GitHub path format. Use: github://owner/repo/path'}

        owner, repo = parts[0], parts[1]
        config_path = parts[2] if len(parts) > 2 else ''

        # Prepare workspace from GitHub
        workspace_result = await REPO_HANDLER.prepare_terraform_workspace(
            owner=owner,
            repo=repo,
            config_path=config_path
        )

        if 'error' in workspace_result:
            return workspace_result

        # Use the prepared workspace path
        path = workspace_result['workspace_path']
    else:
        # Security: Validate and normalize path
        validated_path = validate_and_normalize_path(path)
        if not validated_path:
            return {'error': 'Invalid path: access outside workspace is not allowed'}
        path = validated_path

    # Execute Terraform actions with security-hardened executor
    results = []
    for action in actions:
        result = await terraform_executor.execute_terraform(
            workspace_path=path,
            action=action,
            vars=vars if action in ['plan', 'apply'] else None
        )
        results.append(result)
        if not result.get('success'):
            break

    return {
        'success': all(r.get('success', False) for r in results),
        'results': results
    }


@mcp.tool()
async def terry_validate(file_path: str) -> dict:
    """Validate a Terraform file using Language Server Protocol."""
    # Security: Validate path
    validated_path = validate_and_normalize_path(file_path)
    if not validated_path:
        return {'error': 'Invalid file path: access outside workspace is not allowed'}

    # LSP not available in this server
    return {'error': 'LSP validation not available in MCP-only server'}


@mcp.tool()
async def terry_hover(file_path: str, line: int, character: int) -> dict:
    """Get hover information for a position in a Terraform file."""
    # Security: Validate path
    validated_path = validate_and_normalize_path(file_path)
    if not validated_path:
        return {'error': 'Invalid file path: access outside workspace is not allowed'}

    # LSP not available in this server
    return {'error': 'LSP hover not available in MCP-only server'}


@mcp.tool()
async def terry_complete(file_path: str, line: int, character: int) -> dict:
    """Get completion suggestions for a position in a Terraform file."""
    # Security: Validate path
    validated_path = validate_and_normalize_path(file_path)
    if not validated_path:
        return {'error': 'Invalid file path: access outside workspace is not allowed'}

    # LSP not available in this server
    return {'error': 'LSP completions not available in MCP-only server'}


@mcp.tool()
async def terry_format(file_path: str) -> dict:
    """Format a Terraform file using Language Server Protocol."""
    # Security: Validate path
    validated_path = validate_and_normalize_path(file_path)
    if not validated_path:
        return {'error': 'Invalid file path: access outside workspace is not allowed'}

    # LSP not available in this server
    return {'error': 'LSP formatting not available in MCP-only server'}


@mcp.tool()
async def terry_lsp_status() -> dict:
    """Get the status of the Terraform Language Server."""
    # LSP not available in this server
    return {'error': 'LSP not available in MCP-only server'}


# GitHub App Tools (if available)
if REPO_HANDLER:
    @mcp.tool()
    async def github_clone_repo(owner: str, repo: str, branch: str = None, force: bool = False) -> dict:
        """Clone or update a GitHub repository."""
        # Security: Basic validation for owner/repo names
        if not owner.replace('-', '').replace('_', '').isalnum():
            return {'error': 'Invalid repository owner name'}
        if not repo.replace('-', '').replace('_', '').replace('.', '').isalnum():
            return {'error': 'Invalid repository name'}

        return await REPO_HANDLER.clone_or_update_repo(
            owner=owner,
            repo=repo,
            branch=branch,
            force=force
        )

    @mcp.tool()
    async def github_list_terraform_files(owner: str, repo: str, path: str = '', pattern: str = '*.tf') -> dict:
        """List Terraform files in a GitHub repository."""
        # Security: Basic validation
        if not owner.replace('-', '').replace('_', '').isalnum():
            return {'error': 'Invalid repository owner name'}
        if not repo.replace('-', '').replace('_', '').replace('.', '').isalnum():
            return {'error': 'Invalid repository name'}

        return await REPO_HANDLER.list_terraform_files(
            owner=owner,
            repo=repo,
            path=path,
            pattern=pattern
        )

    @mcp.tool()
    async def github_get_terraform_config(owner: str, repo: str, config_path: str) -> dict:
        """Get information about a Terraform configuration in a GitHub repository."""
        # Security: Basic validation
        if not owner.replace('-', '').replace('_', '').isalnum():
            return {'error': 'Invalid repository owner name'}
        if not repo.replace('-', '').replace('_', '').replace('.', '').isalnum():
            return {'error': 'Invalid repository name'}

        return await REPO_HANDLER.get_terraform_config(
            owner=owner,
            repo=repo,
            config_path=config_path
        )

    @mcp.tool()
    async def github_prepare_workspace(owner: str, repo: str, config_path: str, workspace_name: str = None) -> dict:
        """Prepare a Terraform workspace from a GitHub repository."""
        # Security: Basic validation
        if not owner.replace('-', '').replace('_', '').isalnum():
            return {'error': 'Invalid repository owner name'}
        if not repo.replace('-', '').replace('_', '').replace('.', '').isalnum():
            return {'error': 'Invalid repository name'}

        return await REPO_HANDLER.prepare_terraform_workspace(
            owner=owner,
            repo=repo,
            config_path=config_path,
            workspace_name=workspace_name
        )

    @mcp.tool()
    async def github_repo_info(owner: str, repo: str) -> dict:
        """Get information about a GitHub repository."""
        # Security: Basic validation
        if not owner.replace('-', '').replace('_', '').isalnum():
            return {'error': 'Invalid repository owner name'}
        if not repo.replace('-', '').replace('_', '').replace('.', '').isalnum():
            return {'error': 'Invalid repository name'}

        return await REPO_HANDLER.get_repository_info(owner=owner, repo=repo)

    @mcp.tool()
    async def github_list_installations() -> dict:
        """List GitHub App installations and accessible repositories."""
        # GitHub App doesn't have a list_installations method, return error
        return {'error': 'List installations not implemented'}

    @mcp.tool()
    async def github_cleanup_repos(days_old: int = 7) -> dict:
        """Clean up old cloned repositories."""
        # Security: Validate days parameter
        if not isinstance(days_old, int) or days_old < 0 or days_old > 365:
            return {'error': 'Invalid days_old parameter. Must be between 0 and 365.'}

        return await REPO_HANDLER.cleanup_old_repos(days=days_old)


# Terraform Cloud Tools (if available)
if CLOUD_TOOLS:
    @mcp.tool()
    async def tf_cloud_workspaces(organization: str) -> dict:
        """List Terraform Cloud workspaces in an organization."""
        return await CLOUD_TOOLS.list_workspaces(organization)

    @mcp.tool()
    async def tf_cloud_workspace_info(organization: str, workspace: str) -> dict:
        """Get detailed information about a Terraform Cloud workspace."""
        return await CLOUD_TOOLS.get_workspace_info(organization, workspace)

    @mcp.tool()
    async def tf_cloud_runs(organization: str, workspace: str, limit: int = 10) -> dict:
        """List recent runs for a Terraform Cloud workspace."""
        # Security: Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return {'error': 'Invalid limit. Must be between 1 and 100.'}

        return await CLOUD_TOOLS.list_runs(organization, workspace, limit)

    @mcp.tool()
    async def tf_cloud_run_details(run_id: str) -> dict:
        """Get detailed information about a specific Terraform Cloud run."""
        return await CLOUD_TOOLS.get_run_details(run_id)

    @mcp.tool()
    async def tf_cloud_state_outputs(organization: str, workspace: str) -> dict:
        """Get the current state outputs from a Terraform Cloud workspace."""
        return await CLOUD_TOOLS.get_state_outputs(organization, workspace)


# Module Intelligence Tools (if available)
if MODULE_INTELLIGENCE:
    @mcp.tool()
    async def terry_analyze_modules(config_path: str) -> dict:
        """Analyze Terraform modules and their relationships."""
        # Security: Validate path
        validated_path = validate_and_normalize_path(config_path)
        if not validated_path:
            return {'error': 'Invalid path: access outside workspace is not allowed'}

        return await MODULE_INTELLIGENCE.analyze_configuration(validated_path)

    @mcp.tool()
    async def terry_module_recommendations(config_path: str) -> dict:
        """Get module recommendations based on current configuration."""
        # Security: Validate path
        validated_path = validate_and_normalize_path(config_path)
        if not validated_path:
            return {'error': 'Invalid path: access outside workspace is not allowed'}

        return await MODULE_INTELLIGENCE.get_recommendations(validated_path)

    @mcp.tool()
    async def terry_security_scan(config_path: str) -> dict:
        """Scan Terraform configuration for security issues."""
        # Security: Validate path
        validated_path = validate_and_normalize_path(config_path)
        if not validated_path:
            return {'error': 'Invalid path: access outside workspace is not allowed'}

        return await MODULE_INTELLIGENCE.security_scan(validated_path)


# Workspace tools
@mcp.tool()
async def terry_workspace_info(path: str = ".") -> dict:
    """Get information about a Terraform workspace."""
    # Security: Validate path
    validated_path = validate_and_normalize_path(path)
    if not validated_path:
        return {'error': 'Invalid path: access outside workspace is not allowed'}

    target_path = Path(validated_path)
    workspace_base = Path("/mnt/workspace")

    info = {
        "path_info": {
            "requested_path": path,
            "full_path": str(target_path),
            "relative_path": (
                str(target_path.relative_to(workspace_base))
                if target_path.is_relative_to(workspace_base)
                else path
            ),
            "exists": target_path.exists(),
            "is_directory": target_path.is_dir() if target_path.exists() else False
        },
        "terraform_files": [],
        "terraform_state": {},
        "github_repos": []
    }

    if target_path.exists() and target_path.is_dir():
        # List Terraform files
        tf_files = list(target_path.glob("*.tf"))
        info["terraform_files"] = [f.name for f in tf_files]

        # Check Terraform state
        info["terraform_state"]["initialized"] = (target_path / ".terraform").exists()
        info["terraform_state"]["terraform_dir_exists"] = (target_path / ".terraform").exists()
        info["terraform_state"]["state_file_exists"] = (target_path / "terraform.tfstate").exists()

        # Check for common files
        info["common_files"] = {
            "main.tf": (target_path / "main.tf").exists(),
            "variables.tf": (target_path / "variables.tf").exists(),
            "outputs.tf": (target_path / "outputs.tf").exists(),
            "providers.tf": (target_path / "providers.tf").exists(),
            "terraform.tf": (target_path / "terraform.tf").exists(),
            "versions.tf": (target_path / "versions.tf").exists()
        }

        # Check for GitHub repos in workspace
        github_repos_dir = workspace_base / "github-repos"
        if github_repos_dir.exists():
            info["github_repos"] = [d.name for d in github_repos_dir.iterdir() if d.is_dir()]

    return {"terry-workspace": info}


async def main():
    """Main entry point."""
    # Initialize optional components
    await initialize_github_app()
    initialize_terraform_cloud()
    initialize_MODULE_INTELLIGENCE()

    # Log configuration
    logger.info("Terry-Form MCP Server (MCP Only) v3.0.0 starting...")
    logger.info("Security hardening enabled per Orca findings")
    logger.info(f"GitHub Integration: {'Enabled' if REPO_HANDLER else 'Disabled'}")
    logger.info(f"Terraform Cloud: {'Enabled' if CLOUD_TOOLS else 'Disabled'}")
    logger.info(f"Module Intelligence: {'Enabled' if MODULE_INTELLIGENCE else 'Disabled'}")

    # Run the FastMCP server
    await mcp.run()


if __name__ == "__main__":
    asyncio.run(main())
