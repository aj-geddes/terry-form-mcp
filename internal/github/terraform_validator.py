"""
Terraform validation for GitHub pull requests
Integrates with Terry-Form MCP's existing validation capabilities
"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..terraform.executor import TerraformExecutor
from ..lsp.terraform_lsp_client import TerraformLSPClient

logger = logging.getLogger(__name__)


class TerraformPRValidator:
    """Validates Terraform configurations in GitHub PRs"""
    
    def __init__(self, github_app, terraform_executor: TerraformExecutor, lsp_client: TerraformLSPClient):
        self.github_app = github_app
        self.terraform_executor = terraform_executor
        self.lsp_client = lsp_client
        
    async def validate_files(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate Terraform files from a PR"""
        
        # Create temporary workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_path = Path(tmpdir)
            
            # Download files
            await self._download_files(
                installation_id,
                repo_full_name,
                files,
                workspace_path
            )
            
            # Run validations
            results = {
                "valid": True,
                "title": "Terraform Validation Results",
                "summary": "",
                "annotations": [],
                "comment": ""
            }
            
            # 1. Terraform init
            init_result = await self._run_init(workspace_path)
            if not init_result["success"]:
                results["valid"] = False
                results["summary"] = "Terraform initialization failed"
                results["comment"] = self._format_init_error(init_result)
                return results
            
            # 2. Terraform validate
            validate_result = await self._run_validate(workspace_path)
            if not validate_result["success"]:
                results["valid"] = False
                results["annotations"].extend(self._create_annotations(validate_result, files))
            
            # 3. Terraform fmt check
            fmt_result = await self._run_fmt_check(workspace_path)
            if not fmt_result["success"]:
                results["valid"] = False
                results["annotations"].extend(self._create_fmt_annotations(fmt_result, files))
            
            # 4. LSP analysis
            lsp_results = await self._run_lsp_analysis(workspace_path, files)
            if lsp_results["diagnostics"]:
                results["annotations"].extend(self._create_lsp_annotations(lsp_results, files))
            
            # 5. Terraform plan (if all previous checks pass)
            plan_result = None
            if results["valid"]:
                plan_result = await self._run_plan(workspace_path)
                if not plan_result["success"]:
                    results["valid"] = False
            
            # Generate summary and comment
            results["summary"] = self._generate_summary(
                init_result,
                validate_result,
                fmt_result,
                lsp_results,
                plan_result
            )
            
            results["comment"] = self._generate_pr_comment(
                init_result,
                validate_result,
                fmt_result,
                lsp_results,
                plan_result
            )
            
            return results
    
    async def _download_files(
        self,
        installation_id: int,
        repo_full_name: str,
        files: List[Dict[str, Any]],
        workspace_path: Path
    ):
        """Download PR files to workspace"""
        tasks = []
        
        for file_info in files:
            if file_info["status"] == "removed":
                continue
                
            file_path = workspace_path / file_info["filename"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            task = self._download_file(
                installation_id,
                repo_full_name,
                file_info["filename"],
                file_info["contents_url"],
                file_path
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def _download_file(
        self,
        installation_id: int,
        repo_full_name: str,
        filename: str,
        contents_url: str,
        file_path: Path
    ):
        """Download a single file"""
        # Extract ref from contents URL
        ref = contents_url.split("?ref=")[-1] if "?ref=" in contents_url else "main"
        
        content = await self.github_app.get_file_content(
            installation_id,
            repo_full_name,
            filename,
            ref
        )
        
        file_path.write_text(content)
    
    async def _run_init(self, workspace_path: Path) -> Dict[str, Any]:
        """Run terraform init"""
        result = await self.terraform_executor.execute_terraform(
            "init",
            workspace_path,
            ["-no-color", "-input=false"]
        )
        
        return {
            "success": result["exit_code"] == 0,
            "output": result["output"],
            "error": result["error"]
        }
    
    async def _run_validate(self, workspace_path: Path) -> Dict[str, Any]:
        """Run terraform validate"""
        result = await self.terraform_executor.execute_terraform(
            "validate",
            workspace_path,
            ["-no-color", "-json"]
        )
        
        if result["exit_code"] == 0:
            return {"success": True, "diagnostics": []}
        
        try:
            validation_output = json.loads(result["output"])
            return {
                "success": validation_output.get("valid", False),
                "diagnostics": validation_output.get("diagnostics", [])
            }
        except json.JSONDecodeError:
            return {
                "success": False,
                "diagnostics": [],
                "error": result["error"] or result["output"]
            }
    
    async def _run_fmt_check(self, workspace_path: Path) -> Dict[str, Any]:
        """Run terraform fmt check"""
        result = await self.terraform_executor.execute_terraform(
            "fmt",
            workspace_path,
            ["-check", "-diff", "-no-color"]
        )
        
        return {
            "success": result["exit_code"] == 0,
            "unformatted_files": result["output"].strip().split("\n") if result["output"] else [],
            "diff": result["output"]
        }
    
    async def _run_plan(self, workspace_path: Path) -> Dict[str, Any]:
        """Run terraform plan"""
        result = await self.terraform_executor.execute_terraform(
            "plan",
            workspace_path,
            ["-no-color", "-input=false", "-json"]
        )
        
        if result["exit_code"] != 0:
            return {
                "success": False,
                "error": result["error"] or result["output"]
            }
        
        # Parse plan output
        plan_summary = {
            "add": 0,
            "change": 0,
            "destroy": 0
        }
        
        for line in result["output"].split("\n"):
            if not line:
                continue
                
            try:
                data = json.loads(line)
                if data.get("type") == "planned_change":
                    action = data.get("change", {}).get("action", "")
                    if action == "create":
                        plan_summary["add"] += 1
                    elif action == "update":
                        plan_summary["change"] += 1
                    elif action == "delete":
                        plan_summary["destroy"] += 1
            except json.JSONDecodeError:
                continue
        
        return {
            "success": True,
            "summary": plan_summary
        }
    
    async def _run_lsp_analysis(self, workspace_path: Path, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run LSP analysis on files"""
        diagnostics = []
        
        for file_info in files:
            if file_info["status"] == "removed":
                continue
                
            file_path = workspace_path / file_info["filename"]
            if not file_path.exists():
                continue
            
            # Get LSP diagnostics
            file_diagnostics = await self.lsp_client.get_diagnostics(str(file_path))
            diagnostics.extend([
                {
                    "file": file_info["filename"],
                    "diagnostic": d
                }
                for d in file_diagnostics
            ])
        
        return {"diagnostics": diagnostics}
    
    def _create_annotations(self, validate_result: Dict[str, Any], files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create GitHub annotations from terraform validate results"""
        annotations = []
        
        for diagnostic in validate_result.get("diagnostics", []):
            # Find the file in PR files
            filename = diagnostic.get("filename", "")
            file_info = next((f for f in files if f["filename"] == filename), None)
            
            if not file_info:
                continue
            
            annotation = {
                "path": filename,
                "start_line": diagnostic.get("range", {}).get("start", {}).get("line", 1),
                "end_line": diagnostic.get("range", {}).get("end", {}).get("line", 1),
                "annotation_level": "error" if diagnostic.get("severity") == "error" else "warning",
                "message": diagnostic.get("summary", ""),
                "title": "Terraform Validation Error"
            }
            
            if diagnostic.get("detail"):
                annotation["raw_details"] = diagnostic["detail"]
            
            annotations.append(annotation)
        
        return annotations
    
    def _create_fmt_annotations(self, fmt_result: Dict[str, Any], files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create annotations for formatting issues"""
        annotations = []
        
        for filename in fmt_result.get("unformatted_files", []):
            if not filename:
                continue
                
            file_info = next((f for f in files if f["filename"] == filename), None)
            if not file_info:
                continue
            
            annotations.append({
                "path": filename,
                "start_line": 1,
                "end_line": 1,
                "annotation_level": "warning",
                "message": "File is not properly formatted. Run 'terraform fmt' to fix.",
                "title": "Terraform Format Check"
            })
        
        return annotations
    
    def _create_lsp_annotations(self, lsp_results: Dict[str, Any], files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create annotations from LSP diagnostics"""
        annotations = []
        
        for item in lsp_results.get("diagnostics", []):
            filename = item["file"]
            diagnostic = item["diagnostic"]
            
            file_info = next((f for f in files if f["filename"] == filename), None)
            if not file_info:
                continue
            
            # Map LSP severity to GitHub annotation level
            severity_map = {
                1: "error",      # Error
                2: "warning",    # Warning
                3: "notice",     # Information
                4: "notice"      # Hint
            }
            
            annotation = {
                "path": filename,
                "start_line": diagnostic.get("range", {}).get("start", {}).get("line", 1) + 1,
                "end_line": diagnostic.get("range", {}).get("end", {}).get("line", 1) + 1,
                "annotation_level": severity_map.get(diagnostic.get("severity", 2), "warning"),
                "message": diagnostic.get("message", ""),
                "title": "Terraform Language Server"
            }
            
            annotations.append(annotation)
        
        return annotations
    
    def _generate_summary(
        self,
        init_result: Dict[str, Any],
        validate_result: Dict[str, Any],
        fmt_result: Dict[str, Any],
        lsp_results: Dict[str, Any],
        plan_result: Optional[Dict[str, Any]]
    ) -> str:
        """Generate summary for check run"""
        parts = []
        
        # Init status
        if init_result["success"]:
            parts.append("✅ Terraform initialization successful")
        else:
            parts.append("❌ Terraform initialization failed")
            return "\n".join(parts)
        
        # Validate status
        if validate_result["success"]:
            parts.append("✅ Terraform validation passed")
        else:
            error_count = len(validate_result.get("diagnostics", []))
            parts.append(f"❌ Terraform validation failed ({error_count} errors)")
        
        # Format status
        if fmt_result["success"]:
            parts.append("✅ Terraform formatting correct")
        else:
            file_count = len(fmt_result.get("unformatted_files", []))
            parts.append(f"⚠️ {file_count} files need formatting")
        
        # LSP status
        diagnostic_count = len(lsp_results.get("diagnostics", []))
        if diagnostic_count > 0:
            parts.append(f"⚠️ {diagnostic_count} language server diagnostics")
        
        # Plan status
        if plan_result:
            if plan_result["success"]:
                summary = plan_result["summary"]
                parts.append(
                    f"📋 Plan: {summary['add']} to add, "
                    f"{summary['change']} to change, "
                    f"{summary['destroy']} to destroy"
                )
            else:
                parts.append("❌ Terraform plan failed")
        
        return "\n".join(parts)
    
    def _generate_pr_comment(
        self,
        init_result: Dict[str, Any],
        validate_result: Dict[str, Any],
        fmt_result: Dict[str, Any],
        lsp_results: Dict[str, Any],
        plan_result: Optional[Dict[str, Any]]
    ) -> str:
        """Generate detailed PR comment"""
        sections = [
            "## 🔍 Terry-Form Validation Results\n"
        ]
        
        # Summary section
        sections.append("### Summary\n")
        sections.append(self._generate_summary(
            init_result, validate_result, fmt_result, lsp_results, plan_result
        ))
        sections.append("")
        
        # Details sections
        if not init_result["success"]:
            sections.append("### Initialization Error\n")
            sections.append("```")
            sections.append(init_result.get("error", "Unknown error"))
            sections.append("```\n")
        
        if not validate_result["success"] and validate_result.get("diagnostics"):
            sections.append("### Validation Errors\n")
            for diag in validate_result["diagnostics"]:
                sections.append(f"**{diag.get('filename', 'unknown')}**: {diag.get('summary', '')}")
                if diag.get("detail"):
                    sections.append(f"  {diag['detail']}")
            sections.append("")
        
        if not fmt_result["success"]:
            sections.append("### Formatting Issues\n")
            sections.append("The following files need formatting:")
            for filename in fmt_result.get("unformatted_files", []):
                if filename:
                    sections.append(f"- `{filename}`")
            sections.append("\nRun `terraform fmt` to fix these issues.\n")
        
        if lsp_results.get("diagnostics"):
            sections.append("### Language Server Diagnostics\n")
            for item in lsp_results["diagnostics"]:
                diag = item["diagnostic"]
                sections.append(
                    f"**{item['file']}:{diag['range']['start']['line']+1}**: "
                    f"{diag['message']}"
                )
            sections.append("")
        
        if plan_result and plan_result["success"]:
            sections.append("### Plan Summary\n")
            summary = plan_result["summary"]
            sections.append(f"- **Resources to add**: {summary['add']}")
            sections.append(f"- **Resources to change**: {summary['change']}")
            sections.append(f"- **Resources to destroy**: {summary['destroy']}\n")
        
        sections.append("---")
        sections.append("*Validated by [Terry-Form MCP](https://github.com/aj-geddes/terry-form-mcp) v3.0.0*")
        
        return "\n".join(sections)
    
    def _format_init_error(self, init_result: Dict[str, Any]) -> str:
        """Format initialization error for PR comment"""
        return f"""## ❌ Terraform Initialization Failed

```
{init_result.get('error', 'Unknown error')}
```

Please check your provider configurations and module sources.
"""