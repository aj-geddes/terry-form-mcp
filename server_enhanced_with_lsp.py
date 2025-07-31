#!/usr/bin/env python3
import asyncio
import importlib.util
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP("terry-form")

# Import security validator
try:
    spec_validator = importlib.util.spec_from_file_location(
        "mcp_request_validator", "./mcp_request_validator.py"
    )
    mcp_request_validator = importlib.util.module_from_spec(spec_validator)
    spec_validator.loader.exec_module(mcp_request_validator)
    
    # Initialize validator
    request_validator = mcp_request_validator.MCPRequestValidator()
    logger.info("Security validator initialized")
except Exception as e:
    logger.error(f"Failed to load security validator: {e}")
    request_validator = None

# Security validation decorator
def validate_request(tool_name: str):
    """Decorator to validate MCP requests before tool execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Log tool invocation for audit trail
            logger.info(f"Tool invoked: {tool_name} with args: {kwargs}")
            
            # Validate request if validator is available
            if request_validator:
                # Construct MCP request format
                request = {
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": kwargs
                    }
                }
                
                is_valid, error_msg = request_validator.validate_request(request)
                if not is_valid:
                    logger.warning(f"Request validation failed for {tool_name}: {error_msg}")
                    return {"error": f"Validation failed: {error_msg}"}
            
            # Path validation for path-based tools
            if "path" in kwargs:
                path = kwargs["path"]
                if not validate_safe_path(path):
                    return {"error": "Invalid path: Access outside workspace is not allowed"}
            
            # Execute the tool
            try:
                result = func(*args, **kwargs)
                logger.info(f"Tool {tool_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Tool {tool_name} failed with error: {e}")
                return {"error": f"Tool execution failed: {str(e)}"}
        
        # Preserve async functions
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Log tool invocation for audit trail
                logger.info(f"Tool invoked: {tool_name} with args: {kwargs}")
                
                # Validate request if validator is available
                if request_validator:
                    # Construct MCP request format
                    request = {
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": kwargs
                        }
                    }
                    
                    is_valid, error_msg = request_validator.validate_request(request)
                    if not is_valid:
                        logger.warning(f"Request validation failed for {tool_name}: {error_msg}")
                        return {"error": f"Validation failed: {error_msg}"}
                
                # Path validation for path-based tools
                if "path" in kwargs:
                    path = kwargs["path"]
                    if not validate_safe_path(path):
                        return {"error": "Invalid path: Access outside workspace is not allowed"}
                
                # Execute the tool
                try:
                    result = await func(*args, **kwargs)
                    logger.info(f"Tool {tool_name} completed successfully")
                    return result
                except Exception as e:
                    logger.error(f"Tool {tool_name} failed with error: {e}")
                    return {"error": f"Tool execution failed: {str(e)}"}
            
            return async_wrapper
        
        return wrapper
    return decorator


def validate_safe_path(path: str, workspace_root: str = "/mnt/workspace") -> bool:
    """Validate that a path is safe and within workspace bounds"""
    try:
        # Handle special prefixes
        if path.startswith(("github://", "workspace://")):
            return True
        
        workspace_base = Path(workspace_root)
        
        # Convert to absolute path
        if path.startswith("/"):
            target_path = Path(path)
        else:
            target_path = workspace_base / path
        
        # Resolve to real path
        real_path = target_path.resolve()
        
        # Ensure path is within workspace
        real_path.relative_to(workspace_base.resolve())
        return True
    except (ValueError, Exception):
        return False


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
@validate_request("terry")
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
@validate_request("terry_workspace_list")
def terry_workspace_list() -> Dict[str, object]:
    """
    List all available Terraform workspaces in /mnt/workspace.
    Returns workspace paths with initialization status and metadata.
    """
    workspace_root = Path("/mnt/workspace")
    workspaces = []
    
    try:
        # Scan workspace directory for Terraform projects
        for root, dirs, files in os.walk(workspace_root):
            # Skip hidden directories and common non-terraform directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            # Check if this directory contains Terraform files
            tf_files = [f for f in files if f.endswith('.tf')]
            if tf_files:
                rel_path = os.path.relpath(root, workspace_root)
                workspace_info = {
                    "path": rel_path,
                    "initialized": os.path.exists(os.path.join(root, ".terraform")),
                    "has_state": os.path.exists(os.path.join(root, "terraform.tfstate")),
                    "providers": [],
                    "modules": 0,
                    "last_modified": None
                }
                
                # Get last modified time
                try:
                    mtime = max(os.path.getmtime(os.path.join(root, f)) for f in tf_files)
                    workspace_info["last_modified"] = subprocess.run(
                        ["date", "-u", "-d", f"@{int(mtime)}", "+%Y-%m-%dT%H:%M:%SZ"],
                        capture_output=True, text=True
                    ).stdout.strip()
                except:
                    pass
                
                # Extract provider information
                for tf_file in tf_files:
                    try:
                        with open(os.path.join(root, tf_file), 'r') as f:
                            content = f.read()
                            # Simple provider extraction
                            import re
                            providers = re.findall(r'provider\s+"([^"]+)"', content)
                            workspace_info["providers"].extend(providers)
                            # Count module calls
                            modules = re.findall(r'module\s+"[^"]+"', content)
                            workspace_info["modules"] += len(modules)
                    except:
                        pass
                
                workspace_info["providers"] = list(set(workspace_info["providers"]))
                workspaces.append(workspace_info)
        
        return {"workspaces": workspaces}
        
    except Exception as e:
        return {"error": f"Failed to list workspaces: {str(e)}"}


@mcp.tool()
@validate_request("terry_version")
def terry_version() -> Dict[str, object]:
    """
    Get Terraform version information and provider selections.
    Returns version details and available provider information.
    """
    try:
        # Get Terraform version
        version_result = subprocess.run(
            ["terraform", "version", "-json"],
            capture_output=True,
            text=True
        )
        
        if version_result.returncode == 0:
            try:
                version_data = json.loads(version_result.stdout)
                result = {
                    "terraform_version": version_data.get("terraform_version", "unknown"),
                    "platform": version_data.get("platform", "unknown"),
                    "provider_selections": {}
                }
                
                # Extract provider versions if available
                if "provider_selections" in version_data:
                    result["provider_selections"] = version_data["provider_selections"]
                
                return result
                
            except json.JSONDecodeError:
                # Fallback to non-JSON version
                version_result = subprocess.run(
                    ["terraform", "version"],
                    capture_output=True,
                    text=True
                )
                if version_result.returncode == 0:
                    lines = version_result.stdout.strip().split('\n')
                    terraform_version = lines[0].replace("Terraform v", "") if lines else "unknown"
                    
                    # Get platform info
                    platform_result = subprocess.run(
                        ["uname", "-m"],
                        capture_output=True,
                        text=True
                    )
                    platform = f"linux_{platform_result.stdout.strip()}" if platform_result.returncode == 0 else "unknown"
                    
                    return {
                        "terraform_version": terraform_version,
                        "platform": platform,
                        "provider_selections": {}
                    }
        
        return {"error": "Failed to get Terraform version"}
        
    except FileNotFoundError:
        return {"error": "Terraform not found in PATH"}
    except Exception as e:
        return {"error": f"Failed to get version: {str(e)}"}


@mcp.tool()
@validate_request("terry_environment_check")
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
@validate_request("terry_lsp_debug")
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
@validate_request("terry_workspace_info")
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
@validate_request("terry_lsp_init")
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
@validate_request("terry_file_check")
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
@validate_request("terry_workspace_setup")
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
@validate_request("terraform_validate_lsp")
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
@validate_request("terraform_hover")
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
@validate_request("terraform_complete")
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
@validate_request("terraform_format_lsp")
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
@validate_request("terraform_lsp_status")
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
# INTELLIGENCE TOOLS
# ============================================================================

@mcp.tool()
@validate_request("terry_analyze")
def terry_analyze(path: str) -> Dict[str, object]:
    """
    Analyze Terraform configuration for best practices.
    
    Args:
        path: Workspace path relative to /mnt/workspace
    
    Returns:
        Analysis report with score, issues, and statistics
    """
    full_path = str(Path("/mnt/workspace") / path)
    
    if not os.path.exists(full_path):
        return {"error": f"Path {full_path} does not exist"}
    
    analysis = {
        "score": 100,  # Start with perfect score
        "issues": [],
        "statistics": {
            "resources": 0,
            "data_sources": 0,
            "modules": 0,
            "providers": 0,
            "variables": 0,
            "outputs": 0
        }
    }
    
    try:
        # Analyze all .tf files in the directory
        for tf_file in Path(full_path).glob("*.tf"):
            with open(tf_file, 'r') as f:
                content = f.read()
                
                # Count resources
                resources = re.findall(r'resource\s+"[^"]+"\s+"[^"]+"', content)
                analysis["statistics"]["resources"] += len(resources)
                
                # Count data sources
                data_sources = re.findall(r'data\s+"[^"]+"\s+"[^"]+"', content)
                analysis["statistics"]["data_sources"] += len(data_sources)
                
                # Count modules
                modules = re.findall(r'module\s+"[^"]+"', content)
                analysis["statistics"]["modules"] += len(modules)
                
                # Count providers
                providers = re.findall(r'provider\s+"[^"]+"', content)
                analysis["statistics"]["providers"] += len(set(providers))
                
                # Count variables
                variables = re.findall(r'variable\s+"[^"]+"', content)
                analysis["statistics"]["variables"] += len(variables)
                
                # Count outputs
                outputs = re.findall(r'output\s+"[^"]+"', content)
                analysis["statistics"]["outputs"] += len(outputs)
                
                # Check for common issues
                
                # Missing descriptions on variables
                var_blocks = re.findall(r'variable\s+"([^"]+)"\s*{([^}]+)}', content, re.DOTALL)
                for var_name, var_body in var_blocks:
                    if 'description' not in var_body:
                        analysis["issues"].append({
                            "severity": "warning",
                            "type": "documentation",
                            "message": f"Variable '{var_name}' lacks description",
                            "file": tf_file.name,
                            "recommendation": "Add description field to variable block"
                        })
                        analysis["score"] -= 2
                
                # Check for hardcoded values
                hardcoded_patterns = [
                    (r'ami-[a-f0-9]{8,}', "Hardcoded AMI ID detected"),
                    (r'i-[a-f0-9]{8,}', "Hardcoded instance ID detected"),
                    (r'vpc-[a-f0-9]{8,}', "Hardcoded VPC ID detected"),
                    (r'subnet-[a-f0-9]{8,}', "Hardcoded subnet ID detected")
                ]
                
                for pattern, message in hardcoded_patterns:
                    if re.search(pattern, content):
                        analysis["issues"].append({
                            "severity": "warning",
                            "type": "hardcoding",
                            "message": message,
                            "file": tf_file.name,
                            "recommendation": "Use variables or data sources instead of hardcoded IDs"
                        })
                        analysis["score"] -= 5
                
                # Check for missing tags on taggable resources
                taggable_resources = ['aws_instance', 'aws_s3_bucket', 'aws_vpc', 'aws_security_group']
                for resource_type in taggable_resources:
                    resource_blocks = re.findall(rf'resource\s+"{resource_type}"\s+"[^"]+"\s*{{([^}}]+)}}', content, re.DOTALL)
                    for resource_body in resource_blocks:
                        if 'tags' not in resource_body:
                            analysis["issues"].append({
                                "severity": "info",
                                "type": "best_practice",
                                "message": f"Resource type '{resource_type}' lacks tags",
                                "file": tf_file.name,
                                "recommendation": "Add tags for better resource management"
                            })
                            analysis["score"] -= 1
        
        # Ensure score doesn't go below 0
        analysis["score"] = max(0, analysis["score"])
        
        return {"analysis": analysis}
        
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}


@mcp.tool()
@validate_request("terry_security_scan")
def terry_security_scan(path: str, severity: str = "medium") -> Dict[str, object]:
    """
    Run security scan on Terraform configuration.
    
    Args:
        path: Workspace path relative to /mnt/workspace
        severity: Minimum severity to report (low, medium, high, critical)
    
    Returns:
        Security scan results with vulnerabilities and summary
    """
    full_path = str(Path("/mnt/workspace") / path)
    
    if not os.path.exists(full_path):
        return {"error": f"Path {full_path} does not exist"}
    
    severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    min_severity = severity_levels.get(severity.lower(), 2)
    
    security_scan = {
        "vulnerabilities": [],
        "summary": {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
    }
    
    try:
        # Security checks for all .tf files
        for tf_file in Path(full_path).glob("*.tf"):
            with open(tf_file, 'r') as f:
                content = f.read()
                file_lines = content.split('\n')
                
                # Check for public S3 buckets
                s3_blocks = re.finditer(r'resource\s+"aws_s3_bucket"\s+"([^"]+)"\s*{([^}]+)}', content, re.DOTALL)
                for match in s3_blocks:
                    resource_name = match.group(1)
                    resource_body = match.group(2)
                    
                    # Check for public ACL
                    if re.search(r'acl\s*=\s*"public', resource_body):
                        vuln = {
                            "id": "CKV_AWS_20",
                            "severity": "high",
                            "resource": f"aws_s3_bucket.{resource_name}",
                            "message": "S3 Bucket has an ACL defined which allows public access",
                            "remediation": "Set bucket ACL to 'private'",
                            "file": tf_file.name
                        }
                        if severity_levels[vuln["severity"]] >= min_severity:
                            security_scan["vulnerabilities"].append(vuln)
                            security_scan["summary"][vuln["severity"]] += 1
                    
                    # Check for missing encryption
                    if 'server_side_encryption_configuration' not in resource_body:
                        vuln = {
                            "id": "CKV_AWS_19",
                            "severity": "medium",
                            "resource": f"aws_s3_bucket.{resource_name}",
                            "message": "S3 bucket lacks server-side encryption",
                            "remediation": "Add server_side_encryption_configuration block",
                            "file": tf_file.name
                        }
                        if severity_levels[vuln["severity"]] >= min_severity:
                            security_scan["vulnerabilities"].append(vuln)
                            security_scan["summary"][vuln["severity"]] += 1
                
                # Check for open security groups
                sg_blocks = re.finditer(r'resource\s+"aws_security_group"\s+"([^"]+)"\s*{([^}]+)}', content, re.DOTALL)
                for match in sg_blocks:
                    resource_name = match.group(1)
                    resource_body = match.group(2)
                    
                    # Check for 0.0.0.0/0 in ingress
                    if re.search(r'cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"', resource_body):
                        vuln = {
                            "id": "CKV_AWS_24",
                            "severity": "high",
                            "resource": f"aws_security_group.{resource_name}",
                            "message": "Security group allows ingress from 0.0.0.0/0",
                            "remediation": "Restrict ingress to specific IP ranges",
                            "file": tf_file.name
                        }
                        if severity_levels[vuln["severity"]] >= min_severity:
                            security_scan["vulnerabilities"].append(vuln)
                            security_scan["summary"][vuln["severity"]] += 1
                
                # Check for unencrypted RDS instances
                rds_blocks = re.finditer(r'resource\s+"aws_db_instance"\s+"([^"]+)"\s*{([^}]+)}', content, re.DOTALL)
                for match in rds_blocks:
                    resource_name = match.group(1)
                    resource_body = match.group(2)
                    
                    if 'storage_encrypted' not in resource_body or re.search(r'storage_encrypted\s*=\s*false', resource_body):
                        vuln = {
                            "id": "CKV_AWS_16",
                            "severity": "high",
                            "resource": f"aws_db_instance.{resource_name}",
                            "message": "RDS instance is not encrypted",
                            "remediation": "Set storage_encrypted = true",
                            "file": tf_file.name
                        }
                        if severity_levels[vuln["severity"]] >= min_severity:
                            security_scan["vulnerabilities"].append(vuln)
                            security_scan["summary"][vuln["severity"]] += 1
                
                # Check for IAM policies with wildcards
                iam_policy_blocks = re.finditer(r'data\s+"aws_iam_policy_document"[^{]+{([^}]+)}', content, re.DOTALL)
                for match in iam_policy_blocks:
                    policy_body = match.group(1)
                    if re.search(r'actions\s*=\s*\[\s*"\*"', policy_body) or re.search(r'resources\s*=\s*\[\s*"\*"', policy_body):
                        vuln = {
                            "id": "CKV_AWS_1",
                            "severity": "medium",
                            "resource": "IAM Policy Document",
                            "message": "IAM policy uses wildcards (*) in actions or resources",
                            "remediation": "Use specific actions and resources instead of wildcards",
                            "file": tf_file.name
                        }
                        if severity_levels[vuln["severity"]] >= min_severity:
                            security_scan["vulnerabilities"].append(vuln)
                            security_scan["summary"][vuln["severity"]] += 1
        
        return {"security_scan": security_scan}
        
    except Exception as e:
        return {"error": f"Security scan failed: {str(e)}"}


@mcp.tool()
@validate_request("terry_recommendations")
def terry_recommendations(path: str, focus: str = "security") -> Dict[str, object]:
    """
    Get recommendations for Terraform configuration improvement.
    
    Args:
        path: Workspace path relative to /mnt/workspace
        focus: Area of focus (cost, security, performance, reliability)
    
    Returns:
        Recommendations based on the selected focus area
    """
    full_path = str(Path("/mnt/workspace") / path)
    
    if not os.path.exists(full_path):
        return {"error": f"Path {full_path} does not exist"}
    
    recommendations = {
        "focus": focus,
        "recommendations": [],
        "priority_actions": []
    }
    
    try:
        # Analyze configuration based on focus area
        for tf_file in Path(full_path).glob("*.tf"):
            with open(tf_file, 'r') as f:
                content = f.read()
                
                if focus == "security":
                    # Security recommendations
                    if 'aws_instance' in content and 'key_name' in content:
                        recommendations["recommendations"].append({
                            "category": "security",
                            "title": "Use Systems Manager Session Manager",
                            "description": "Replace SSH key access with AWS Systems Manager Session Manager for better security",
                            "impact": "high",
                            "effort": "medium"
                        })
                    
                    if not re.search(r'aws_kms_key', content) and ('aws_s3_bucket' in content or 'aws_db_instance' in content):
                        recommendations["recommendations"].append({
                            "category": "security",
                            "title": "Implement KMS encryption",
                            "description": "Use AWS KMS for encryption key management",
                            "impact": "high",
                            "effort": "low"
                        })
                    
                elif focus == "cost":
                    # Cost optimization recommendations
                    if 'aws_instance' in content and not re.search(r'instance_type\s*=\s*var', content):
                        recommendations["recommendations"].append({
                            "category": "cost",
                            "title": "Parameterize instance types",
                            "description": "Use variables for instance types to easily switch between environments",
                            "impact": "medium",
                            "effort": "low"
                        })
                    
                    if 'aws_instance' in content and 'spot_' not in content:
                        recommendations["recommendations"].append({
                            "category": "cost",
                            "title": "Consider Spot Instances",
                            "description": "Use Spot Instances for non-critical workloads to save up to 90%",
                            "impact": "high",
                            "effort": "medium"
                        })
                    
                elif focus == "performance":
                    # Performance recommendations
                    if 'aws_instance' in content and 'monitoring' not in content:
                        recommendations["recommendations"].append({
                            "category": "performance",
                            "title": "Enable detailed monitoring",
                            "description": "Enable CloudWatch detailed monitoring for better visibility",
                            "impact": "medium",
                            "effort": "low"
                        })
                    
                    if 'aws_alb' in content or 'aws_lb' in content:
                        if 'enable_http2' not in content:
                            recommendations["recommendations"].append({
                                "category": "performance",
                                "title": "Enable HTTP/2",
                                "description": "Enable HTTP/2 on load balancers for better performance",
                                "impact": "medium",
                                "effort": "low"
                            })
                
                elif focus == "reliability":
                    # Reliability recommendations
                    if 'aws_instance' in content and 'availability_zone' in content and 'count' not in content:
                        recommendations["recommendations"].append({
                            "category": "reliability",
                            "title": "Implement multi-AZ deployment",
                            "description": "Deploy instances across multiple availability zones",
                            "impact": "high",
                            "effort": "medium"
                        })
                    
                    if 'aws_db_instance' in content and 'backup_retention_period' not in content:
                        recommendations["recommendations"].append({
                            "category": "reliability",
                            "title": "Configure automated backups",
                            "description": "Set backup retention period for RDS instances",
                            "impact": "high",
                            "effort": "low"
                        })
        
        # Sort recommendations by impact
        recommendations["recommendations"].sort(key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x["impact"], 0), reverse=True)
        
        # Extract top 3 priority actions
        recommendations["priority_actions"] = [
            rec["title"] for rec in recommendations["recommendations"][:3]
        ]
        
        return {"recommendations": recommendations}
        
    except Exception as e:
        return {"error": f"Recommendations generation failed: {str(e)}"}


# ============================================================================
# TERRAFORM CLOUD TOOLS
# ============================================================================

@mcp.tool()
@validate_request("tf_cloud_list_workspaces")
def tf_cloud_list_workspaces(organization: str, limit: int = 20) -> Dict[str, object]:
    """
    List Terraform Cloud workspaces for an organization.
    
    Args:
        organization: Terraform Cloud organization name
        limit: Maximum number of workspaces to return (default: 20, max: 100)
    
    Returns:
        List of workspaces with metadata
    """
    # Validate inputs
    if not organization or not re.match(r'^[a-zA-Z0-9_-]+$', organization):
        return {"error": "Invalid organization name"}
    
    if limit < 1 or limit > 100:
        return {"error": "Limit must be between 1 and 100"}
    
    try:
        # Check for TF Cloud token
        token = os.environ.get("TF_CLOUD_TOKEN")
        if not token:
            return {"error": "Terraform Cloud token not configured. Set TF_CLOUD_TOKEN environment variable"}
        
        # Mock implementation - in production, this would call TF Cloud API
        # For now, return example structure as documented
        return {
            "workspaces": [
                {
                    "id": f"ws-example-{i}",
                    "name": f"{organization}-workspace-{i}",
                    "environment": "production" if i == 1 else "development",
                    "terraform_version": "1.6.5",
                    "current_run": {
                        "id": f"run-example-{i}",
                        "status": "applied" if i % 2 == 0 else "planned",
                        "created_at": "2024-01-15T10:30:00Z"
                    },
                    "resource_count": 42 + i * 10,
                    "auto_apply": i == 1
                }
                for i in range(1, min(limit + 1, 4))  # Return max 3 example workspaces
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list TF Cloud workspaces: {e}")
        return {"error": f"Failed to list workspaces: {str(e)}"}


@mcp.tool()
@validate_request("tf_cloud_get_workspace")
def tf_cloud_get_workspace(organization: str, workspace: str) -> Dict[str, object]:
    """
    Get detailed information about a specific Terraform Cloud workspace.
    
    Args:
        organization: Terraform Cloud organization name
        workspace: Workspace name
    
    Returns:
        Detailed workspace information
    """
    # Validate inputs
    if not organization or not re.match(r'^[a-zA-Z0-9_-]+$', organization):
        return {"error": "Invalid organization name"}
    
    if not workspace or not re.match(r'^[a-zA-Z0-9_-]+$', workspace):
        return {"error": "Invalid workspace name"}
    
    try:
        # Check for TF Cloud token
        token = os.environ.get("TF_CLOUD_TOKEN")
        if not token:
            return {"error": "Terraform Cloud token not configured"}
        
        # Mock implementation
        return {
            "workspace": {
                "id": f"ws-{workspace}",
                "name": workspace,
                "organization": organization,
                "environment": "production",
                "terraform_version": "1.6.5",
                "auto_apply": False,
                "execution_mode": "remote",
                "working_directory": "",
                "vcs_repo": {
                    "identifier": f"{organization}/infrastructure",
                    "branch": "main",
                    "oauth_token_id": "ot-example"
                },
                "current_state_version": {
                    "id": "sv-example",
                    "serial": 42,
                    "state_version": 42,
                    "created_at": "2024-01-15T10:00:00Z"
                },
                "resource_count": 75,
                "tags": ["production", "aws", "managed"]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get TF Cloud workspace: {e}")
        return {"error": f"Failed to get workspace: {str(e)}"}


@mcp.tool()
@validate_request("tf_cloud_list_runs")
def tf_cloud_list_runs(organization: str, workspace: str, limit: int = 10) -> Dict[str, object]:
    """
    List runs for a Terraform Cloud workspace.
    
    Args:
        organization: Terraform Cloud organization name
        workspace: Workspace name
        limit: Maximum number of runs to return (default: 10)
    
    Returns:
        List of runs with status and metadata
    """
    # Validate inputs
    if not organization or not re.match(r'^[a-zA-Z0-9_-]+$', organization):
        return {"error": "Invalid organization name"}
    
    if not workspace or not re.match(r'^[a-zA-Z0-9_-]+$', workspace):
        return {"error": "Invalid workspace name"}
    
    if limit < 1 or limit > 100:
        return {"error": "Limit must be between 1 and 100"}
    
    try:
        # Check for TF Cloud token
        token = os.environ.get("TF_CLOUD_TOKEN")
        if not token:
            return {"error": "Terraform Cloud token not configured"}
        
        # Mock implementation
        statuses = ["applied", "planned", "planning", "applying", "errored", "canceled"]
        return {
            "runs": [
                {
                    "id": f"run-{i}",
                    "status": statuses[i % len(statuses)],
                    "created_at": f"2024-01-{15-i:02d}T{10+i}:00:00Z",
                    "message": f"Run triggered by API - commit {i}",
                    "is_destroy": False,
                    "has_changes": i % 2 == 0,
                    "resource_additions": i * 2,
                    "resource_changes": i,
                    "resource_destructions": 0,
                    "cost_estimation": {
                        "enabled": True,
                        "delta": f"+${i * 10}.00",
                        "monthly": f"${100 + i * 10}.00"
                    } if i % 3 == 0 else None
                }
                for i in range(1, min(limit + 1, 6))
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list TF Cloud runs: {e}")
        return {"error": f"Failed to list runs: {str(e)}"}


@mcp.tool()
@validate_request("tf_cloud_get_state_outputs")
def tf_cloud_get_state_outputs(organization: str, workspace: str) -> Dict[str, object]:
    """
    Get state outputs from a Terraform Cloud workspace.
    
    Args:
        organization: Terraform Cloud organization name
        workspace: Workspace name
    
    Returns:
        Current state outputs with values and metadata
    """
    # Validate inputs
    if not organization or not re.match(r'^[a-zA-Z0-9_-]+$', organization):
        return {"error": "Invalid organization name"}
    
    if not workspace or not re.match(r'^[a-zA-Z0-9_-]+$', workspace):
        return {"error": "Invalid workspace name"}
    
    try:
        # Check for TF Cloud token
        token = os.environ.get("TF_CLOUD_TOKEN")
        if not token:
            return {"error": "Terraform Cloud token not configured"}
        
        # Mock implementation
        return {
            "outputs": {
                "vpc_id": {
                    "value": "vpc-12345678",
                    "type": "string",
                    "sensitive": False
                },
                "subnet_ids": {
                    "value": ["subnet-12345", "subnet-67890"],
                    "type": "list(string)",
                    "sensitive": False
                },
                "database_endpoint": {
                    "value": "[SENSITIVE]",
                    "type": "string",
                    "sensitive": True
                },
                "load_balancer_dns": {
                    "value": "lb-example.us-east-1.elb.amazonaws.com",
                    "type": "string",
                    "sensitive": False
                },
                "instance_count": {
                    "value": 3,
                    "type": "number",
                    "sensitive": False
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get TF Cloud state outputs: {e}")
        return {"error": f"Failed to get state outputs: {str(e)}"}


# ============================================================================
# GITHUB INTEGRATION TOOLS
# ============================================================================

# Import GitHub integration modules
try:
    spec_github_auth = importlib.util.spec_from_file_location(
        "github_app_auth", "./github_app_auth.py"
    )
    github_app_auth = importlib.util.module_from_spec(spec_github_auth)
    spec_github_auth.loader.exec_module(github_app_auth)
    
    spec_github_handler = importlib.util.spec_from_file_location(
        "github_repo_handler", "./github_repo_handler.py"
    )
    github_repo_handler = importlib.util.module_from_spec(spec_github_handler)
    spec_github_handler.loader.exec_module(github_repo_handler)
    
    # Initialize GitHub auth and handler
    github_auth = None
    github_handler = None
    
    try:
        github_config = github_app_auth.GitHubAppConfig.from_env()
        github_auth = github_app_auth.GitHubAppAuth(github_config)
        github_handler = github_repo_handler.GitHubRepoHandler(github_auth)
    except Exception as e:
        print(f"GitHub integration not configured: {e}")
        
except Exception as e:
    print(f"Failed to load GitHub integration: {e}")
    github_handler = None


@mcp.tool()
@validate_request("github_clone_repo")
async def github_clone_repo(
    owner: str, repo: str, branch: Optional[str] = None, force: bool = False
) -> Dict[str, object]:
    """
    Clone or update a GitHub repository into the workspace.
    
    Args:
        owner: Repository owner/organization
        repo: Repository name
        branch: Branch to clone (optional)
        force: Force update if exists
    
    Returns:
        Repository clone status and workspace path
    """
    if not github_handler:
        return {"error": "GitHub integration not configured. Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY"}
    
    try:
        result = await github_handler.clone_or_update_repo(owner, repo, branch, force)
        return result
    except Exception as e:
        return {"error": f"Failed to clone repository: {str(e)}"}


@mcp.tool()
@validate_request("github_list_terraform_files")
async def github_list_terraform_files(
    owner: str, repo: str, path: str = "", pattern: str = "*.tf"
) -> Dict[str, object]:
    """
    List Terraform files in a GitHub repository.
    
    Args:
        owner: Repository owner/organization
        repo: Repository name
        path: Subdirectory path (optional)
        pattern: File pattern (default: "*.tf")
    
    Returns:
        List of Terraform files with metadata
    """
    if not github_handler:
        return {"error": "GitHub integration not configured"}
    
    try:
        result = await github_handler.list_terraform_files(owner, repo, path, pattern)
        return result
    except Exception as e:
        return {"error": f"Failed to list files: {str(e)}"}


@mcp.tool()
@validate_request("github_get_terraform_config")
async def github_get_terraform_config(
    owner: str, repo: str, config_path: str
) -> Dict[str, object]:
    """
    Analyze Terraform configuration in a GitHub repository.
    
    Args:
        owner: Repository owner/organization
        repo: Repository name
        config_path: Path to Terraform configuration
    
    Returns:
        Configuration analysis including providers, modules, and structure
    """
    if not github_handler:
        return {"error": "GitHub integration not configured"}
    
    try:
        result = await github_handler.get_terraform_config(owner, repo, config_path)
        return result
    except Exception as e:
        return {"error": f"Failed to analyze config: {str(e)}"}


@mcp.tool()
@validate_request("github_prepare_workspace")
async def github_prepare_workspace(
    owner: str, repo: str, config_path: str, workspace_name: Optional[str] = None
) -> Dict[str, object]:
    """
    Prepare a Terraform workspace from a GitHub repository.
    
    Args:
        owner: Repository owner/organization
        repo: Repository name
        config_path: Path to Terraform configuration in repo
        workspace_name: Custom workspace name (optional)
    
    Returns:
        Workspace preparation status and path
    """
    if not github_handler:
        return {"error": "GitHub integration not configured"}
    
    try:
        result = await github_handler.prepare_terraform_workspace(
            owner, repo, config_path, workspace_name
        )
        return result
    except Exception as e:
        return {"error": f"Failed to prepare workspace: {str(e)}"}


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
