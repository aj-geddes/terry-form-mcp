#!/usr/bin/env python3
"""
Terry-Form MCP HTTP Server - Simplified version
Uses FastMCP's streamable-http transport
"""
import os
import sys
import logging
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Terry-Form MCP v3.0.0")

# Workspace root
WORKSPACE_ROOT = "/mnt/workspace"

def build_var_args(vars_dict):
    """Build terraform variable arguments"""
    args = []
    for key, val in vars_dict.items():
        args += ["-var", f"{key}={val}"]
    return args

def run_terraform_command(path, action, vars_dict=None):
    """Execute terraform command"""
    base_cmds = {
        "init": ["terraform", "init", "-input=false"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt", "-check", "-recursive"],
        "version": ["terraform", "version"],
    }

    if action == "plan":
        cmd = ["terraform", "plan", "-input=false", "-no-color"]
        if vars_dict:
            cmd += build_var_args(vars_dict)
    elif action in base_cmds:
        cmd = base_cmds[action]
    else:
        return {
            "success": False,
            "action": action,
            "error": f"Unsupported action '{action}'"
        }

    try:
        result = subprocess.run(cmd, cwd=path, capture_output=True, text=True, timeout=300)
        return {
            "success": result.returncode == 0,
            "action": action,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "action": action,
            "error": "Command timed out after 300 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "action": action,
            "error": str(e)
        }

@mcp.tool()
def terraform_init(path: str) -> Dict[str, object]:
    """Initialize a Terraform working directory"""
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return {"error": f"Path {path} does not exist in workspace"}
    
    result = run_terraform_command(full_path, "init")
    return {"terraform_init": result}

@mcp.tool()
def terraform_validate(path: str) -> Dict[str, object]:
    """Validate Terraform configuration files"""
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return {"error": f"Path {path} does not exist in workspace"}
    
    result = run_terraform_command(full_path, "validate")
    return {"terraform_validate": result}

@mcp.tool()
def terraform_fmt(path: str) -> Dict[str, object]:
    """Check Terraform configuration formatting"""
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return {"error": f"Path {path} does not exist in workspace"}
    
    result = run_terraform_command(full_path, "fmt")
    return {"terraform_fmt": result}

@mcp.tool()
def terraform_plan(
    path: str,
    vars: Optional[Dict[str, str]] = None
) -> Dict[str, object]:
    """Create a Terraform execution plan"""
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return {"error": f"Path {path} does not exist in workspace"}
    
    result = run_terraform_command(full_path, "plan", vars)
    return {"terraform_plan": result}

@mcp.tool()
def terraform_version() -> Dict[str, object]:
    """Get Terraform version information"""
    result = run_terraform_command(os.getcwd(), "version")
    return {"terraform_version": result}

@mcp.tool()
def workspace_list() -> Dict[str, object]:
    """List contents of the workspace directory"""
    try:
        items = []
        for item in Path(WORKSPACE_ROOT).iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "path": str(item.relative_to(WORKSPACE_ROOT))
            })
        return {"workspace_list": {"items": items, "count": len(items)}}
    except Exception as e:
        return {"error": f"Failed to list workspace: {str(e)}"}

@mcp.tool()
def workspace_info(path: str) -> Dict[str, object]:
    """Get information about a specific workspace path"""
    full_path = Path(WORKSPACE_ROOT) / path
    
    if not full_path.exists():
        return {"error": f"Path {path} does not exist"}
    
    info = {
        "path": path,
        "full_path": str(full_path),
        "exists": True,
        "is_directory": full_path.is_dir(),
        "is_file": full_path.is_file()
    }
    
    if full_path.is_dir():
        try:
            tf_files = list(full_path.glob("*.tf"))
            info["terraform_files"] = [f.name for f in tf_files]
            info["has_terraform"] = len(tf_files) > 0
        except:
            info["terraform_files"] = []
            info["has_terraform"] = False
    
    return {"workspace_info": info}

# Add health endpoints for Kubernetes using custom routes
@mcp.custom_route(method="GET", path="/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "version": "v3.0.0-http"}

@mcp.custom_route(method="GET", path="/ready")
async def ready():
    """Readiness check endpoint"""
    # Check if terraform is available
    try:
        result = subprocess.run(["terraform", "version"], capture_output=True, timeout=5)
        terraform_ready = result.returncode == 0
    except:
        terraform_ready = False
    
    return {
        "status": "ready" if terraform_ready else "not_ready",
        "terraform": terraform_ready,
        "version": "v3.0.0-http"
    }

def main():
    """Main entry point"""
    try:
        # Get configuration from environment
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        
        logger.info(f"Starting Terry-Form MCP HTTP Server on {host}:{port}")
        logger.info(f"Workspace root: {WORKSPACE_ROOT}")
        
        # Create workspace directory if it doesn't exist
        Path(WORKSPACE_ROOT).mkdir(parents=True, exist_ok=True)
        
        # Run with streamable-http transport
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port
        )
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()