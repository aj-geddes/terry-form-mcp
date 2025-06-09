#!/usr/bin/env python3
import importlib.util
from pathlib import Path
from typing import List, Dict
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("terry-form")

# Load the existing Terraform tool logic (kebab-case)
spec = importlib.util.spec_from_file_location("terry_form", "./terry-form-mcp.py")
terry_form = importlib.util.module_from_spec(spec)
spec.loader.exec_module(terry_form)

@mcp.tool()
def terry(
    path: str,
    actions: List[str] = ["plan"],
    vars: Dict[str, str] = {}
) -> Dict[str, object]:
    """
    Runs terraform actions in /mnt/workspace/<path> using provided variables.
    Returns a raw JSON result dictionary under `terry-results`.
    """
    full_path = str(Path("/mnt/workspace") / path)
    results = []
    for action in actions:
        results.append(terry_form.run_terraform(full_path, action, vars if action == "plan" else None))
    return {
        "terry-results": results
    }

if __name__ == "__main__":
    mcp.run()
