#!/usr/bin/env python3
"""
Terry-Form MCP HTTP Server - Fixed version
Uses FastMCP with proper HTTP endpoints
"""
import os
import sys
import logging
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from fastmcp import FastMCP
from auth_manager import auth_manager
from ai_service import ai_service

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
def terraform_init(path: str) -> str:
    """
    Initialize a Terraform working directory
    
    Args:
        path: Path relative to workspace root
        
    Returns:
        JSON string with operation result
    """
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Path {path} does not exist in workspace"})
    
    result = run_terraform_command(full_path, "init")
    return json.dumps({"terraform_init": result})

@mcp.tool()
def terraform_validate(path: str) -> str:
    """
    Validate Terraform configuration files
    
    Args:
        path: Path relative to workspace root
        
    Returns:
        JSON string with validation result
    """
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Path {path} does not exist in workspace"})
    
    result = run_terraform_command(full_path, "validate")
    return json.dumps({"terraform_validate": result})

@mcp.tool()
def terraform_fmt(path: str) -> str:
    """
    Check Terraform configuration formatting
    
    Args:
        path: Path relative to workspace root
        
    Returns:
        JSON string with format check result
    """
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Path {path} does not exist in workspace"})
    
    result = run_terraform_command(full_path, "fmt")
    return json.dumps({"terraform_fmt": result})

@mcp.tool()
def terraform_plan(
    path: str,
    vars: Optional[Dict[str, str]] = None
) -> str:
    """
    Create a Terraform execution plan
    
    Args:
        path: Path relative to workspace root
        vars: Optional dictionary of Terraform variables
        
    Returns:
        JSON string with plan result
    """
    full_path = str(Path(WORKSPACE_ROOT) / path)
    
    if not os.path.exists(full_path):
        return json.dumps({"error": f"Path {path} does not exist in workspace"})
    
    result = run_terraform_command(full_path, "plan", vars)
    return json.dumps({"terraform_plan": result})

@mcp.tool()
def terraform_version() -> str:
    """
    Get Terraform version information
    
    Returns:
        JSON string with version info
    """
    result = run_terraform_command(os.getcwd(), "version")
    return json.dumps({"terraform_version": result})

@mcp.tool()
def workspace_list() -> str:
    """
    List contents of the workspace directory
    
    Returns:
        JSON string with workspace contents
    """
    try:
        items = []
        for item in Path(WORKSPACE_ROOT).iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "path": str(item.relative_to(WORKSPACE_ROOT))
            })
        return json.dumps({"workspace_list": {"items": items, "count": len(items)}})
    except Exception as e:
        return json.dumps({"error": f"Failed to list workspace: {str(e)}"})

@mcp.tool()
def workspace_info(path: str) -> str:
    """
    Get information about a specific workspace path
    
    Args:
        path: Path relative to workspace root
        
    Returns:
        JSON string with path information
    """
    full_path = Path(WORKSPACE_ROOT) / path
    
    if not full_path.exists():
        return json.dumps({"error": f"Path {path} does not exist"})
    
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
    
    return json.dumps({"workspace_info": info})

@mcp.tool()
def auth_status() -> str:
    """
    Get authentication status for GitHub and Azure
    
    Returns:
        JSON string with authentication status
    """
    status = auth_manager.get_auth_status()
    return json.dumps({"auth_status": status})

@mcp.tool()
def ai_status() -> str:
    """
    Get AI service status and configuration
    
    Returns:
        JSON string with AI service status
    """
    status = ai_service.get_ai_status()
    return json.dumps({"ai_status": status})

@mcp.tool()
async def ai_analyze_terraform(code: str, context: str = "") -> str:
    """
    Analyze Terraform code using AI and provide insights
    
    Args:
        code: Terraform code to analyze
        context: Additional context about the infrastructure
        
    Returns:
        JSON string with AI analysis results
    """
    try:
        result = await ai_service.analyze_terraform_code(code, context)
        return json.dumps({"ai_analysis": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
async def ai_generate_terraform(requirements: str, provider: str = "aws") -> str:
    """
    Generate Terraform code based on requirements using AI
    
    Args:
        requirements: Description of infrastructure requirements
        provider: Cloud provider (aws, azure, gcp)
        
    Returns:
        JSON string with generated Terraform code
    """
    try:
        result = await ai_service.generate_terraform_code(requirements, provider)
        return json.dumps({"ai_generated": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
async def ai_explain_resources(resources_text: str) -> str:
    """
    Explain Terraform resources using AI
    
    Args:
        resources_text: Terraform resources to explain (newline separated)
        
    Returns:
        JSON string with resource explanations
    """
    try:
        resources = [r.strip() for r in resources_text.split('\n') if r.strip()]
        result = await ai_service.explain_terraform_resources(resources)
        return json.dumps({"ai_explanations": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
async def ai_suggest_improvements(code: str, goals: str = "") -> str:
    """
    Get AI suggestions for improving Terraform code
    
    Args:
        code: Current Terraform code
        goals: Improvement goals (optional)
        
    Returns:
        JSON string with improvement suggestions
    """
    try:
        result = await ai_service.suggest_improvements(code, goals)
        return json.dumps({"ai_suggestions": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def clone_repository(repo_url: str, target_dir: Optional[str] = None, branch: Optional[str] = None) -> str:
    """
    Clone a git repository into the workspace
    
    Args:
        repo_url: GitHub repository URL (e.g. https://github.com/user/repo)
        target_dir: Optional target directory name (defaults to repo name)
        branch: Optional specific branch to clone (defaults to default branch)
        
    Returns:
        JSON string with operation result
    """
    # Extract repo name if target_dir not provided
    if not target_dir:
        target_dir = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    
    target_path = Path(WORKSPACE_ROOT) / target_dir
    
    # Check if already exists
    if target_path.exists():
        return json.dumps({
            "success": False,
            "error": f"Directory {target_dir} already exists",
            "path": str(target_path.relative_to(WORKSPACE_ROOT))
        })
    
    try:
        # Build clone command
        clone_cmd = ["git", "clone"]
        if branch:
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([repo_url, str(target_path)])
        
        # Clone the repository
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            # List terraform files
            tf_files = list(target_path.glob("**/*.tf"))
            
            return json.dumps({
                "success": True,
                "message": f"Successfully cloned {repo_url}",
                "path": target_dir,
                "terraform_files": [str(f.relative_to(target_path)) for f in tf_files[:10]],
                "total_tf_files": len(tf_files)
            })
        else:
            return json.dumps({
                "success": False,
                "error": result.stderr,
                "stdout": result.stdout
            })
            
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Clone operation timed out after 60 seconds"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def create_terraform_file(path: str, filename: str, content: str) -> str:
    """
    Create a Terraform file in the workspace
    
    Args:
        path: Directory path relative to workspace root
        filename: Name of the file to create (should end with .tf)
        content: Content of the Terraform file
        
    Returns:
        JSON string with operation result
    """
    full_dir = Path(WORKSPACE_ROOT) / path
    full_path = full_dir / filename
    
    try:
        # Create directory if it doesn't exist
        full_dir.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        full_path.write_text(content)
        
        return json.dumps({
            "success": True,
            "path": str(full_path.relative_to(WORKSPACE_ROOT)),
            "message": f"Created {filename} successfully"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def git_commit(path: str, message: str, add_all: bool = True) -> str:
    """
    Commit changes in a git repository
    
    Args:
        path: Path relative to workspace root (must be a git repository)
        message: Commit message
        add_all: Whether to add all changes before committing (default: True)
        
    Returns:
        JSON string with operation result
    """
    full_path = Path(WORKSPACE_ROOT) / path
    
    if not full_path.exists():
        return json.dumps({"success": False, "error": f"Path {path} does not exist"})
    
    if not (full_path / ".git").exists():
        return json.dumps({"success": False, "error": f"Path {path} is not a git repository"})
    
    try:
        # Add files if requested
        if add_all:
            add_result = subprocess.run(
                ["git", "add", "-A"],
                cwd=str(full_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            if add_result.returncode != 0:
                return json.dumps({
                    "success": False,
                    "error": f"Failed to add files: {add_result.stderr}"
                })
        
        # Check if there are changes to commit
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(full_path),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if not status_result.stdout.strip():
            return json.dumps({
                "success": False,
                "error": "No changes to commit"
            })
        
        # Commit changes
        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(full_path),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if commit_result.returncode == 0:
            return json.dumps({
                "success": True,
                "message": "Changes committed successfully",
                "commit_hash": commit_result.stdout.strip().split()[1] if commit_result.stdout else None
            })
        else:
            return json.dumps({
                "success": False,
                "error": commit_result.stderr
            })
            
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Git commit operation timed out"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def git_push(path: str, remote: str = "origin", branch: Optional[str] = None) -> str:
    """
    Push changes to remote repository
    
    Args:
        path: Path relative to workspace root (must be a git repository)
        remote: Remote name (default: origin)
        branch: Branch name (defaults to current branch)
        
    Returns:
        JSON string with operation result
    """
    full_path = Path(WORKSPACE_ROOT) / path
    
    if not full_path.exists():
        return json.dumps({"success": False, "error": f"Path {path} does not exist"})
    
    if not (full_path / ".git").exists():
        return json.dumps({"success": False, "error": f"Path {path} is not a git repository"})
    
    try:
        # Get current branch if not specified
        if not branch:
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(full_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            if branch_result.returncode == 0:
                branch = branch_result.stdout.strip()
            else:
                return json.dumps({
                    "success": False,
                    "error": "Failed to determine current branch"
                })
        
        # Push to remote
        push_result = subprocess.run(
            ["git", "push", remote, branch],
            cwd=str(full_path),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if push_result.returncode == 0:
            return json.dumps({
                "success": True,
                "message": f"Successfully pushed to {remote}/{branch}",
                "output": push_result.stderr  # Git push output goes to stderr
            })
        else:
            return json.dumps({
                "success": False,
                "error": push_result.stderr
            })
            
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Git push operation timed out"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.tool()
def git_status(path: str) -> str:
    """
    Get git status of a repository
    
    Args:
        path: Path relative to workspace root (must be a git repository)
        
    Returns:
        JSON string with git status information
    """
    full_path = Path(WORKSPACE_ROOT) / path
    
    if not full_path.exists():
        return json.dumps({"error": f"Path {path} does not exist"})
    
    if not (full_path / ".git").exists():
        return json.dumps({"error": f"Path {path} is not a git repository"})
    
    try:
        # Get status
        status_result = subprocess.run(
            ["git", "status", "--porcelain", "-b"],
            cwd=str(full_path),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(full_path),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Get last commit
        commit_result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=str(full_path),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return json.dumps({
            "git_status": {
                "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else None,
                "status": status_result.stdout,
                "last_commit": commit_result.stdout.strip() if commit_result.returncode == 0 else None,
                "has_changes": bool(status_result.stdout.strip())
            }
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})

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
        
        # Configure authentication
        auth_manager.configure_git_auth()
        
        # Create a test directory with sample Terraform file
        test_dir = Path(WORKSPACE_ROOT) / "test"
        test_dir.mkdir(exist_ok=True)
        
        sample_tf = test_dir / "main.tf"
        if not sample_tf.exists():
            sample_tf.write_text('''
terraform {
  required_version = ">= 1.0"
}

resource "null_resource" "example" {
  provisioner "local-exec" {
    command = "echo 'Hello from Terry-Form MCP!'"
  }
}

variable "environment" {
  type        = string
  description = "Environment name"
  default     = "development"
}

output "message" {
  value = "Terry-Form MCP is working!"
}
''')
            logger.info("Created sample Terraform configuration in test/main.tf")
        
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