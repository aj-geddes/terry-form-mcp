#!/usr/bin/env python3
"""
Git clone tool for Terry-Form MCP
Adds ability to clone repositories into the workspace
"""
import subprocess
import os
from pathlib import Path

def clone_repository(repo_url: str, target_dir: str = None) -> dict:
    """
    Clone a git repository into the workspace
    
    Args:
        repo_url: GitHub repository URL
        target_dir: Optional target directory name (defaults to repo name)
    
    Returns:
        Dict with operation result
    """
    workspace_root = "/mnt/workspace"
    
    # Extract repo name if target_dir not provided
    if not target_dir:
        target_dir = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    
    target_path = Path(workspace_root) / target_dir
    
    # Check if already exists
    if target_path.exists():
        return {
            "success": False,
            "error": f"Directory {target_dir} already exists",
            "path": str(target_path)
        }
    
    try:
        # Clone the repository
        result = subprocess.run(
            ["git", "clone", repo_url, str(target_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # List the contents
            files = list(target_path.glob("**/*.tf"))
            
            return {
                "success": True,
                "message": f"Successfully cloned {repo_url}",
                "path": target_dir,
                "terraform_files": [str(f.relative_to(target_path)) for f in files[:10]],
                "total_files": len(files)
            }
        else:
            return {
                "success": False,
                "error": result.stderr,
                "stdout": result.stdout
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Clone operation timed out after 60 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Add to server_http_fixed.py
if __name__ == "__main__":
    # Test with a sample repo
    result = clone_repository("https://github.com/terraform-aws-modules/terraform-aws-vpc")
    print(result)