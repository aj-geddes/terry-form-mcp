#!/usr/bin/env python3
"""
MCP Request Validator
Validates incoming MCP protocol requests for security and compliance.

Security hardened:
- Path traversal prevention
- Command injection prevention
- Input sanitization
- Action whitelisting
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


class MCPRequestValidator:
    """Validates MCP protocol requests for security and compliance"""

    def __init__(self, workspace_root: str = "/mnt/workspace"):
        self.workspace_root = Path(workspace_root)

        # Define allowed actions for terry tool
        self.allowed_terraform_actions = {
            "init",
            "validate",
            "fmt",
            "plan",
            "show",
            "graph",
            "providers",
            "version",
        }
        self.blocked_terraform_actions = {
            "apply",
            "destroy",
            "import",
            "taint",
            "untaint",
        }

        # Define validation patterns
        self.valid_name_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
        self.dangerous_chars_pattern = re.compile(r'[$`\\"\';|&><(){}]')

    def validate_request(self, request: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate an MCP request.
        Returns (is_valid, error_message)
        """
        try:
            # Check basic structure
            if not isinstance(request, dict):
                return False, "Request must be a dictionary"

            method = request.get("method", "")
            if method != "tools/call":
                # Non-tool calls are allowed (handled by MCP framework)
                return True, ""

            params = request.get("params", {})
            if not isinstance(params, dict):
                return False, "Params must be a dictionary"

            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            # Validate based on tool
            if tool_name == "terry":
                return self._validate_terry_request(arguments)
            elif tool_name.startswith("github_"):
                return self._validate_github_request(tool_name, arguments)
            elif tool_name.startswith("tf_cloud_"):
                return self._validate_tf_cloud_request(tool_name, arguments)
            elif tool_name.startswith("terry_"):
                return self._validate_terry_extended_request(tool_name, arguments)
            else:
                # Unknown tools are allowed (handled by MCP framework)
                return True, ""

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation error: {str(e)}"

    def _validate_terry_request(self, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate terry tool request"""
        # Validate path
        path = arguments.get("path", "")
        if not path:
            return False, "Path is required"

        # Check for path traversal
        if not self._is_safe_path(path):
            return False, "Invalid path: access outside workspace is not allowed"

        # Validate actions
        actions = arguments.get("actions", [])
        if not isinstance(actions, list):
            return False, "Actions must be a list"

        for action in actions:
            if action in self.blocked_terraform_actions:
                return False, f"Action '{action}' is blocked for security reasons"
            if action not in self.allowed_terraform_actions:
                return False, f"Unknown action '{action}'"

        # Validate variables
        vars_dict = arguments.get("vars", {})
        if vars_dict and not isinstance(vars_dict, dict):
            return False, "Variables must be a dictionary"

        if vars_dict:
            is_valid, error = self._validate_terraform_vars(vars_dict)
            if not is_valid:
                return False, error

        # Check blocked flags
        if arguments.get("auto_approve", False):
            return False, "auto_approve is blocked for security reasons"
        if arguments.get("destroy", False):
            return False, "destroy is blocked for security reasons"

        return True, ""

    def _validate_github_request(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate GitHub tool requests"""
        # Validate owner/repo names
        owner = arguments.get("owner", "")
        repo = arguments.get("repo", "")

        if owner and not self.valid_name_pattern.match(owner):
            return False, f"Invalid repository owner name: {owner}"

        if repo:
            # Allow dots in repo names
            if not re.match(r"^[a-zA-Z0-9_.-]+$", repo):
                return False, f"Invalid repository name: {repo}"

        # Validate other parameters based on tool
        if tool_name == "github_cleanup_repos":
            days = arguments.get("days_old", 7)
            if not isinstance(days, int) or days < 0 or days > 365:
                return False, "Invalid days_old parameter"

        return True, ""

    def _validate_tf_cloud_request(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate Terraform Cloud tool requests"""
        # Basic validation for organization/workspace names
        org = arguments.get("organization", "")
        workspace = arguments.get("workspace", "")

        if org and not self.valid_name_pattern.match(org):
            return False, f"Invalid organization name: {org}"

        if workspace and not self.valid_name_pattern.match(workspace):
            return False, f"Invalid workspace name: {workspace}"

        # Validate limit parameter
        if "limit" in arguments:
            limit = arguments["limit"]
            if not isinstance(limit, int) or limit < 1 or limit > 100:
                return False, "Invalid limit parameter"

        return True, ""

    def _validate_terry_extended_request(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate extended terry tool requests"""
        # Most extended tools work with file paths
        if "file_path" in arguments or "path" in arguments:
            path = arguments.get("file_path") or arguments.get("path", "")
            if not self._is_safe_path(path):
                return False, "Invalid path: access outside workspace is not allowed"

        return True, ""

    def _validate_terraform_vars(self, vars: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate Terraform variables for security"""
        for key, value in vars.items():
            # Validate key format
            if (
                not isinstance(key, str)
                or not key.replace("_", "").replace("-", "").isalnum()
            ):
                return False, f"Invalid variable name: {key}"

            # Check for dangerous characters in value
            str_value = str(value)
            if self.dangerous_chars_pattern.search(str_value):
                return False, f"Variable value contains dangerous characters: {key}"

        return True, ""

    def _is_safe_path(self, path: str) -> bool:
        """Check if a path is safe (no traversal attacks)"""
        # Handle special prefixes
        if path.startswith(("github://", "workspace://")):
            return True

        try:
            # Convert to Path object
            if path.startswith("/"):
                target_path = Path(path)
            else:
                target_path = self.workspace_root / path

            # Resolve to real path
            real_path = target_path.resolve()

            # Ensure path is within workspace
            real_path.relative_to(self.workspace_root.resolve())
            return True
        except (ValueError, Exception):
            return False

    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters (for internal use)"""
        sanitized = params.copy()

        # Sanitize paths
        if "path" in sanitized:
            path = sanitized["path"]
            if self._is_safe_path(path):
                try:
                    if not path.startswith(("github://", "workspace://")):
                        if path.startswith("/"):
                            sanitized["path"] = str(Path(path).resolve())
                        else:
                            sanitized["path"] = str(
                                (self.workspace_root / path).resolve()
                            )
                except Exception:
                    # Keep original path if resolution fails
                    logger.debug(f"Failed to resolve path: {path}")

        return sanitized


def validate_mcp_request(
    request: Dict[str, Any], workspace_root: str = "/mnt/workspace"
) -> Tuple[bool, str]:
    """
    Convenience function to validate MCP requests.
    Returns (is_valid, error_message)
    """
    validator = MCPRequestValidator(workspace_root)
    return validator.validate_request(request)
