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
    import time
    import re
    
    base_cmds = {
        "init": ["terraform", "init", "-input=false"],
        "validate": ["terraform", "validate"],
        "fmt": ["terraform", "fmt", "-check", "-recursive"],
        "show": ["terraform", "show"],
        "graph": ["terraform", "graph"],
        "providers": ["terraform", "providers"],
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
            "action": action,
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Unsupported action '{action}'",
            "duration": 0.0,
        }

    try:
        start_time = time.time()
        result = subprocess.run(cmd, cwd=path, capture_output=True, text=True, shell=False)
        duration = round(time.time() - start_time, 2)
        
        response = {
            "action": action,
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "duration": duration,
        }
        
        # Add plan-specific parsing for plan actions
        if action == "plan" and result.returncode == 0:
            plan_summary = parse_terraform_plan_output(result.stdout)
            if plan_summary:
                response["plan_summary"] = plan_summary
                response["resources"] = extract_resources_from_plan(result.stdout)
        
        return response
    except Exception as e:
        return {
            "action": action,
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(e),
            "duration": 0.0,
        }


def parse_terraform_plan_output(stdout):
    """Parse Terraform plan output to extract summary information."""
    try:
        # Look for plan summary in output
        add_pattern = r"Plan: (?:(\d+) to add,)? ?(?:(\d+) to change,)? ?(?:(\d+) to destroy)?"
        match = re.search(add_pattern, stdout)
        
        if match:
            add_count = int(match.group(1)) if match.group(1) else 0
            change_count = int(match.group(2)) if match.group(2) else 0
            destroy_count = int(match.group(3)) if match.group(3) else 0
            
            return {
                "add": add_count,
                "change": change_count,
                "destroy": destroy_count
            }
        
        # If no changes
        if "No changes" in stdout:
            return {"add": 0, "change": 0, "destroy": 0}
            
    except Exception:
        pass
    
    return None


def extract_resources_from_plan(stdout):
    """Extract resource information from Terraform plan output."""
    resources = []
    try:
        # Basic resource extraction - this is a simplified version
        # In a full implementation, you'd parse the entire plan JSON
        lines = stdout.split('\n')
        for line in lines:
            if line.strip().startswith('# ') and ('will be created' in line or 'will be updated' in line or 'will be destroyed' in line):
                resource_match = re.search(r'# (.+?) will be', line)
                if resource_match:
                    resource_name = resource_match.group(1)
                    action = "create" if "created" in line else "update" if "updated" in line else "destroy"
                    resources.append({
                        "address": resource_name,
                        "action": action,
                        "type": resource_name.split('.')[0] if '.' in resource_name else "unknown"
                    })
    except Exception:
        pass
    
    return resources


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
