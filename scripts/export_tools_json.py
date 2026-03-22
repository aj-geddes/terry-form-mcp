#!/usr/bin/env python3
"""Export all MCP tool schemas from the server to tools.json.

Usage:
    python3 scripts/export_tools_json.py
    python3 scripts/export_tools_json.py --output path/to/tools.json

Generates tools.json at the project root and docs/_data/tools.json for Jekyll.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

script_logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    from _version import __version__ as _SERVER_VERSION
except ImportError:
    _SERVER_VERSION = "unknown"

CATEGORIES = {
    "Core Terraform": {
        "prefix": "terry_*",
        "tools": {
            "terry", "terry_version", "terry_environment_check", "terry_workspace_list",
        },
    },
    "LSP Intelligence": {
        "prefix": "terraform_*",
        "tools": {
            "terraform_validate_lsp", "terraform_hover", "terraform_complete",
            "terraform_format_lsp", "terraform_lsp_status",
        },
    },
    "Diagnostics": {
        "prefix": "terry_lsp_*, terry_file_*, terry_workspace_*",
        "tools": {
            "terry_lsp_debug", "terry_workspace_info", "terry_lsp_init",
            "terry_file_check", "terry_workspace_setup", "terry_analyze",
        },
    },
    "Security & Recommendations": {
        "prefix": "terry_security_*, terry_recommendations",
        "tools": {"terry_security_scan", "terry_recommendations"},
    },
    "GitHub Integration": {
        "prefix": "github_*",
        "tools": {
            "github_clone_repo", "github_list_terraform_files",
            "github_get_terraform_config", "github_prepare_workspace",
        },
    },
    "Terraform Cloud": {
        "prefix": "tf_cloud_*",
        "tools": {
            "tf_cloud_list_workspaces", "tf_cloud_get_workspace",
            "tf_cloud_list_runs", "tf_cloud_get_state_outputs",
        },
    },
}


def get_category(tool_name: str) -> str:
    for cat_name, cat_info in CATEGORIES.items():
        if tool_name in cat_info["tools"]:
            return cat_name
    return "Uncategorized"


def parse_description(raw: str) -> dict:
    """Split a docstring into summary, args description, and returns description."""
    lines = raw.strip().split("\n")
    summary_lines = []
    args_lines = []
    returns_lines = []
    section = "summary"

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Args:"):
            section = "args"
            continue
        elif stripped.startswith("Returns:"):
            section = "returns"
            continue

        if section == "summary":
            summary_lines.append(stripped)
        elif section == "args":
            args_lines.append(stripped)
        elif section == "returns":
            returns_lines.append(stripped)

    return {
        "summary": " ".join(s for s in summary_lines if s),
        "args_raw": "\n".join(args_lines).strip(),
        "returns": " ".join(s for s in returns_lines if s),
    }


def simplify_type(schema: dict) -> str:
    """Convert a JSON Schema type to a readable string."""
    if "anyOf" in schema:
        types = [simplify_type(s) for s in schema["anyOf"] if s.get("type") != "null"]
        return types[0] if len(types) == 1 else " | ".join(types)
    t = schema.get("type", "any")
    if t == "array":
        items = schema.get("items", {})
        return f"array<{simplify_type(items)}>"
    if t == "object" and schema.get("additionalProperties"):
        return "object"
    return t


def build_parameters(input_schema: dict) -> list:
    """Extract a clean parameter list from inputSchema."""
    props = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    params = []
    for name, schema in props.items():
        params.append({
            "name": name,
            "type": simplify_type(schema),
            "required": name in required,
            "default": schema.get("default"),
            "description": schema.get("description", ""),
        })
    return params


async def export():
    from server_enhanced_with_lsp import mcp

    tools_map = await mcp.get_tools()
    tools = []

    for name, tool in sorted(tools_map.items()):
        mcp_tool = tool.to_mcp_tool()
        raw = mcp_tool.model_dump(exclude_none=True)
        desc = parse_description(raw.get("description", ""))
        category = get_category(name)

        tools.append({
            "name": name,
            "summary": desc["summary"],
            "description": raw.get("description", ""),
            "returns": desc["returns"],
            "category": category,
            "parameters": build_parameters(raw.get("inputSchema", {})),
            "inputSchema": raw.get("inputSchema", {}),
        })

    categories = {}
    for cat_name, cat_info in CATEGORIES.items():
        count = sum(1 for t in tools if t["category"] == cat_name)
        categories[cat_name] = {
            "prefix": cat_info["prefix"],
            "count": count,
        }

    return {
        "server": {"name": "terry-form", "version": _SERVER_VERSION},
        "tool_count": len(tools),
        "tools": tools,
        "categories": categories,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    output_path = PROJECT_ROOT / "tools.json"
    if len(sys.argv) > 2 and sys.argv[1] == "--output":
        output_path = Path(sys.argv[2])

    try:
        data = asyncio.run(export())
    except Exception as e:
        script_logger.error(f"Failed to export tools.json: {e}", exc_info=True)
        sys.exit(1)

    # Write to project root
    output_path.write_text(json.dumps(data, indent=2) + "\n")
    script_logger.info(f"Wrote {output_path} ({data['tool_count']} tools)")

    # Also write to docs/_data/ for Jekyll
    docs_data = PROJECT_ROOT / "docs" / "_data" / "tools.json"
    if docs_data.parent.exists():
        docs_data.write_text(json.dumps(data, indent=2) + "\n")
        script_logger.info(f"Wrote {docs_data}")


if __name__ == "__main__":
    main()
