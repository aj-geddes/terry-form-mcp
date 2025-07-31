#!/usr/bin/env python3
import json
import os
import shlex
import subprocess
import sys

# Define your fixed workspace root
WORKSPACE_ROOT = "/mnt/workspace"


def build_var_args(vars_dict):
    """Build Terraform variable arguments with proper shell escaping."""
    args = []
    for key, val in vars_dict.items():
        # Validate key to prevent injection
        if not key.replace("_", "").replace("-", "").isalnum():
            raise ValueError(f"Invalid variable name: {key}")
        # Use shlex.quote for safe shell escaping
        args += ["-var", f"{key}={shlex.quote(str(val))}"]
    return args


def run_terraform(path, action, vars_dict=None):
    base_cmds = {
        "init": ["terraform", "init", "-input=false"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt", "-check", "-recursive"],
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
            "error": f"Unsupported action '{action}'",
        }

    try:
        result = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
        return {
            "success": result.returncode == 0,
            "action": action,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"success": False, "action": action, "error": str(e)}


def main():
    try:
        input_data = json.load(sys.stdin)
        rel_path = input_data["path"]
        abs_path = os.path.join(WORKSPACE_ROOT, rel_path)

        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Resolved path does not exist: {abs_path}")

        actions = input_data.get("actions", [input_data.get("action", "plan")])
        vars_dict = input_data.get("vars", {})

        results = []
        for action in actions:
            results.append(
                run_terraform(abs_path, action, vars_dict if action == "plan" else None)
            )

        print(json.dumps(results, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))


if __name__ == "__main__":
    main()
