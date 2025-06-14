"""
Terry-Form MCP Server v3.0.0
Enhanced MCP server with GitHub App, Terraform Cloud, and Module Intelligence
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Import v3.0.0 components
from internal.github.github_app import GitHubApp, GitHubWebhookHandler
from internal.github.terraform_validator import TerraformPRValidator
from internal.cloud.terraform_cloud_client import TerraformCloudClient
from internal.cloud.terraform_cloud_tools import create_terraform_cloud_tools
from internal.analytics.module_intelligence import ModuleIntelligenceEngine

# Import existing components
from terraform_lsp_client import TerraformLSPClient
from internal.terraform.executor import TerraformExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TerryFormMCPv3:
    """Terry-Form MCP Server v3.0.0"""
    
    def __init__(self):
        self.mcp = FastMCP("Terry-Form MCP v3.0.0")
        self.terraform_executor = None
        self.lsp_client = None
        self.github_app = None
        self.github_webhook_handler = None
        self.tfc_client = None
        self.module_intelligence = None
        self.web_app = None
        
        # Configuration
        self.config = self._load_config()
        
        # Initialize components
        asyncio.create_task(self._initialize_components())
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            # Core settings
            "port": int(os.getenv("PORT", "8000")),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "workspace_path": Path(os.getenv("WORKSPACE_PATH", "/mnt/workspace")),
            
            # GitHub App settings
            "github_enabled": os.getenv("GITHUB_ENABLED", "false").lower() == "true",
            "github_app_id": os.getenv("GITHUB_APP_ID", ""),
            "github_private_key": os.getenv("GITHUB_PRIVATE_KEY", ""),
            "github_webhook_secret": os.getenv("GITHUB_WEBHOOK_SECRET", ""),
            "github_webhook_path": os.getenv("GITHUB_WEBHOOK_PATH", "/webhooks/github"),
            
            # Terraform Cloud settings
            "tfc_enabled": os.getenv("TFC_ENABLED", "false").lower() == "true",
            "tfc_token": os.getenv("TFC_TOKEN", ""),
            "tfc_organization": os.getenv("TFC_ORGANIZATION", ""),
            "tfc_endpoint": os.getenv("TFC_ENDPOINT", "https://app.terraform.io/api/v2"),
            
            # Module Intelligence settings
            "module_intelligence_enabled": os.getenv("MODULE_INTELLIGENCE_ENABLED", "false").lower() == "true",
            "module_cache_dir": Path(os.getenv("MODULE_CACHE_DIR", "/tmp/module_cache")),
            
            # LSP settings
            "lsp_enabled": os.getenv("LSP_ENABLED", "true").lower() == "true",
            "lsp_cache_dir": Path(os.getenv("LSP_CACHE_DIR", "/tmp/lsp_cache")),
            
            # Security settings
            "allowed_operations": os.getenv("ALLOWED_OPERATIONS", "init,validate,fmt,plan").split(","),
            "max_concurrent_operations": int(os.getenv("MAX_CONCURRENT_OPERATIONS", "10")),
        }
    
    async def _initialize_components(self):
        """Initialize all components asynchronously"""
        try:
            # Initialize Terraform executor
            self.terraform_executor = TerraformExecutor()
            
            # Initialize LSP client if enabled
            if self.config["lsp_enabled"]:
                self.lsp_client = TerraformLSPClient()
                await self.lsp_client.initialize()
                logger.info("LSP client initialized")
            
            # Initialize GitHub App if enabled
            if self.config["github_enabled"]:
                await self._initialize_github_app()
            
            # Initialize Terraform Cloud if enabled
            if self.config["tfc_enabled"]:
                await self._initialize_terraform_cloud()
            
            # Initialize Module Intelligence if enabled
            if self.config["module_intelligence_enabled"]:
                await self._initialize_module_intelligence()
            
            # Set up MCP tools
            await self._setup_mcp_tools()
            
            # Set up web endpoints
            await self._setup_web_app()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def _initialize_github_app(self):
        """Initialize GitHub App integration"""
        if not all([
            self.config["github_app_id"],
            self.config["github_private_key"],
            self.config["github_webhook_secret"]
        ]):
            logger.warning("GitHub App configuration incomplete, skipping initialization")
            return
        
        self.github_app = GitHubApp(
            app_id=self.config["github_app_id"],
            private_key=self.config["github_private_key"],
            webhook_secret=self.config["github_webhook_secret"]
        )
        
        # Create PR validator
        terraform_validator = TerraformPRValidator(
            self.github_app,
            self.terraform_executor,
            self.lsp_client
        )
        
        # Create webhook handler
        self.github_webhook_handler = GitHubWebhookHandler(
            self.github_app,
            terraform_validator
        )
        
        logger.info("GitHub App initialized")
    
    async def _initialize_terraform_cloud(self):
        """Initialize Terraform Cloud integration"""
        if not all([
            self.config["tfc_token"],
            self.config["tfc_organization"]
        ]):
            logger.warning("Terraform Cloud configuration incomplete, skipping initialization")
            return
        
        self.tfc_client = TerraformCloudClient(
            api_token=self.config["tfc_token"],
            organization=self.config["tfc_organization"],
            api_endpoint=self.config["tfc_endpoint"]
        )
        
        logger.info("Terraform Cloud client initialized")
    
    async def _initialize_module_intelligence(self):
        """Initialize Module Intelligence system"""
        if not self.lsp_client:
            logger.warning("LSP client required for Module Intelligence, skipping initialization")
            return
        
        cache_dir = self.config["module_cache_dir"]
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.module_intelligence = ModuleIntelligenceEngine(
            cache_dir=cache_dir,
            lsp_client=self.lsp_client
        )
        
        logger.info("Module Intelligence engine initialized")
    
    async def _setup_mcp_tools(self):
        """Set up all MCP tools"""
        # Add basic Terraform tools (recreate the core functionality)
        await self._add_basic_terraform_tools()
        
        # Add LSP tools if available
        if self.lsp_client:
            await self._add_lsp_tools()
        
        # Add Terraform Cloud tools
        if self.tfc_client:
            async with self.tfc_client:
                tfc_tools = await create_terraform_cloud_tools(self.tfc_client)
                for tool in tfc_tools:
                    self.mcp.add_tool(tool)
        
        # Add Module Intelligence tools
        if self.module_intelligence:
            await self._add_module_intelligence_tools()
        
        # Add GitHub integration tools
        if self.github_app:
            await self._add_github_tools()
        
        logger.info(f"Added {len(self.mcp.tools)} MCP tools")
    
    async def _add_basic_terraform_tools(self):
        """Add basic Terraform MCP tools"""
        from fastmcp import Tool
        from pydantic import BaseModel, Field
        from pathlib import Path
        
        class TerraformParams(BaseModel):
            path: str = Field(description="Path within workspace to run Terraform")
            actions: List[str] = Field(default=["plan"], description="Actions to run")
            vars: Dict[str, str] = Field(default={}, description="Terraform variables")
        
        @Tool()
        async def terry(params: TerraformParams) -> Dict[str, Any]:
            """Run Terraform actions in workspace with security restrictions"""
            try:
                full_path = Path("/mnt/workspace") / params.path
                results = []
                
                for action in params.actions:
                    if action in self.terraform_executor.disallowed_actions:
                        results.append({
                            "action": action,
                            "success": False,
                            "error": f"Action '{action}' is not allowed for security reasons"
                        })
                    else:
                        result = await self.terraform_executor.execute_terraform(
                            action, 
                            full_path, 
                            vars_dict=params.vars if action == "plan" else None
                        )
                        results.append({
                            "action": action,
                            "success": result["success"],
                            "output": result["output"],
                            "error": result["error"]
                        })
                
                return {"terry-results": results}
                
            except Exception as e:
                logger.exception("Error in terry tool")
                return {"terry-results": [{"error": str(e), "success": False}]}
        
        self.mcp.add_tool(terry)
        
        @Tool()
        async def terry_environment_check() -> Dict[str, Any]:
            """Check Terraform environment and installation"""
            try:
                result = await self.terraform_executor.execute_terraform(
                    "version", Path("/tmp")
                )
                
                return {
                    "success": result["success"],
                    "terraform_installed": result["success"],
                    "version_output": result["output"],
                    "workspace_accessible": os.path.exists("/mnt/workspace")
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "terraform_installed": False,
                    "workspace_accessible": False
                }
        
        self.mcp.add_tool(terry_environment_check)
    
    async def _add_lsp_tools(self):
        """Add LSP-based tools"""
        from fastmcp import Tool
        from pydantic import BaseModel, Field
        
        class LSPParams(BaseModel):
            file_path: str = Field(description="Path to Terraform file")
            content: Optional[str] = Field(None, description="File content for analysis")
        
        @Tool()
        async def terraform_validate_lsp(params: LSPParams) -> Dict[str, Any]:
            """Validate Terraform file using LSP"""
            try:
                if not self.lsp_client or not self.lsp_client.is_initialized():
                    return {"success": False, "error": "LSP client not available"}
                
                diagnostics = await self.lsp_client.get_diagnostics(params.file_path)
                
                return {
                    "success": True,
                    "diagnostics": diagnostics,
                    "file_path": params.file_path
                }
                
            except Exception as e:
                logger.exception("Error in LSP validation")
                return {"success": False, "error": str(e)}
        
        self.mcp.add_tool(terraform_validate_lsp)
    
    async def _add_module_intelligence_tools(self):
        """Add Module Intelligence MCP tools"""
        from fastmcp import Tool
        from pydantic import BaseModel, Field
        
        class ModuleAnalysisParams(BaseModel):
            module_paths: List[str] = Field(description="List of module paths to analyze")
            provider_updates: Dict[str, Dict[str, str]] = Field(
                description="Provider updates in format {provider: {old_version, new_version}}"
            )
        
        @Tool()
        async def analyze_provider_impact(params: ModuleAnalysisParams) -> Dict[str, Any]:
            """Analyze the impact of provider updates on Terraform modules"""
            try:
                # Convert string paths to Path objects
                module_paths = [Path(p) for p in params.module_paths]
                
                # Convert provider updates format
                provider_updates = {
                    provider: (versions["old_version"], versions["new_version"])
                    for provider, versions in params.provider_updates.items()
                }
                
                # Perform analysis
                report = await self.module_intelligence.analyze_provider_update_impact(
                    module_paths, provider_updates
                )
                
                return {
                    "success": True,
                    "analysis": report
                }
                
            except Exception as e:
                logger.exception("Error in provider impact analysis")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self.mcp.add_tool(analyze_provider_impact)
        
        class UpgradeRecommendationParams(BaseModel):
            current_providers: Dict[str, str] = Field(
                description="Current providers and versions {provider: version}"
            )
        
        @Tool()
        async def get_upgrade_recommendations(params: UpgradeRecommendationParams) -> Dict[str, Any]:
            """Get provider upgrade recommendations"""
            try:
                recommendations = await self.module_intelligence.get_provider_upgrade_recommendations(
                    params.current_providers
                )
                
                return {
                    "success": True,
                    "recommendations": recommendations
                }
                
            except Exception as e:
                logger.exception("Error getting upgrade recommendations")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self.mcp.add_tool(get_upgrade_recommendations)
    
    async def _add_github_tools(self):
        """Add GitHub integration MCP tools"""
        from fastmcp import Tool
        from pydantic import BaseModel, Field
        
        class GitHubRepoParams(BaseModel):
            repo_full_name: str = Field(description="Repository full name (owner/repo)")
            installation_id: int = Field(description="GitHub App installation ID")
        
        @Tool()
        async def validate_terraform_repo(params: GitHubRepoParams) -> Dict[str, Any]:
            """Validate Terraform configuration in a GitHub repository"""
            try:
                # This would implement repository-wide validation
                # For now, return a placeholder
                return {
                    "success": True,
                    "message": "Repository validation not yet implemented",
                    "repo": params.repo_full_name
                }
                
            except Exception as e:
                logger.exception("Error validating GitHub repository")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        self.mcp.add_tool(validate_terraform_repo)
    
    async def _setup_web_app(self):
        """Set up web application for webhooks and health checks"""
        self.web_app = web.Application()
        
        # Health check endpoints
        self.web_app.router.add_get("/health", self._health_check)
        self.web_app.router.add_get("/ready", self._readiness_check)
        
        # Metrics endpoint (if Prometheus monitoring is enabled)
        if os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true":
            self.web_app.router.add_get("/metrics", self._metrics_endpoint)
        
        # GitHub webhook endpoint
        if self.github_webhook_handler:
            self.web_app.router.add_post(
                self.config["github_webhook_path"],
                self.github_webhook_handler.handle_webhook
            )
    
    async def _health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        health_status = {
            "status": "healthy",
            "version": "3.0.0",
            "components": {
                "terraform_executor": self.terraform_executor is not None,
                "lsp_client": self.lsp_client is not None and self.lsp_client.is_initialized(),
                "github_app": self.github_app is not None,
                "terraform_cloud": self.tfc_client is not None,
                "module_intelligence": self.module_intelligence is not None
            }
        }
        
        return web.json_response(health_status)
    
    async def _readiness_check(self, request: web.Request) -> web.Response:
        """Readiness check endpoint"""
        ready = True
        
        # Check if required components are ready
        if self.config["lsp_enabled"] and not (self.lsp_client and self.lsp_client.is_initialized()):
            ready = False
        
        status_code = 200 if ready else 503
        return web.json_response(
            {"status": "ready" if ready else "not ready"},
            status=status_code
        )
    
    async def _metrics_endpoint(self, request: web.Request) -> web.Response:
        """Prometheus metrics endpoint"""
        # This would implement Prometheus metrics
        # For now, return basic metrics
        metrics = """
# HELP terry_form_mcp_tools_total Total number of MCP tools available
# TYPE terry_form_mcp_tools_total gauge
terry_form_mcp_tools_total {len(self.mcp.tools)}

# HELP terry_form_mcp_components_status Status of Terry-Form MCP components (1=healthy, 0=unhealthy)
# TYPE terry_form_mcp_components_status gauge
terry_form_mcp_components_terraform_executor {1 if self.terraform_executor else 0}
terry_form_mcp_components_lsp_client {1 if self.lsp_client and self.lsp_client.is_initialized() else 0}
terry_form_mcp_components_github_app {1 if self.github_app else 0}
terry_form_mcp_components_terraform_cloud {1 if self.tfc_client else 0}
terry_form_mcp_components_module_intelligence {1 if self.module_intelligence else 0}
        """
        
        return web.Response(text=metrics, content_type="text/plain")
    
    async def run(self):
        """Run the Terry-Form MCP server"""
        # Start MCP server
        mcp_task = asyncio.create_task(
            self.mcp.run(stdio=True)
        )
        
        # Start web server for webhooks and health checks
        runner = web.AppRunner(self.web_app)
        await runner.setup()
        
        site = web.TCPSite(runner, "0.0.0.0", self.config["port"])
        await site.start()
        
        logger.info(f"Terry-Form MCP v3.0.0 started on port {self.config['port']}")
        
        # Wait for tasks
        try:
            await asyncio.gather(mcp_task)
        except KeyboardInterrupt:
            logger.info("Shutting down Terry-Form MCP v3.0.0")
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """Clean up resources"""
        if self.lsp_client:
            await self.lsp_client.cleanup()
        
        if self.tfc_client:
            await self.tfc_client.__aexit__(None, None, None)
        
        if self.github_app:
            await self.github_app.__aexit__(None, None, None)


async def main():
    """Main entry point"""
    server = TerryFormMCPv3()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())