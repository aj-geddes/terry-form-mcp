"""
MCP Request Validator
Provides JSON schema validation for MCP protocol requests
to prevent malicious inputs and ensure protocol compliance.
"""

from jsonschema import validate, ValidationError
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Define JSON schemas for MCP requests
MCP_TOOL_CALL_SCHEMA = {
    "type": "object",
    "properties": {
        "method": {"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$"},
        "params": {"type": "object"},
        "id": {"type": ["string", "number"]}
    },
    "required": ["method", "params"],
    "additionalProperties": False
}

# Schema for terry tool parameters
TERRY_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "minLength": 1,
            "maxLength": 4096,
            # Disallow certain patterns that might be malicious
            "not": {
                "pattern": "(\\.\\./|\\\\|\\$|`|;|&|\\||>|<|\\(|\\)|{|})"
            }
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["init", "validate", "fmt", "plan", "show", "graph", "providers", "version"]
            },
            "minItems": 1,
            "maxItems": 10
        },
        "vars": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z_][a-zA-Z0-9_-]*$": {
                    "type": ["string", "number", "boolean"],
                    "maxLength": 1024
                }
            },
            "additionalProperties": False,
            "maxProperties": 100
        },
        "auto_approve": {"type": "boolean"},
        "destroy": {"type": "boolean"}
    },
    "required": ["path"],
    "additionalProperties": False
}

# Schema for GitHub tool parameters
GITHUB_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "owner": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9-_]*$",
            "minLength": 1,
            "maxLength": 100
        },
        "repo": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9-_.]*$",
            "minLength": 1,
            "maxLength": 100
        },
        "branch": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9-_/]*$",
            "maxLength": 255
        },
        "path": {
            "type": "string",
            "maxLength": 4096
        },
        "pattern": {
            "type": "string",
            "maxLength": 100
        },
        "config_path": {
            "type": "string",
            "maxLength": 4096
        },
        "workspace_name": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9][a-zA-Z0-9-_]*$",
            "maxLength": 100
        },
        "force": {"type": "boolean"},
        "days_old": {
            "type": "integer",
            "minimum": 0,
            "maximum": 365
        }
    },
    "additionalProperties": False
}

# Schema for LSP tool parameters
LSP_PARAMS_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "minLength": 1,
            "maxLength": 4096,
            "not": {
                "pattern": "(\\.\\./|\\\\|\\$|`)"
            }
        },
        "line": {
            "type": "integer",
            "minimum": 0,
            "maximum": 1000000
        },
        "character": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10000
        }
    },
    "required": ["file_path"],
    "additionalProperties": False
}

# Map tool names to their parameter schemas
TOOL_SCHEMAS = {
    "terry": TERRY_PARAMS_SCHEMA,
    "terry_validate": LSP_PARAMS_SCHEMA,
    "terry_hover": LSP_PARAMS_SCHEMA,
    "terry_complete": LSP_PARAMS_SCHEMA,
    "terry_format": LSP_PARAMS_SCHEMA,
    "terry_workspace_info": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "maxLength": 4096
            }
        },
        "additionalProperties": False
    },
    # GitHub tools
    "github_clone_repo": GITHUB_PARAMS_SCHEMA,
    "github_list_terraform_files": GITHUB_PARAMS_SCHEMA,
    "github_get_terraform_config": GITHUB_PARAMS_SCHEMA,
    "github_prepare_workspace": GITHUB_PARAMS_SCHEMA,
    "github_repo_info": GITHUB_PARAMS_SCHEMA,
    "github_cleanup_repos": GITHUB_PARAMS_SCHEMA,
    # No params tools
    "terry_lsp_status": {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    },
    "github_list_installations": {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    }
}


class MCPRequestValidator:
    """Validates MCP protocol requests for security and compliance"""

    def __init__(self, custom_schemas: Optional[Dict[str, Dict]] = None):
        """
        Initialize the validator with optional custom schemas.

        Args:
            custom_schemas: Additional tool schemas to register
        """
        self.tool_schemas = TOOL_SCHEMAS.copy()
        if custom_schemas:
            self.tool_schemas.update(custom_schemas)

    def validate_request(self, request: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate an MCP request structure.

        Args:
            request: The request dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate basic structure
            validate(instance=request, schema=MCP_TOOL_CALL_SCHEMA)

            # Get method name
            method = request.get("method", "")

            # Check if tool is known
            if method not in self.tool_schemas:
                return False, f"Unknown tool: {method}"

            # Validate parameters for the specific tool
            params = request.get("params", {})
            tool_schema = self.tool_schemas[method]

            try:
                validate(instance=params, schema=tool_schema)
            except ValidationError as e:
                return False, f"Invalid parameters for {method}: {e.message}"

            # Additional security checks
            if not self._security_checks(method, params):
                return False, "Security validation failed"

            return True, None

        except ValidationError as e:
            return False, f"Invalid request structure: {e.message}"
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation error: {str(e)}"

    def _security_checks(self, method: str, params: Dict[str, Any]) -> bool:
        """
        Perform additional security checks beyond schema validation.

        Args:
            method: The method being called
            params: The parameters for the method

        Returns:
            True if security checks pass
        """
        # Check for specific dangerous patterns
        if method.startswith("terry"):
            # Ensure no command injection attempts
            if "path" in params:
                path = params["path"]
                dangerous_patterns = [
                    "$(", "${", "`", "\\n", "\\r", "\\0",
                    ";", "&", "|", ">>", "<<", "&&", "||"
                ]
                if any(pattern in str(path) for pattern in dangerous_patterns):
                    logger.warning(f"Dangerous pattern detected in path: {path}")
                    return False

            # Check vars for injection attempts
            if "vars" in params:
                for key, value in params["vars"].items():
                    str_value = str(value)
                    if len(str_value) > 1024:
                        logger.warning(f"Variable value too long: {key}")
                        return False

                    # Check for template injection
                    if "{{" in str_value or "${" in str_value:
                        logger.warning(f"Template injection attempt in variable: {key}")
                        return False

        return True

    def sanitize_params(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize parameters to ensure they're safe to use.

        Args:
            method: The method being called
            params: The parameters to sanitize

        Returns:
            Sanitized parameters
        """
        sanitized = params.copy()

        # Remove any keys not in the schema
        if method in self.tool_schemas:
            schema = self.tool_schemas[method]
            allowed_keys = schema.get("properties", {}).keys()
            sanitized = {k: v for k, v in sanitized.items() if k in allowed_keys}

        # Additional sanitization based on method
        if method.startswith("terry"):
            # Ensure certain flags are always false for security
            sanitized["auto_approve"] = False
            sanitized["destroy"] = False

        return sanitized

    def get_allowed_tools(self) -> List[str]:
        """Get list of allowed tool names"""
        return list(self.tool_schemas.keys())

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the schema for a specific tool"""
        return self.tool_schemas.get(tool_name)


# Create a default validator instance
default_validator = MCPRequestValidator()


def validate_mcp_request(request: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Convenience function to validate an MCP request.

    Args:
        request: The request to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return default_validator.validate_request(request)


def sanitize_mcp_params(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to sanitize MCP parameters.

    Args:
        method: The method being called
        params: The parameters to sanitize

    Returns:
        Sanitized parameters
    """
    return default_validator.sanitize_params(method, params)
