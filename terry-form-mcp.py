#!/usr/bin/env python3
"""
Terry-Form MCP Core Execution Module
Executes Terraform operations with comprehensive security hardening.

Security hardened:
- Safe subprocess execution (shell=False)
- Timeout enforcement
- Controlled environment variables
- No interactive prompts
"""

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Environment variables to pass through to Terraform
ALLOWED_ENV_VARS = {
    "HOME",
    "PATH",
    "USER",
    "TF_LOG",
    "TF_LOG_PATH",
    "TF_CLI_ARGS",
    # AWS credentials
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_DEFAULT_REGION",
    "AWS_REGION",
    "AWS_PROFILE",
    # Google Cloud credentials
    "GOOGLE_CREDENTIALS",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_PROJECT",
    "GOOGLE_REGION",
    "GOOGLE_ZONE",
    # Azure credentials
    "ARM_CLIENT_ID",
    "ARM_CLIENT_SECRET",
    "ARM_SUBSCRIPTION_ID",
    "ARM_TENANT_ID",
    # Terraform Cloud
    "TF_TOKEN_app_terraform_io",
    "TERRAFORM_CLOUD_TOKEN",
}

# Environment variables to force for automation
FORCED_ENV_VARS = {
    "TF_IN_AUTOMATION": "true",
    "TF_INPUT": "false",
    "CHECKPOINT_DISABLE": "true",
}


def get_controlled_env() -> Dict[str, str]:
    """Build a controlled environment for Terraform execution."""
    env = {}

    # Copy allowed variables from current environment
    for var in ALLOWED_ENV_VARS:
        if var in os.environ:
            env[var] = os.environ[var]

    # Apply forced variables
    env.update(FORCED_ENV_VARS)

    return env


def build_terraform_command(
    action: str, vars: Optional[Dict[str, Any]] = None, var_file: Optional[str] = None
) -> list:
    """Build Terraform command with appropriate flags for each action."""
    base_cmd = ["terraform"]

    if action == "init":
        return base_cmd + ["init", "-input=false", "-no-color"]

    elif action == "validate":
        return base_cmd + ["validate", "-no-color"]

    elif action == "fmt":
        return base_cmd + ["fmt", "-check", "-diff", "-no-color"]

    elif action == "plan":
        cmd = base_cmd + ["plan", "-input=false", "-no-color", "-out=tfplan"]
        if var_file:
            cmd.extend(["-var-file", var_file])
        return cmd

    elif action == "show":
        return base_cmd + ["show", "-json", "-no-color"]

    elif action == "graph":
        return base_cmd + ["graph"]

    elif action == "providers":
        return base_cmd + ["providers"]

    elif action == "version":
        return base_cmd + ["version", "-json"]

    else:
        # Fallback for unknown actions (should be caught by validator)
        return base_cmd + [action, "-no-color"]


def parse_plan_output(path: str) -> Optional[Dict[str, Any]]:
    """Parse Terraform plan output to extract summary."""
    plan_file = Path(path) / "tfplan"

    if not plan_file.exists():
        return None

    try:
        # Use terraform show to get JSON representation of plan
        result = subprocess.run(
            ["terraform", "show", "-json", str(plan_file)],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=60,
            env=get_controlled_env(),
        )

        if result.returncode != 0:
            logger.warning(f"Failed to parse plan: {result.stderr}")
            return None

        plan_data = json.loads(result.stdout)

        # Extract resource changes
        resource_changes = plan_data.get("resource_changes", [])

        add_count = 0
        change_count = 0
        destroy_count = 0
        resources = []

        for change in resource_changes:
            actions = change.get("change", {}).get("actions", [])
            resource_info = {
                "address": change.get("address", ""),
                "type": change.get("type", ""),
                "name": change.get("name", ""),
                "actions": actions,
            }
            resources.append(resource_info)

            if "create" in actions:
                add_count += 1
            if "update" in actions:
                change_count += 1
            if "delete" in actions:
                destroy_count += 1

        return {
            "plan_summary": {
                "add": add_count,
                "change": change_count,
                "destroy": destroy_count,
            },
            "resources": resources,
        }

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse plan JSON: {e}")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Plan parsing timed out")
        return None
    except Exception as e:
        logger.warning(f"Error parsing plan: {e}")
        return None


def parse_text_plan_summary(stdout: str) -> Dict[str, int]:
    """Fallback: Parse plan summary from text output."""
    summary = {"add": 0, "change": 0, "destroy": 0}

    patterns = {
        "add": r"(\d+) to add",
        "change": r"(\d+) to change",
        "destroy": r"(\d+) to destroy",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, stdout)
        if match:
            summary[key] = int(match.group(1))

    return summary


def run_terraform(
    path: str, action: str, vars: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Execute a Terraform action with security hardening.

    Args:
        path: Full path to Terraform workspace directory
        action: Terraform action to execute (init, validate, plan, etc.)
        vars: Optional dictionary of Terraform variables (for plan action)

    Returns:
        Dictionary with execution results:
        - action: The action that was executed
        - success: Whether the action succeeded
        - exit_code: Terraform exit code
        - stdout: Standard output
        - stderr: Standard error
        - duration: Execution time in seconds
        - plan_summary: (for plan action) Summary of changes
        - resources: (for plan action) List of affected resources
    """
    # Get timeout from environment or use default
    timeout = int(os.environ.get("MAX_OPERATION_TIMEOUT", 300))

    # Validate path exists
    workspace_path = Path(path)
    if not workspace_path.exists():
        return {
            "action": action,
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Workspace path does not exist: {path}",
            "duration": 0.0,
        }

    if not workspace_path.is_dir():
        return {
            "action": action,
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Workspace path is not a directory: {path}",
            "duration": 0.0,
        }

    # Handle variables for plan action
    var_file_path = None
    temp_var_file = None

    try:
        if action == "plan" and vars:
            # Create temporary var file for complex variable handling
            temp_var_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".tfvars.json", dir=path, delete=False
            )
            json.dump(vars, temp_var_file)
            temp_var_file.close()
            var_file_path = temp_var_file.name

        # Build command
        cmd = build_terraform_command(action, vars, var_file_path)

        logger.info(f"Executing Terraform {action} in {path}")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Execute with timing
        start_time = time.time()

        result = subprocess.run(
            cmd,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=get_controlled_env(),
        )

        duration = time.time() - start_time

        # Build response
        response = {
            "action": action,
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "duration": round(duration, 2),
        }

        # For plan action, parse the plan output
        if action == "plan":
            # Terraform returns 0 for no changes, 2 for changes (with -detailed-exitcode)
            # Without -detailed-exitcode, it returns 0 for both
            plan_data = parse_plan_output(path)

            if plan_data:
                response["plan_summary"] = plan_data["plan_summary"]
                response["resources"] = plan_data["resources"]
            else:
                # Fallback to text parsing
                response["plan_summary"] = parse_text_plan_summary(result.stdout)

        # For version action, parse JSON output
        if action == "version" and result.returncode == 0:
            try:
                version_data = json.loads(result.stdout)
                response["terraform_version"] = version_data.get("terraform_version")
                response["platform"] = version_data.get("platform")
                response["provider_selections"] = version_data.get(
                    "provider_selections", {}
                )
            except json.JSONDecodeError:
                pass

        # For show action, include parsed state
        if action == "show" and result.returncode == 0:
            try:
                response["state"] = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        logger.info(
            f"Terraform {action} completed: success={response['success']}, "
            f"exit_code={response['exit_code']}, duration={response['duration']}s"
        )

        return response

    except subprocess.TimeoutExpired as e:
        duration = timeout
        logger.error(f"Terraform {action} timed out after {timeout}s")

        return {
            "action": action,
            "success": False,
            "exit_code": -1,
            "stdout": e.stdout.decode("utf-8", errors="replace") if e.stdout else "",
            "stderr": f"Operation timed out after {timeout} seconds",
            "duration": duration,
        }

    except FileNotFoundError:
        logger.error("Terraform binary not found")
        return {
            "action": action,
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "Terraform binary not found. Ensure terraform is installed and in PATH.",
            "duration": 0.0,
        }

    except PermissionError as e:
        logger.error(f"Permission error: {e}")
        return {
            "action": action,
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Permission denied: {str(e)}",
            "duration": 0.0,
        }

    except Exception as e:
        logger.error(f"Unexpected error during Terraform {action}: {e}")
        return {
            "action": action,
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "duration": 0.0,
        }

    finally:
        # Clean up temporary var file
        if temp_var_file and os.path.exists(temp_var_file.name):
            try:
                os.unlink(temp_var_file.name)
            except Exception as e:
                logger.warning(f"Failed to clean up temp var file: {e}")

        # Clean up plan file after execution
        plan_file = Path(path) / "tfplan"
        if plan_file.exists():
            try:
                plan_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up plan file: {e}")


# Convenience function for batch execution
def run_terraform_actions(
    path: str, actions: list, vars: Optional[Dict[str, Any]] = None
) -> list:
    """
    Execute multiple Terraform actions in sequence.

    Args:
        path: Full path to Terraform workspace directory
        actions: List of actions to execute
        vars: Optional variables (passed only to plan action)

    Returns:
        List of results for each action
    """
    results = []

    for action in actions:
        # Only pass vars to plan action
        action_vars = vars if action == "plan" else None
        result = run_terraform(path, action, action_vars)
        results.append(result)

        # Stop on failure (except for fmt which may fail on formatting issues)
        if not result["success"] and action != "fmt":
            logger.warning(f"Action {action} failed, stopping execution")
            break

    return results
