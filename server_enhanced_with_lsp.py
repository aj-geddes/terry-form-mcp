#!/usr/bin/env python3
import asyncio
import importlib.util
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("terry-form")

# Load the existing Terraform tool logic (kebab-case)
spec = importlib.util.spec_from_file_location("terry_form", "./terry-form-mcp.py")
terry_form = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terry_form)

# Load the LSP client
spec_lsp = importlib.util.spec_from_file_location(
    "terraform_lsp_client", "./terraform_lsp_client.py"
)
terraform_lsp_client = importlib.util.module_from_spec(spec_lsp)
spec_lsp.loader.exec_module(terraform_lsp_client)

# ============================================================================
# EXISTING TERRAFORM EXECUTION TOOLS
# ============================================================================


@mcp.tool()
def terry(
    path: str, actions: List[str] = ["plan"], vars: Dict[str, str] = {}
) -> Dict[str, object]:
    """
    Runs terraform actions in /mnt/workspace/<path> using provided variables.
    Returns a raw JSON result dictionary under `terry-results`.

    Supported actions: init, validate, fmt, plan
    """
    full_path = str(Path("/mnt/workspace") / path)
    results = []
    for action in actions:
        results.append(
            terry_form.run_terraform(
                full_path, action, vars if action == "plan" else None
            )
        )
    return {"terry-results": results}


# ============================================================================
# NEW DIAGNOSTIC AND UTILITY TOOLS
# ============================================================================


@mcp.tool()
def terry_environment_check() -> Dict[str, object]:
    """
    Comprehensive environment check for Terraform and LSP integration.
    Checks container environment, available tools, and configuration.
    """
    results = {}

    try:
        # Basic environment info
        results["environment"] = {
            "working_directory": os.getcwd(),
            "user": os.getenv("USER", "unknown"),
            "path": os.getenv("PATH", ""),
            "workspace_mount": os.path.exists("/mnt/workspace"),
        }

        # Check Terraform
        terraform_check = subprocess.run(
            ["which", "terraform"], capture_output=True, text=True
        )
        if terraform_check.returncode == 0:
            version_check = subprocess.run(
                ["terraform", "version"], capture_output=True, text=True
            )
            results["terraform"] = {
                "available": True,
                "path": terraform_check.stdout.strip(),
                "version": (
                    version_check.stdout.strip()
                    if version_check.returncode == 0
                    else "version check failed"
                ),
            }
        else:
            results["terraform"] = {"available": False, "error": "terraform not found"}

        # Check terraform-ls
        terraformls_check = subprocess.run(
            ["which", "terraform-ls"], capture_output=True, text=True
        )
        if terraformls_check.returncode == 0:
            version_check = subprocess.run(
                ["terraform-ls", "version"], capture_output=True, text=True
            )
            results["terraform_ls"] = {
                "available": True,
                "path": terraformls_check.stdout.strip(),
                "version": (
                    version_check.stdout.strip()
                    if version_check.returncode == 0
                    else "version check failed"
                ),
            }
        else:
            results["terraform_ls"] = {
                "available": False,
                "error": "terraform-ls not found",
            }

        # Check common paths
        common_paths = ["/usr/local/bin/terraform-ls", "/usr/bin/terraform-ls"]
        results["terraform_ls"]["common_paths"] = {}
        for path in common_paths:
            results["terraform_ls"]["common_paths"][path] = os.path.exists(path)

        # Container detection
        results["container"] = {
            "is_docker": os.path.exists("/.dockerenv"),
            "hostname": subprocess.run(
                ["hostname"], capture_output=True, text=True
            ).stdout.strip(),
        }

        return {"terry-environment": results}

    except Exception as e:
        return {"terry-environment": {"error": str(e)}}


@mcp.tool()
def terry_lsp_debug() -> Dict[str, object]:
    """
    Debug terraform-ls functionality and LSP client state.
    Tests terraform-ls availability and basic functionality.
    """
    results = {}

    try:
        # Test terraform-ls binary
        try:
            version_result = subprocess.run(
                ["terraform-ls", "version"], capture_output=True, text=True, timeout=10
            )
            results["terraform_ls_binary"] = {
                "available": version_result.returncode == 0,
                "version": (
                    version_result.stdout.strip()
                    if version_result.returncode == 0
                    else None
                ),
                "error": (
                    version_result.stderr.strip()
                    if version_result.returncode != 0
                    else None
                ),
            }
        except subprocess.TimeoutExpired:
            results["terraform_ls_binary"] = {"available": False, "error": "timeout"}
        except FileNotFoundError:
            results["terraform_ls_binary"] = {
                "available": False,
                "error": "binary not found",
            }
        except Exception as e:
            results["terraform_ls_binary"] = {"available": False, "error": str(e)}

        # Test LSP client state
        if terraform_lsp_client._lsp_client:
            results["lsp_client"] = {
                "exists": True,
                "initialized": terraform_lsp_client._lsp_client.initialized,
                "workspace_root": terraform_lsp_client._lsp_client.workspace_root,
                "process_active": terraform_lsp_client._lsp_client.terraform_ls_process
                is not None,
            }
        else:
            results["lsp_client"] = {"exists": False}

        # Test LSP help command
        try:
            help_result = subprocess.run(
                ["terraform-ls", "serve", "--help"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            results["terraform_ls_help"] = {
                "available": help_result.returncode == 0,
                "output": (
                    help_result.stdout[:200] + "..."
                    if len(help_result.stdout) > 200
                    else help_result.stdout
                ),
            }
        except Exception as e:
            results["terraform_ls_help"] = {"error": str(e)}

        return {"terry-lsp-debug": results}

    except Exception as e:
        return {"terry-lsp-debug": {"error": str(e)}}


@mcp.tool()
def terry_workspace_info(path: str = ".") -> Dict[str, object]:
    """
    Analyze Terraform workspace structure and provide recommendations.
    Shows file structure, configuration status, and LSP readiness.
    """
    full_path = str(Path("/mnt/workspace") / path)
    results = {}

    try:
        if not os.path.exists(full_path):
            return {"terry-workspace": {"error": f"Path {full_path} does not exist"}}

        # Basic path info
        results["path_info"] = {
            "full_path": full_path,
            "relative_path": path,
            "exists": True,
            "is_directory": os.path.isdir(full_path),
        }

        # Find Terraform files
        tf_files = []
        if os.path.isdir(full_path):
            for item in os.listdir(full_path):
                if item.endswith(".tf") or item.endswith(".tfvars"):
                    tf_files.append(item)

        results["terraform_files"] = tf_files

        # Check for terraform initialization
        terraform_dir = os.path.join(full_path, ".terraform")
        results["terraform_state"] = {
            "initialized": os.path.exists(terraform_dir),
            "terraform_dir_exists": os.path.exists(terraform_dir),
            "state_file_exists": os.path.exists(
                os.path.join(full_path, "terraform.tfstate")
            ),
        }

        # Check for common Terraform files
        common_files = [
            "main.tf",
            "variables.tf",
            "outputs.tf",
            "providers.tf",
            "terraform.tf",
            "versions.tf",
        ]
        results["common_files"] = {}
        for file in common_files:
            file_path = os.path.join(full_path, file)
            results["common_files"][file] = os.path.exists(file_path)

        # LSP readiness assessment
        results["lsp_readiness"] = {
            "has_terraform_files": len(tf_files) > 0,
            "has_main_tf": "main.tf" in tf_files,
            "is_initialized": os.path.exists(terraform_dir),
            "recommended_actions": [],
        }

        if len(tf_files) == 0:
            results["lsp_readiness"]["recommended_actions"].append(
                "Create Terraform files (.tf)"
            )
        if not os.path.exists(terraform_dir):
            results["lsp_readiness"]["recommended_actions"].append("Run terraform init")

        return {"terry-workspace": results}

    except Exception as e:
        return {"terry-workspace": {"error": str(e)}}


@mcp.tool()
async def terry_lsp_init(workspace_path: str) -> Dict[str, object]:
    """
    Manually initialize LSP client for a specific workspace.
    Useful for troubleshooting LSP initialization issues.
    """
    try:
        full_workspace_path = str(Path("/mnt/workspace") / workspace_path)

        # Check if workspace exists
        if not os.path.exists(full_workspace_path):
            return {
                "terry-lsp-init": {
                    "error": f"Workspace {full_workspace_path} does not exist"
                }
            }

        # Shutdown existing client if any
        if terraform_lsp_client._lsp_client:
            await terraform_lsp_client._lsp_client.shutdown()
            terraform_lsp_client._lsp_client = None

        # Create new LSP client
        lsp_client = await terraform_lsp_client.get_lsp_client(full_workspace_path)

        if lsp_client and lsp_client.initialized:
            return {
                "terry-lsp-init": {
                    "success": True,
                    "workspace": full_workspace_path,
                    "capabilities": lsp_client.capabilities,
                    "message": "LSP client initialized successfully",
                }
            }
        else:
            return {
                "terry-lsp-init": {
                    "success": False,
                    "workspace": full_workspace_path,
                    "error": "Failed to initialize LSP client",
                }
            }

    except Exception as e:
        return {"terry-lsp-init": {"error": str(e)}}


@mcp.tool()
def terry_file_check(file_path: str) -> Dict[str, object]:
    """
    Check Terraform file syntax and readiness for LSP operations.
    Validates file exists, is readable, and has basic Terraform syntax.
    """
    try:
        full_path = str(Path("/mnt/workspace") / file_path)

        results = {
            "file_path": file_path,
            "full_path": full_path,
            "exists": os.path.exists(full_path),
            "is_file": (
                os.path.isfile(full_path) if os.path.exists(full_path) else False
            ),
            "readable": False,
            "size": 0,
            "syntax_check": {},
        }

        if results["exists"] and results["is_file"]:
            try:
                with open(full_path, "r") as f:
                    content = f.read()
                    results["readable"] = True
                    results["size"] = len(content)

                    # Basic syntax checks
                    results["syntax_check"] = {
                        "has_content": len(content.strip()) > 0,
                        "has_terraform_block": "terraform {" in content,
                        "has_resource_block": 'resource "' in content,
                        "has_data_block": 'data "' in content,
                        "line_count": len(content.split("\n")),
                    }

            except Exception as e:
                results["syntax_check"]["error"] = str(e)

        return {"terry-file-check": results}

    except Exception as e:
        return {"terry-file-check": {"error": str(e)}}


@mcp.tool()
def terry_workspace_setup(
    path: str, project_name: str = "terraform-project"
) -> Dict[str, object]:
    """
    Create a properly structured Terraform workspace ready for LSP operations.
    Sets up basic files and directory structure.
    """
    try:
        full_path = str(Path("/mnt/workspace") / path)

        # Create directory if it doesn't exist
        os.makedirs(full_path, exist_ok=True)

        created_files = []

        # Create main.tf if it doesn't exist
        main_tf_path = os.path.join(full_path, "main.tf")
        if not os.path.exists(main_tf_path):
            main_tf_content = f"""# {project_name} - Main Configuration
terraform {{
  required_version = ">= 1.0"
  required_providers {{
    # Add your required providers here
    # Example:
    # azurerm = {{
    #   source  = "hashicorp/azurerm"
    #   version = "~> 3.0"
    # }}
  }}
}}

# Configure providers here
# provider "azurerm" {{
#   features {{}}
# }}

# Add your resources here
"""
            with open(main_tf_path, "w") as f:
                f.write(main_tf_content)
            created_files.append("main.tf")

        # Create variables.tf if it doesn't exist
        variables_tf_path = os.path.join(full_path, "variables.tf")
        if not os.path.exists(variables_tf_path):
            variables_tf_content = f"""# {project_name} - Variable Definitions

variable "environment" {{
  description = "Environment name"
  type        = string
  default     = "dev"
}}

variable "project_name" {{
  description = "Name of the project"
  type        = string
  default     = "{project_name}"
}}
"""
            with open(variables_tf_path, "w") as f:
                f.write(variables_tf_content)
            created_files.append("variables.tf")

        # Create outputs.tf if it doesn't exist
        outputs_tf_path = os.path.join(full_path, "outputs.tf")
        if not os.path.exists(outputs_tf_path):
            outputs_tf_content = f"""# {project_name} - Output Values

# Example output
# output "example_output" {{
#   description = "Example output value"
#   value       = "example"
# }}
"""
            with open(outputs_tf_path, "w") as f:
                f.write(outputs_tf_content)
            created_files.append("outputs.tf")

        return {
            "terry-workspace-setup": {
                "success": True,
                "workspace_path": full_path,
                "project_name": project_name,
                "created_files": created_files,
                "message": f"Workspace setup complete. Created {len(created_files)} files.",
            }
        }

    except Exception as e:
        return {"terry-workspace-setup": {"error": str(e)}}


# ============================================================================
# ENHANCED LSP TOOLS WITH BETTER ERROR HANDLING
# ============================================================================


@mcp.tool()
async def terraform_validate_lsp(
    file_path: str, workspace_path: Optional[str] = None
) -> Dict[str, object]:
    """
    Validate a Terraform file using terraform-ls Language Server.
    Provides detailed diagnostics and syntax validation.

    Args:
        file_path: Path to Terraform file relative to workspace (e.g., "main.tf" or "modules/vpc/main.tf")
        workspace_path: Optional workspace directory (defaults to parent directory of file)
    """
    try:
        # Resolve full paths
        if workspace_path:
            full_workspace_path = str(Path("/mnt/workspace") / workspace_path)
            full_file_path = str(Path(full_workspace_path) / file_path)
        else:
            full_file_path = str(Path("/mnt/workspace") / file_path)
            full_workspace_path = str(Path(full_file_path).parent)

        # Check if file exists
        if not os.path.exists(full_file_path):
            return {
                "terraform-ls-validation": {
                    "file_path": file_path,
                    "workspace_path": full_workspace_path,
                    "error": f"File {full_file_path} does not exist",
                }
            }

        # Get LSP client
        lsp_client = await terraform_lsp_client.get_lsp_client(full_workspace_path)

        # Validate document
        result = await lsp_client.validate_document(full_file_path)

        return {
            "terraform-ls-validation": {
                "file_path": file_path,
                "workspace_path": full_workspace_path,
                **result,
            }
        }

    except Exception as e:
        return {"terraform-ls-validation": {"error": str(e), "file_path": file_path}}


@mcp.tool()
async def terraform_hover(
    file_path: str, line: int, character: int, workspace_path: Optional[str] = None
) -> Dict[str, object]:
    """
    Get documentation and information for Terraform resource at cursor position.

    Args:
        file_path: Path to Terraform file relative to workspace
        line: Line number (0-based)
        character: Character position (0-based)
        workspace_path: Optional workspace directory
    """
    try:
        # Resolve full paths
        if workspace_path:
            full_workspace_path = str(Path("/mnt/workspace") / workspace_path)
            full_file_path = str(Path(full_workspace_path) / file_path)
        else:
            full_file_path = str(Path("/mnt/workspace") / file_path)
            full_workspace_path = str(Path(full_file_path).parent)

        # Check if file exists
        if not os.path.exists(full_file_path):
            return {
                "terraform-hover": {
                    "file_path": file_path,
                    "position": {"line": line, "character": character},
                    "error": f"File {full_file_path} does not exist",
                }
            }

        # Get LSP client
        lsp_client = await terraform_lsp_client.get_lsp_client(full_workspace_path)

        # Get hover info
        result = await lsp_client.get_hover_info(full_file_path, line, character)

        return {
            "terraform-hover": {
                "file_path": file_path,
                "position": {"line": line, "character": character},
                **result,
            }
        }

    except Exception as e:
        return {
            "terraform-hover": {
                "error": str(e),
                "file_path": file_path,
                "position": {"line": line, "character": character},
            }
        }


@mcp.tool()
async def terraform_complete(
    file_path: str, line: int, character: int, workspace_path: Optional[str] = None
) -> Dict[str, object]:
    """
    Get completion suggestions for Terraform code at cursor position.

    Args:
        file_path: Path to Terraform file relative to workspace
        line: Line number (0-based)
        character: Character position (0-based)
        workspace_path: Optional workspace directory
    """
    try:
        # Resolve full paths
        if workspace_path:
            full_workspace_path = str(Path("/mnt/workspace") / workspace_path)
            full_file_path = str(Path(full_workspace_path) / file_path)
        else:
            full_file_path = str(Path("/mnt/workspace") / file_path)
            full_workspace_path = str(Path(full_file_path).parent)

        # Check if file exists
        if not os.path.exists(full_file_path):
            return {
                "terraform-completions": {
                    "file_path": file_path,
                    "position": {"line": line, "character": character},
                    "error": f"File {full_file_path} does not exist",
                }
            }

        # Get LSP client
        lsp_client = await terraform_lsp_client.get_lsp_client(full_workspace_path)

        # Get completions
        result = await lsp_client.get_completions(full_file_path, line, character)

        return {
            "terraform-completions": {
                "file_path": file_path,
                "position": {"line": line, "character": character},
                **result,
            }
        }

    except Exception as e:
        return {
            "terraform-completions": {
                "error": str(e),
                "file_path": file_path,
                "position": {"line": line, "character": character},
            }
        }


@mcp.tool()
async def terraform_format_lsp(
    file_path: str, workspace_path: Optional[str] = None
) -> Dict[str, object]:
    """
    Format a Terraform file using terraform-ls Language Server.

    Args:
        file_path: Path to Terraform file relative to workspace
        workspace_path: Optional workspace directory
    """
    try:
        # Resolve full paths
        if workspace_path:
            full_workspace_path = str(Path("/mnt/workspace") / workspace_path)
            full_file_path = str(Path(full_workspace_path) / file_path)
        else:
            full_file_path = str(Path("/mnt/workspace") / file_path)
            full_workspace_path = str(Path(full_file_path).parent)

        # Check if file exists
        if not os.path.exists(full_file_path):
            return {
                "terraform-format": {
                    "file_path": file_path,
                    "error": f"File {full_file_path} does not exist",
                }
            }

        # Get LSP client
        lsp_client = await terraform_lsp_client.get_lsp_client(full_workspace_path)

        # Format document
        result = await lsp_client.format_document(full_file_path)

        return {"terraform-format": {"file_path": file_path, **result}}

    except Exception as e:
        return {"terraform-format": {"error": str(e), "file_path": file_path}}


@mcp.tool()
def terraform_lsp_status() -> Dict[str, object]:
    """
    Get the status of the terraform-ls Language Server integration.
    """
    global terraform_lsp_client

    if (
        terraform_lsp_client._lsp_client
        and terraform_lsp_client._lsp_client.initialized
    ):
        return {
            "terraform-ls-status": {
                "status": "active",
                "initialized": True,
                "capabilities": terraform_lsp_client._lsp_client.capabilities,
                "workspace_root": terraform_lsp_client._lsp_client.workspace_root,
            }
        }
    else:
        return {
            "terraform-ls-status": {
                "status": "inactive",
                "initialized": False,
                "message": "terraform-ls not started. Use any LSP tool to initialize.",
            }
        }


# ============================================================================
# SERVER STARTUP AND SHUTDOWN
# ============================================================================


async def _shutdown_handler():
    """Cleanup LSP client on server shutdown"""
    if terraform_lsp_client._lsp_client:
        await terraform_lsp_client._lsp_client.shutdown()


if __name__ == "__main__":
    try:
        # Register shutdown handler
        import atexit
        import signal

        def cleanup():
            if terraform_lsp_client._lsp_client:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(terraform_lsp_client._lsp_client.shutdown())
                loop.close()

        atexit.register(cleanup)
        signal.signal(signal.SIGTERM, lambda s, f: cleanup())

        # Start MCP server
        mcp.run()

    except KeyboardInterrupt:
        # Cleanup on Ctrl+C
        if terraform_lsp_client._lsp_client:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(terraform_lsp_client._lsp_client.shutdown())
