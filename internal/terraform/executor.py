"""
Terraform Executor for Terry-Form MCP v3.0.0
Enhanced version of the Terraform execution logic
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Define workspace root
WORKSPACE_ROOT = "/mnt/workspace"


class TerraformExecutor:
    """Enhanced Terraform executor with async support"""
    
    def __init__(self, workspace_root: str = WORKSPACE_ROOT):
        self.workspace_root = workspace_root
        self.allowed_actions = [
            "init", "validate", "fmt", "plan", "show", 
            "graph", "providers", "version"
        ]
        # Security: explicitly disallow destructive operations
        self.disallowed_actions = ["apply", "destroy", "import"]
    
    def build_var_args(self, vars_dict: Dict[str, str]) -> List[str]:
        """Build variable arguments for Terraform commands"""
        args = []
        for key, val in vars_dict.items():
            args += ["-var", f"{key}={val}"]
        return args
    
    async def execute_terraform(
        self, 
        action: str, 
        path: Path, 
        extra_args: Optional[List[str]] = None,
        vars_dict: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Execute Terraform command asynchronously"""
        
        # Security check
        if action in self.disallowed_actions:
            return {
                "success": False,
                "exit_code": 1,
                "output": "",
                "error": f"Action '{action}' is not allowed for security reasons"
            }
        
        if action not in self.allowed_actions:
            return {
                "success": False,
                "exit_code": 1,
                "output": "",
                "error": f"Unknown action '{action}'"
            }
        
        # Build command
        cmd = self._build_command(action, extra_args, vars_dict)
        
        # Execute command
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "output": stdout.decode('utf-8', errors='replace'),
                "error": stderr.decode('utf-8', errors='replace')
            }
            
        except Exception as e:
            logger.exception(f"Error executing terraform {action}")
            return {
                "success": False,
                "exit_code": -1,
                "output": "",
                "error": str(e)
            }
    
    def _build_command(
        self, 
        action: str, 
        extra_args: Optional[List[str]] = None,
        vars_dict: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """Build the Terraform command"""
        base_cmds = {
            "init": ["terraform", "init", "-input=false"],
            "validate": ["terraform", "validate"],
            "fmt": ["terraform", "fmt", "-check", "-recursive"],
            "version": ["terraform", "version"],
            "providers": ["terraform", "providers"],
            "show": ["terraform", "show"],
            "graph": ["terraform", "graph"]
        }
        
        if action == "plan":
            cmd = ["terraform", "plan", "-input=false", "-no-color"]
            if vars_dict:
                cmd += self.build_var_args(vars_dict)
        elif action in base_cmds:
            cmd = base_cmds[action]
        else:
            cmd = ["terraform", action]
        
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd
    
    def run_terraform(self, path: str, action: str, vars_dict: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Synchronous wrapper for backward compatibility"""
        # This is the original synchronous function for compatibility
        base_cmds = {
            "init": ["terraform", "init", "-input=false"],
            "validate": ["terraform", "validate"],
            "fmt": ["terraform", "fmt", "-check", "-recursive"],
        }

        if action == "plan":
            cmd = ["terraform", "plan", "-input=false", "-no-color"]
            if vars_dict:
                cmd += self.build_var_args(vars_dict)
        elif action in base_cmds:
            cmd = base_cmds[action]
        else:
            return {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Unknown action: {action}",
                "raw_result": {}
            }

        try:
            result = subprocess.run(
                cmd, 
                cwd=path, 
                capture_output=True, 
                text=True, 
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "raw_result": {
                    "action": action,
                    "path": path,
                    "command": " ".join(cmd),
                    "returncode": result.returncode
                }
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timed out after 300 seconds",
                "raw_result": {"action": action, "path": path, "error": "timeout"}
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e),
                "raw_result": {"action": action, "path": path, "error": str(e)}
            }