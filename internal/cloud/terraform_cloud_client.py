"""
Terraform Cloud API client for Terry-Form MCP v3.0.0
Implements complete Terraform Cloud API v2 integration
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from urllib.parse import urlencode, quote

import aiohttp
from aiohttp import ClientSession, ClientTimeout

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, max_requests_per_second: int = 10, burst_limit: int = 25):
        self.max_requests_per_second = max_requests_per_second
        self.burst_limit = burst_limit
        self.tokens = burst_limit
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token for making a request"""
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(
                self.burst_limit,
                self.tokens + elapsed * self.max_requests_per_second
            )
            self.last_update = now
            
            if self.tokens < 1:
                # Wait until we have a token
                wait_time = (1 - self.tokens) / self.max_requests_per_second
                await asyncio.sleep(wait_time)
                self.tokens = 1
                self.last_update = time.time()
            
            self.tokens -= 1


class TerraformCloudClient:
    """Terraform Cloud API v2 client"""
    
    def __init__(
        self,
        api_token: str,
        organization: str,
        api_endpoint: str = "https://app.terraform.io/api/v2",
        rate_limit: Optional[RateLimiter] = None
    ):
        self.api_token = api_token
        self.organization = organization
        self.api_endpoint = api_endpoint.rstrip("/")
        self.rate_limiter = rate_limit or RateLimiter()
        self.session: Optional[ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = ClientTimeout(total=300, connect=30, sock_read=30)
        self.session = ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/vnd.api+json"
            },
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an API request with rate limiting and error handling"""
        await self.rate_limiter.acquire()
        
        url = f"{self.api_endpoint}{path}"
        
        try:
            async with self.session.request(
                method,
                url,
                params=params,
                json=json_data,
                **kwargs
            ) as response:
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self._request(method, path, params, json_data, **kwargs)
                
                # Parse response
                text = await response.text()
                
                if response.status >= 400:
                    error_data = {}
                    try:
                        error_data = json.loads(text) if text else {}
                    except json.JSONDecodeError:
                        pass
                    
                    raise TerraformCloudError(
                        f"API request failed: {response.status}",
                        status_code=response.status,
                        response_data=error_data
                    )
                
                if not text:
                    return {}
                
                return json.loads(text)
                
        except aiohttp.ClientError as e:
            raise TerraformCloudError(f"Network error: {str(e)}")
    
    async def _paginate(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Paginate through API results"""
        if params is None:
            params = {}
        
        page_number = 1
        page_size = params.get("page[size]", 20)
        
        while True:
            params["page[number]"] = page_number
            params["page[size]"] = page_size
            
            response = await self._request("GET", path, params=params)
            
            # Yield items from this page
            data = response.get("data", [])
            for item in data:
                yield item
            
            # Check if there are more pages
            meta = response.get("meta", {})
            pagination = meta.get("pagination", {})
            
            if page_number >= pagination.get("total-pages", 1):
                break
            
            page_number += 1
    
    # Workspace Operations
    
    async def list_workspaces(
        self,
        search: Optional[str] = None,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """List workspaces in the organization"""
        params = {}
        
        if search:
            params["search[name]"] = search
        
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
        
        workspaces = []
        async for workspace in self._paginate(
            f"/organizations/{self.organization}/workspaces",
            params
        ):
            workspaces.append(workspace)
        
        return workspaces
    
    async def get_workspace(self, workspace_name: str) -> Dict[str, Any]:
        """Get a specific workspace"""
        response = await self._request(
            "GET",
            f"/organizations/{self.organization}/workspaces/{workspace_name}"
        )
        return response.get("data", {})
    
    async def create_workspace(
        self,
        name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new workspace"""
        data = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "name": name,
                    "auto-apply": kwargs.get("auto_apply", False),
                    "execution-mode": kwargs.get("execution_mode", "remote"),
                    "terraform-version": kwargs.get("terraform_version", "latest"),
                    "working-directory": kwargs.get("working_directory", ""),
                    **{k: v for k, v in kwargs.items() if k not in [
                        "auto_apply", "execution_mode", "terraform_version", "working_directory"
                    ]}
                }
            }
        }
        
        response = await self._request(
            "POST",
            f"/organizations/{self.organization}/workspaces",
            json_data=data
        )
        return response.get("data", {})
    
    async def update_workspace(
        self,
        workspace_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update a workspace"""
        # Convert pythonic names to API format
        attributes = {}
        mapping = {
            "auto_apply": "auto-apply",
            "execution_mode": "execution-mode",
            "terraform_version": "terraform-version",
            "working_directory": "working-directory"
        }
        
        for key, value in kwargs.items():
            api_key = mapping.get(key, key)
            attributes[api_key] = value
        
        data = {
            "data": {
                "type": "workspaces",
                "attributes": attributes
            }
        }
        
        response = await self._request(
            "PATCH",
            f"/workspaces/{workspace_id}",
            json_data=data
        )
        return response.get("data", {})
    
    async def delete_workspace(self, workspace_id: str):
        """Delete a workspace"""
        await self._request("DELETE", f"/workspaces/{workspace_id}")
    
    # Run Operations
    
    async def create_run(
        self,
        workspace_id: str,
        message: str = "Queued by Terry-Form MCP",
        is_destroy: bool = False,
        auto_apply: Optional[bool] = None,
        target_addrs: Optional[List[str]] = None,
        configuration_version_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new run"""
        attributes = {
            "message": message,
            "is-destroy": is_destroy
        }
        
        if auto_apply is not None:
            attributes["auto-apply"] = auto_apply
        
        if target_addrs:
            attributes["target-addrs"] = target_addrs
        
        data = {
            "data": {
                "type": "runs",
                "attributes": attributes,
                "relationships": {
                    "workspace": {
                        "data": {
                            "type": "workspaces",
                            "id": workspace_id
                        }
                    }
                }
            }
        }
        
        if configuration_version_id:
            data["data"]["relationships"]["configuration-version"] = {
                "data": {
                    "type": "configuration-versions",
                    "id": configuration_version_id
                }
            }
        
        response = await self._request("POST", "/runs", json_data=data)
        return response.get("data", {})
    
    async def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get run details"""
        response = await self._request("GET", f"/runs/{run_id}")
        return response.get("data", {})
    
    async def list_runs(
        self,
        workspace_id: str,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """List runs for a workspace"""
        params = {}
        
        if filters:
            for key, value in filters.items():
                params[f"filter[{key}]"] = value
        
        runs = []
        async for run in self._paginate(
            f"/workspaces/{workspace_id}/runs",
            params
        ):
            runs.append(run)
        
        return runs
    
    async def apply_run(self, run_id: str, comment: Optional[str] = None):
        """Apply a run"""
        data = {"comment": comment} if comment else {}
        await self._request(
            "POST",
            f"/runs/{run_id}/actions/apply",
            json_data=data
        )
    
    async def cancel_run(self, run_id: str, comment: Optional[str] = None):
        """Cancel a run"""
        data = {"comment": comment} if comment else {}
        await self._request(
            "POST",
            f"/runs/{run_id}/actions/cancel",
            json_data=data
        )
    
    async def discard_run(self, run_id: str, comment: Optional[str] = None):
        """Discard a run"""
        data = {"comment": comment} if comment else {}
        await self._request(
            "POST",
            f"/runs/{run_id}/actions/discard",
            json_data=data
        )
    
    async def get_run_logs(self, run_id: str, log_type: str = "plan") -> str:
        """Get run logs (plan or apply)"""
        # Get the plan or apply object
        run = await self.get_run(run_id)
        
        if log_type == "plan":
            log_url = run.get("attributes", {}).get("log-read-url")
        else:  # apply
            relationships = run.get("relationships", {})
            apply_data = relationships.get("apply", {}).get("data", {})
            if apply_data:
                apply_id = apply_data.get("id")
                apply_response = await self._request("GET", f"/applies/{apply_id}")
                apply_obj = apply_response.get("data", {})
                log_url = apply_obj.get("attributes", {}).get("log-read-url")
            else:
                log_url = None
        
        if not log_url:
            return ""
        
        # Stream logs from the URL
        async with self.session.get(log_url) as response:
            return await response.text()
    
    # State Operations
    
    async def get_current_state_version(self, workspace_id: str) -> Dict[str, Any]:
        """Get current state version for a workspace"""
        response = await self._request(
            "GET",
            f"/workspaces/{workspace_id}/current-state-version"
        )
        return response.get("data", {})
    
    async def list_state_versions(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List state versions for a workspace"""
        versions = []
        async for version in self._paginate(
            f"/workspaces/{workspace_id}/state-versions"
        ):
            versions.append(version)
        
        return versions
    
    async def get_state_version(self, state_version_id: str) -> Dict[str, Any]:
        """Get a specific state version"""
        response = await self._request(
            "GET",
            f"/state-versions/{state_version_id}"
        )
        return response.get("data", {})
    
    async def download_state(self, state_version_id: str) -> Dict[str, Any]:
        """Download state file content"""
        # Get the state version to get the download URL
        state_version = await self.get_state_version(state_version_id)
        download_url = state_version.get("attributes", {}).get("hosted-state-download-url")
        
        if not download_url:
            raise TerraformCloudError("No download URL available for state")
        
        async with self.session.get(download_url) as response:
            text = await response.text()
            return json.loads(text)
    
    # Variable Operations
    
    async def list_variables(self, workspace_id: str) -> List[Dict[str, Any]]:
        """List variables for a workspace"""
        variables = []
        async for variable in self._paginate(
            f"/workspaces/{workspace_id}/vars"
        ):
            variables.append(variable)
        
        return variables
    
    async def create_variable(
        self,
        workspace_id: str,
        key: str,
        value: str,
        category: str = "terraform",  # terraform or env
        description: str = "",
        sensitive: bool = False,
        hcl: bool = False
    ) -> Dict[str, Any]:
        """Create a workspace variable"""
        data = {
            "data": {
                "type": "vars",
                "attributes": {
                    "key": key,
                    "value": value,
                    "category": category,
                    "description": description,
                    "sensitive": sensitive,
                    "hcl": hcl
                },
                "relationships": {
                    "workspace": {
                        "data": {
                            "type": "workspaces",
                            "id": workspace_id
                        }
                    }
                }
            }
        }
        
        response = await self._request("POST", "/vars", json_data=data)
        return response.get("data", {})
    
    async def update_variable(
        self,
        variable_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update a variable"""
        data = {
            "data": {
                "type": "vars",
                "attributes": kwargs
            }
        }
        
        response = await self._request(
            "PATCH",
            f"/vars/{variable_id}",
            json_data=data
        )
        return response.get("data", {})
    
    async def delete_variable(self, variable_id: str):
        """Delete a variable"""
        await self._request("DELETE", f"/vars/{variable_id}")
    
    # Policy Operations
    
    async def list_policy_checks(self, run_id: str) -> List[Dict[str, Any]]:
        """List policy checks for a run"""
        checks = []
        async for check in self._paginate(f"/runs/{run_id}/policy-checks"):
            checks.append(check)
        
        return checks
    
    async def override_policy(
        self,
        policy_check_id: str,
        comment: Optional[str] = None
    ):
        """Override a policy check"""
        data = {}
        if comment:
            data = {"comment": comment}
        
        await self._request(
            "POST",
            f"/policy-checks/{policy_check_id}/actions/override",
            json_data=data
        )
    
    # Cost Estimation
    
    async def get_cost_estimate(self, run_id: str) -> Dict[str, Any]:
        """Get cost estimate for a run"""
        response = await self._request(
            "GET",
            f"/runs/{run_id}/cost-estimate"
        )
        return response.get("data", {})
    
    # Registry Operations
    
    async def list_registry_modules(
        self,
        namespace: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List modules from private registry"""
        if namespace is None:
            namespace = self.organization
        
        params = {}
        if provider:
            params["filter[provider]"] = provider
        
        modules = []
        async for module in self._paginate(
            f"/organizations/{namespace}/registry-modules",
            params
        ):
            modules.append(module)
        
        return modules
    
    async def get_registry_module(
        self,
        namespace: str,
        name: str,
        provider: str
    ) -> Dict[str, Any]:
        """Get a specific registry module"""
        response = await self._request(
            "GET",
            f"/registry-modules/{namespace}/{name}/{provider}"
        )
        return response.get("data", {})


class TerraformCloudError(Exception):
    """Terraform Cloud API error"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
        
        # Extract detailed error information
        errors = self.response_data.get("errors", [])
        if errors:
            error_messages = [e.get("detail", e.get("title", "")) for e in errors]
            self.message = f"{message}: {'; '.join(error_messages)}"
        else:
            self.message = message
    
    def __str__(self):
        return self.message