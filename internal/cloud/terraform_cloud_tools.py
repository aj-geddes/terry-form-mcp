"""
Terraform Cloud MCP tools for Terry-Form MCP v3.0.0
Provides MCP tool interfaces for Terraform Cloud operations
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import Tool
from pydantic import BaseModel, Field

from .terraform_cloud_client import TerraformCloudClient, TerraformCloudError

logger = logging.getLogger(__name__)


# Tool parameter models

class WorkspaceManagementParams(BaseModel):
    """Parameters for workspace management operations"""
    action: str = Field(description="Action to perform: list, get, create, update, delete")
    workspace_name: Optional[str] = Field(None, description="Name of the workspace")
    search: Optional[str] = Field(None, description="Search term for listing workspaces")
    auto_apply: Optional[bool] = Field(None, description="Auto-apply setting for workspace")
    execution_mode: Optional[str] = Field(None, description="Execution mode: remote, local, agent")
    terraform_version: Optional[str] = Field(None, description="Terraform version to use")
    working_directory: Optional[str] = Field(None, description="Working directory in VCS")
    description: Optional[str] = Field(None, description="Workspace description")


class RunOperationsParams(BaseModel):
    """Parameters for run operations"""
    action: str = Field(description="Action: create, get, list, apply, cancel, discard")
    workspace_name: str = Field(description="Name of the workspace")
    run_id: Optional[str] = Field(None, description="Run ID for get/apply/cancel/discard")
    message: Optional[str] = Field(None, description="Message for the run")
    is_destroy: bool = Field(False, description="Whether this is a destroy run")
    auto_apply: Optional[bool] = Field(None, description="Override workspace auto-apply")
    target_addrs: Optional[List[str]] = Field(None, description="Target specific resources")
    comment: Optional[str] = Field(None, description="Comment for apply/cancel/discard")


class StateOperationsParams(BaseModel):
    """Parameters for state operations"""
    action: str = Field(description="Action: current, list, get, download")
    workspace_name: str = Field(description="Name of the workspace")
    state_version_id: Optional[str] = Field(None, description="State version ID for get/download")


class VariableOperationsParams(BaseModel):
    """Parameters for variable operations"""
    action: str = Field(description="Action: list, create, update, delete")
    workspace_name: str = Field(description="Name of the workspace")
    key: Optional[str] = Field(None, description="Variable key")
    value: Optional[str] = Field(None, description="Variable value")
    category: str = Field("terraform", description="Variable category: terraform or env")
    description: Optional[str] = Field(None, description="Variable description")
    sensitive: bool = Field(False, description="Whether the variable is sensitive")
    hcl: bool = Field(False, description="Whether the value is HCL")
    variable_id: Optional[str] = Field(None, description="Variable ID for update/delete")


class PolicyCheckParams(BaseModel):
    """Parameters for policy check operations"""
    run_id: str = Field(description="Run ID to check policies for")
    policy_check_id: Optional[str] = Field(None, description="Policy check ID to override")
    comment: Optional[str] = Field(None, description="Comment for policy override")


class CostEstimationParams(BaseModel):
    """Parameters for cost estimation"""
    run_id: str = Field(description="Run ID to get cost estimate for")


class RegistryOperationsParams(BaseModel):
    """Parameters for registry operations"""
    action: str = Field(description="Action: list, get")
    namespace: Optional[str] = Field(None, description="Module namespace")
    name: Optional[str] = Field(None, description="Module name")
    provider: Optional[str] = Field(None, description="Module provider")


# MCP Tools

async def create_terraform_cloud_tools(tfc_client: TerraformCloudClient) -> List[Tool]:
    """Create all Terraform Cloud MCP tools"""
    tools = []
    
    # Workspace Management Tool
    @Tool()
    async def tfc_workspace_management(params: WorkspaceManagementParams) -> Dict[str, Any]:
        """
        Manage Terraform Cloud workspaces.
        Actions: list, get, create, update, delete
        """
        try:
            if params.action == "list":
                workspaces = await tfc_client.list_workspaces(
                    search=params.search
                )
                return {
                    "success": True,
                    "count": len(workspaces),
                    "workspaces": [
                        {
                            "id": w["id"],
                            "name": w["attributes"]["name"],
                            "execution_mode": w["attributes"]["execution-mode"],
                            "terraform_version": w["attributes"]["terraform-version"],
                            "auto_apply": w["attributes"]["auto-apply"],
                            "locked": w["attributes"]["locked"]
                        }
                        for w in workspaces
                    ]
                }
            
            elif params.action == "get":
                if not params.workspace_name:
                    return {"success": False, "error": "workspace_name required"}
                
                workspace = await tfc_client.get_workspace(params.workspace_name)
                return {
                    "success": True,
                    "workspace": {
                        "id": workspace["id"],
                        "name": workspace["attributes"]["name"],
                        "execution_mode": workspace["attributes"]["execution-mode"],
                        "terraform_version": workspace["attributes"]["terraform-version"],
                        "auto_apply": workspace["attributes"]["auto-apply"],
                        "working_directory": workspace["attributes"]["working-directory"],
                        "locked": workspace["attributes"]["locked"],
                        "created_at": workspace["attributes"]["created-at"],
                        "resource_count": workspace["attributes"]["resource-count"]
                    }
                }
            
            elif params.action == "create":
                if not params.workspace_name:
                    return {"success": False, "error": "workspace_name required"}
                
                kwargs = {}
                if params.auto_apply is not None:
                    kwargs["auto_apply"] = params.auto_apply
                if params.execution_mode:
                    kwargs["execution_mode"] = params.execution_mode
                if params.terraform_version:
                    kwargs["terraform_version"] = params.terraform_version
                if params.working_directory:
                    kwargs["working_directory"] = params.working_directory
                if params.description:
                    kwargs["description"] = params.description
                
                workspace = await tfc_client.create_workspace(
                    params.workspace_name,
                    **kwargs
                )
                
                return {
                    "success": True,
                    "workspace_id": workspace["id"],
                    "message": f"Workspace '{params.workspace_name}' created successfully"
                }
            
            elif params.action == "update":
                if not params.workspace_name:
                    return {"success": False, "error": "workspace_name required"}
                
                # Get workspace ID first
                workspace = await tfc_client.get_workspace(params.workspace_name)
                workspace_id = workspace["id"]
                
                kwargs = {}
                if params.auto_apply is not None:
                    kwargs["auto_apply"] = params.auto_apply
                if params.execution_mode:
                    kwargs["execution_mode"] = params.execution_mode
                if params.terraform_version:
                    kwargs["terraform_version"] = params.terraform_version
                if params.working_directory:
                    kwargs["working_directory"] = params.working_directory
                if params.description:
                    kwargs["description"] = params.description
                
                await tfc_client.update_workspace(workspace_id, **kwargs)
                
                return {
                    "success": True,
                    "message": f"Workspace '{params.workspace_name}' updated successfully"
                }
            
            elif params.action == "delete":
                if not params.workspace_name:
                    return {"success": False, "error": "workspace_name required"}
                
                workspace = await tfc_client.get_workspace(params.workspace_name)
                await tfc_client.delete_workspace(workspace["id"])
                
                return {
                    "success": True,
                    "message": f"Workspace '{params.workspace_name}' deleted successfully"
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {params.action}"}
                
        except TerraformCloudError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error in workspace management")
            return {"success": False, "error": str(e)}
    
    tools.append(tfc_workspace_management)
    
    # Run Operations Tool
    @Tool()
    async def tfc_run_operations(params: RunOperationsParams) -> Dict[str, Any]:
        """
        Manage Terraform Cloud runs.
        Actions: create, get, list, apply, cancel, discard
        """
        try:
            # Get workspace ID
            workspace = await tfc_client.get_workspace(params.workspace_name)
            workspace_id = workspace["id"]
            
            if params.action == "create":
                run = await tfc_client.create_run(
                    workspace_id,
                    message=params.message or "Run created by Terry-Form MCP",
                    is_destroy=params.is_destroy,
                    auto_apply=params.auto_apply,
                    target_addrs=params.target_addrs
                )
                
                return {
                    "success": True,
                    "run_id": run["id"],
                    "status": run["attributes"]["status"],
                    "message": f"Run created successfully"
                }
            
            elif params.action == "get":
                if not params.run_id:
                    return {"success": False, "error": "run_id required"}
                
                run = await tfc_client.get_run(params.run_id)
                
                # Get logs if available
                logs = {}
                if run["attributes"]["status"] in ["planned", "applied"]:
                    try:
                        logs["plan"] = await tfc_client.get_run_logs(params.run_id, "plan")
                    except:
                        pass
                
                return {
                    "success": True,
                    "run": {
                        "id": run["id"],
                        "status": run["attributes"]["status"],
                        "message": run["attributes"]["message"],
                        "is_destroy": run["attributes"]["is-destroy"],
                        "created_at": run["attributes"]["created-at"],
                        "has_changes": run["attributes"]["has-changes"],
                        "resource_additions": run["attributes"]["resource-additions"],
                        "resource_changes": run["attributes"]["resource-changes"],
                        "resource_destructions": run["attributes"]["resource-destructions"]
                    },
                    "logs": logs
                }
            
            elif params.action == "list":
                runs = await tfc_client.list_runs(workspace_id)
                
                return {
                    "success": True,
                    "count": len(runs),
                    "runs": [
                        {
                            "id": r["id"],
                            "status": r["attributes"]["status"],
                            "message": r["attributes"]["message"],
                            "created_at": r["attributes"]["created-at"],
                            "is_destroy": r["attributes"]["is-destroy"]
                        }
                        for r in runs[:10]  # Limit to 10 most recent
                    ]
                }
            
            elif params.action == "apply":
                if not params.run_id:
                    return {"success": False, "error": "run_id required"}
                
                await tfc_client.apply_run(params.run_id, params.comment)
                
                return {
                    "success": True,
                    "message": f"Run {params.run_id} applied successfully"
                }
            
            elif params.action == "cancel":
                if not params.run_id:
                    return {"success": False, "error": "run_id required"}
                
                await tfc_client.cancel_run(params.run_id, params.comment)
                
                return {
                    "success": True,
                    "message": f"Run {params.run_id} cancelled"
                }
            
            elif params.action == "discard":
                if not params.run_id:
                    return {"success": False, "error": "run_id required"}
                
                await tfc_client.discard_run(params.run_id, params.comment)
                
                return {
                    "success": True,
                    "message": f"Run {params.run_id} discarded"
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {params.action}"}
                
        except TerraformCloudError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error in run operations")
            return {"success": False, "error": str(e)}
    
    tools.append(tfc_run_operations)
    
    # State Operations Tool
    @Tool()
    async def tfc_state_operations(params: StateOperationsParams) -> Dict[str, Any]:
        """
        Manage Terraform Cloud state.
        Actions: current, list, get, download
        """
        try:
            # Get workspace ID
            workspace = await tfc_client.get_workspace(params.workspace_name)
            workspace_id = workspace["id"]
            
            if params.action == "current":
                state_version = await tfc_client.get_current_state_version(workspace_id)
                
                return {
                    "success": True,
                    "state_version": {
                        "id": state_version["id"],
                        "serial": state_version["attributes"]["serial"],
                        "created_at": state_version["attributes"]["created-at"],
                        "size": state_version["attributes"]["size"],
                        "hosted_state_download_url": state_version["attributes"]["hosted-state-download-url"],
                        "modules": state_version["attributes"]["modules"],
                        "providers": state_version["attributes"]["providers"],
                        "resources": state_version["attributes"]["resources"],
                        "resources_processed": state_version["attributes"]["resources-processed"]
                    }
                }
            
            elif params.action == "list":
                versions = await tfc_client.list_state_versions(workspace_id)
                
                return {
                    "success": True,
                    "count": len(versions),
                    "versions": [
                        {
                            "id": v["id"],
                            "serial": v["attributes"]["serial"],
                            "created_at": v["attributes"]["created-at"],
                            "size": v["attributes"]["size"]
                        }
                        for v in versions[:10]  # Limit to 10 most recent
                    ]
                }
            
            elif params.action == "get":
                if not params.state_version_id:
                    return {"success": False, "error": "state_version_id required"}
                
                state_version = await tfc_client.get_state_version(params.state_version_id)
                
                return {
                    "success": True,
                    "state_version": {
                        "id": state_version["id"],
                        "serial": state_version["attributes"]["serial"],
                        "created_at": state_version["attributes"]["created-at"],
                        "size": state_version["attributes"]["size"],
                        "modules": state_version["attributes"]["modules"],
                        "providers": state_version["attributes"]["providers"],
                        "resources": state_version["attributes"]["resources"]
                    }
                }
            
            elif params.action == "download":
                if not params.state_version_id:
                    # Get current state version
                    state_version = await tfc_client.get_current_state_version(workspace_id)
                    params.state_version_id = state_version["id"]
                
                state_content = await tfc_client.download_state(params.state_version_id)
                
                return {
                    "success": True,
                    "state": state_content,
                    "version": state_content.get("version", 4),
                    "terraform_version": state_content.get("terraform_version", "unknown"),
                    "serial": state_content.get("serial", 0)
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {params.action}"}
                
        except TerraformCloudError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error in state operations")
            return {"success": False, "error": str(e)}
    
    tools.append(tfc_state_operations)
    
    # Variable Operations Tool
    @Tool()
    async def tfc_variable_operations(params: VariableOperationsParams) -> Dict[str, Any]:
        """
        Manage Terraform Cloud variables.
        Actions: list, create, update, delete
        """
        try:
            # Get workspace ID
            workspace = await tfc_client.get_workspace(params.workspace_name)
            workspace_id = workspace["id"]
            
            if params.action == "list":
                variables = await tfc_client.list_variables(workspace_id)
                
                return {
                    "success": True,
                    "count": len(variables),
                    "variables": [
                        {
                            "id": v["id"],
                            "key": v["attributes"]["key"],
                            "value": v["attributes"]["value"] if not v["attributes"]["sensitive"] else "[SENSITIVE]",
                            "category": v["attributes"]["category"],
                            "sensitive": v["attributes"]["sensitive"],
                            "hcl": v["attributes"]["hcl"],
                            "description": v["attributes"]["description"]
                        }
                        for v in variables
                    ]
                }
            
            elif params.action == "create":
                if not params.key or params.value is None:
                    return {"success": False, "error": "key and value required"}
                
                variable = await tfc_client.create_variable(
                    workspace_id,
                    params.key,
                    params.value,
                    category=params.category,
                    description=params.description or "",
                    sensitive=params.sensitive,
                    hcl=params.hcl
                )
                
                return {
                    "success": True,
                    "variable_id": variable["id"],
                    "message": f"Variable '{params.key}' created successfully"
                }
            
            elif params.action == "update":
                if not params.variable_id:
                    return {"success": False, "error": "variable_id required"}
                
                kwargs = {}
                if params.key:
                    kwargs["key"] = params.key
                if params.value is not None:
                    kwargs["value"] = params.value
                if params.description is not None:
                    kwargs["description"] = params.description
                if params.sensitive is not None:
                    kwargs["sensitive"] = params.sensitive
                if params.hcl is not None:
                    kwargs["hcl"] = params.hcl
                
                await tfc_client.update_variable(params.variable_id, **kwargs)
                
                return {
                    "success": True,
                    "message": f"Variable updated successfully"
                }
            
            elif params.action == "delete":
                if not params.variable_id:
                    return {"success": False, "error": "variable_id required"}
                
                await tfc_client.delete_variable(params.variable_id)
                
                return {
                    "success": True,
                    "message": f"Variable deleted successfully"
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {params.action}"}
                
        except TerraformCloudError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error in variable operations")
            return {"success": False, "error": str(e)}
    
    tools.append(tfc_variable_operations)
    
    # Policy Check Tool
    @Tool()
    async def tfc_policy_check(params: PolicyCheckParams) -> Dict[str, Any]:
        """
        Check and override Terraform Cloud policies.
        """
        try:
            if params.policy_check_id:
                # Override a specific policy
                await tfc_client.override_policy(
                    params.policy_check_id,
                    params.comment
                )
                
                return {
                    "success": True,
                    "message": f"Policy check {params.policy_check_id} overridden"
                }
            
            else:
                # List policy checks for a run
                checks = await tfc_client.list_policy_checks(params.run_id)
                
                return {
                    "success": True,
                    "count": len(checks),
                    "policy_checks": [
                        {
                            "id": c["id"],
                            "status": c["attributes"]["status"],
                            "scope": c["attributes"]["scope"],
                            "result": c["attributes"]["result"],
                            "passed": c["attributes"]["passed"],
                            "total_failed": c["attributes"]["total-failed"],
                            "hard_failed": c["attributes"]["hard-failed"],
                            "soft_failed": c["attributes"]["soft-failed"],
                            "advisory_failed": c["attributes"]["advisory-failed"]
                        }
                        for c in checks
                    ]
                }
                
        except TerraformCloudError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error in policy check")
            return {"success": False, "error": str(e)}
    
    tools.append(tfc_policy_check)
    
    # Cost Estimation Tool
    @Tool()
    async def tfc_cost_estimation(params: CostEstimationParams) -> Dict[str, Any]:
        """
        Get cost estimation for a Terraform Cloud run.
        """
        try:
            cost_estimate = await tfc_client.get_cost_estimate(params.run_id)
            
            if not cost_estimate:
                return {
                    "success": True,
                    "message": "No cost estimate available for this run"
                }
            
            attrs = cost_estimate.get("attributes", {})
            
            return {
                "success": True,
                "cost_estimate": {
                    "status": attrs.get("status"),
                    "delta_monthly_cost": attrs.get("delta-monthly-cost"),
                    "prior_monthly_cost": attrs.get("prior-monthly-cost"),
                    "proposed_monthly_cost": attrs.get("proposed-monthly-cost"),
                    "resources_count": attrs.get("resources-count", 0),
                    "matched_resources_count": attrs.get("matched-resources-count", 0),
                    "unmatched_resources_count": attrs.get("unmatched-resources-count", 0)
                }
            }
            
        except TerraformCloudError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error in cost estimation")
            return {"success": False, "error": str(e)}
    
    tools.append(tfc_cost_estimation)
    
    # Registry Operations Tool
    @Tool()
    async def tfc_registry_operations(params: RegistryOperationsParams) -> Dict[str, Any]:
        """
        Browse and retrieve modules from Terraform Cloud private registry.
        Actions: list, get
        """
        try:
            if params.action == "list":
                modules = await tfc_client.list_registry_modules(
                    namespace=params.namespace,
                    provider=params.provider
                )
                
                return {
                    "success": True,
                    "count": len(modules),
                    "modules": [
                        {
                            "id": m["id"],
                            "name": m["attributes"]["name"],
                            "namespace": m["attributes"]["namespace"],
                            "provider": m["attributes"]["provider"],
                            "version": m["attributes"]["version-statuses"][0]["version"] 
                                      if m["attributes"].get("version-statuses") else "unknown",
                            "status": m["attributes"]["status"],
                            "source": m["attributes"]["vcs-repo"]["identifier"]
                                     if m["attributes"].get("vcs-repo") else None
                        }
                        for m in modules
                    ]
                }
            
            elif params.action == "get":
                if not all([params.namespace, params.name, params.provider]):
                    return {
                        "success": False,
                        "error": "namespace, name, and provider required"
                    }
                
                module = await tfc_client.get_registry_module(
                    params.namespace,
                    params.name,
                    params.provider
                )
                
                return {
                    "success": True,
                    "module": {
                        "id": module["id"],
                        "name": module["attributes"]["name"],
                        "namespace": module["attributes"]["namespace"],
                        "provider": module["attributes"]["provider"],
                        "status": module["attributes"]["status"],
                        "versions": [
                            v["version"] 
                            for v in module["attributes"].get("version-statuses", [])
                        ],
                        "source": module["attributes"]["vcs-repo"]["identifier"]
                                 if module["attributes"].get("vcs-repo") else None
                    }
                }
            
            else:
                return {"success": False, "error": f"Unknown action: {params.action}"}
                
        except TerraformCloudError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error in registry operations")
            return {"success": False, "error": str(e)}
    
    tools.append(tfc_registry_operations)
    
    return tools