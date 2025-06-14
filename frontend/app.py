#!/usr/bin/env python3
"""
Terry-Form MCP Frontend
A web interface for testing Terry-Form MCP and accessing LSP documentation
"""
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from aiohttp import web, ClientSession
import aiohttp_cors
from mcp_simple_client import SimpleMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "7575"))

class TerryFormFrontend:
    def __init__(self):
        self.app = web.Application()
        self.mcp_client = SimpleMCPClient(MCP_SERVER_URL)
        self.setup_routes()
        self.setup_cors()
        
    def setup_cors(self):
        """Setup CORS for the frontend"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Configure CORS on all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/health', self.health_check)
        self.app.router.add_post('/api/mcp/call', self.mcp_call)
        self.app.router.add_get('/api/mcp/tools', self.list_tools)
        self.app.router.add_post('/api/terraform/{action}', self.terraform_action)
        self.app.router.add_get('/api/workspace', self.list_workspace)
    
    async def index(self, request):
        """Serve the main HTML page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terry-Form MCP Testing Interface</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-hcl.min.js"></script>
</head>
<body class="bg-gray-100">
    <div x-data="terryFormApp()" class="container mx-auto px-4 py-8">
        <header class="mb-8">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">Terry-Form MCP Testing Interface</h1>
            <p class="text-gray-600">Test Terraform operations and explore LSP documentation</p>
            <div class="mt-4 flex items-center space-x-4">
                <div :class="serverStatus === 'connected' ? 'bg-green-100' : 'bg-red-100'" class="px-3 py-1 rounded-full">
                    <span :class="serverStatus === 'connected' ? 'text-green-800' : 'text-red-800'" class="text-sm font-medium">
                        Server: <span x-text="serverStatus"></span>
                    </span>
                </div>
                <button @click="checkServerStatus" class="text-blue-600 hover:text-blue-800 text-sm">
                    Refresh Status
                </button>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Tools Panel -->
            <div class="lg:col-span-1">
                <div class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-xl font-semibold mb-4">Available Tools</h2>
                    <div class="space-y-2">
                        <template x-for="tool in tools" :key="tool.name">
                            <button 
                                @click="selectTool(tool)"
                                :class="selectedTool?.name === tool.name ? 'bg-blue-50 border-blue-500' : 'bg-gray-50 border-gray-300'"
                                class="w-full text-left p-3 border rounded hover:bg-gray-100 transition">
                                <div class="font-medium" x-text="tool.name"></div>
                                <div class="text-sm text-gray-600 mt-1" x-text="tool.description"></div>
                            </button>
                        </template>
                    </div>
                </div>

                <!-- Workspace Browser -->
                <div class="bg-white rounded-lg shadow p-6 mt-6">
                    <h2 class="text-xl font-semibold mb-4">Workspace Browser</h2>
                    <button @click="loadWorkspace" class="mb-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                        Refresh Workspace
                    </button>
                    <div class="space-y-1">
                        <template x-for="item in workspaceItems" :key="item.path">
                            <div class="flex items-center space-x-2 p-2 hover:bg-gray-50 rounded">
                                <span x-text="item.type === 'directory' ? '📁' : '📄'"></span>
                                <span class="text-sm" x-text="item.name"></span>
                            </div>
                        </template>
                    </div>
                </div>
            </div>

            <!-- Main Content -->
            <div class="lg:col-span-2">
                <!-- Tool Execution -->
                <div class="bg-white rounded-lg shadow p-6 mb-6">
                    <h2 class="text-xl font-semibold mb-4">Tool Execution</h2>
                    
                    <div x-show="selectedTool" class="space-y-4">
                        <h3 class="font-medium text-lg" x-text="selectedTool?.name"></h3>
                        
                        <!-- Dynamic input fields -->
                        <div class="space-y-3">
                            <template x-for="(param, key) in selectedTool?.inputSchema?.properties" :key="key">
                                <div>
                                    <label :for="key" class="block text-sm font-medium text-gray-700 mb-1">
                                        <span x-text="key"></span>
                                        <span x-show="selectedTool?.inputSchema?.required?.includes(key)" class="text-red-500">*</span>
                                    </label>
                                    <input 
                                        :id="key"
                                        :type="param.type === 'number' ? 'number' : 'text'"
                                        x-model="toolInputs[key]"
                                        class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        :placeholder="param.description"
                                    />
                                </div>
                            </template>
                        </div>
                        
                        <button 
                            @click="executeTool"
                            :disabled="executing"
                            class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-gray-400">
                            <span x-show="!executing">Execute Tool</span>
                            <span x-show="executing">Executing...</span>
                        </button>
                    </div>
                    
                    <div x-show="!selectedTool" class="text-gray-500">
                        Select a tool from the left panel to begin
                    </div>
                </div>

                <!-- Results -->
                <div x-show="lastResult" class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-xl font-semibold mb-4">Execution Results</h2>
                    
                    <div class="mb-4">
                        <span class="text-sm text-gray-600">Executed at: </span>
                        <span class="text-sm" x-text="lastResult?.timestamp"></span>
                    </div>
                    
                    <div class="bg-gray-900 rounded p-4 overflow-x-auto">
                        <pre><code class="language-json" x-text="JSON.stringify(lastResult?.result, null, 2)"></code></pre>
                    </div>
                </div>

                <!-- Clone Repository -->
                <div class="bg-white rounded-lg shadow p-6 mt-6">
                    <h2 class="text-xl font-semibold mb-4">Clone Repository</h2>
                    <div class="space-y-3">
                        <input 
                            type="text" 
                            x-model="repoUrl" 
                            placeholder="https://github.com/user/repo"
                            class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <button 
                            @click="cloneRepo()" 
                            :disabled="!repoUrl || cloning"
                            class="w-full bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:bg-gray-400">
                            <span x-show="!cloning">Clone Repository</span>
                            <span x-show="cloning">Cloning...</span>
                        </button>
                    </div>
                    <div class="mt-3 text-sm text-gray-600">
                        Popular examples:
                        <ul class="mt-1 space-y-1">
                            <li>• <a href="#" @click.prevent="repoUrl='https://github.com/terraform-aws-modules/terraform-aws-vpc'" class="text-blue-600 hover:underline">AWS VPC Module</a></li>
                            <li>• <a href="#" @click.prevent="repoUrl='https://github.com/terraform-aws-modules/terraform-aws-eks'" class="text-blue-600 hover:underline">AWS EKS Module</a></li>
                            <li>• <a href="#" @click.prevent="repoUrl='https://github.com/terraform-google-modules/terraform-google-kubernetes-engine'" class="text-blue-600 hover:underline">GCP GKE Module</a></li>
                        </ul>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="bg-white rounded-lg shadow p-6 mt-6">
                    <h2 class="text-xl font-semibold mb-4">Quick Actions</h2>
                    <div class="grid grid-cols-2 gap-4">
                        <button @click="quickAction('init')" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                            Terraform Init
                        </button>
                        <button @click="quickAction('validate')" class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700">
                            Terraform Validate
                        </button>
                        <button @click="quickAction('fmt')" class="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700">
                            Terraform Format Check
                        </button>
                        <button @click="quickAction('plan')" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                            Terraform Plan
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    function terryFormApp() {
        return {
            serverStatus: 'checking',
            tools: [],
            selectedTool: null,
            toolInputs: {},
            executing: false,
            lastResult: null,
            workspaceItems: [],
            repoUrl: '',
            cloning: false,
            
            async init() {
                await this.checkServerStatus();
                await this.loadTools();
                await this.loadWorkspace();
            },
            
            async checkServerStatus() {
                try {
                    const response = await fetch('/api/health');
                    if (response.ok) {
                        this.serverStatus = 'connected';
                    } else {
                        this.serverStatus = 'disconnected';
                    }
                } catch (error) {
                    this.serverStatus = 'error';
                }
            },
            
            async loadTools() {
                try {
                    const response = await fetch('/api/mcp/tools');
                    const data = await response.json();
                    this.tools = data.tools || [];
                } catch (error) {
                    console.error('Failed to load tools:', error);
                }
            },
            
            async loadWorkspace() {
                try {
                    const response = await fetch('/api/workspace');
                    const data = await response.json();
                    this.workspaceItems = data.items || [];
                } catch (error) {
                    console.error('Failed to load workspace:', error);
                }
            },
            
            selectTool(tool) {
                this.selectedTool = tool;
                this.toolInputs = {};
                // Initialize inputs with defaults
                if (tool.inputSchema?.properties) {
                    Object.keys(tool.inputSchema.properties).forEach(key => {
                        this.toolInputs[key] = '';
                    });
                }
            },
            
            async executeTool() {
                if (!this.selectedTool) return;
                
                this.executing = true;
                try {
                    const response = await fetch('/api/mcp/call', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            tool: this.selectedTool.name,
                            arguments: this.toolInputs
                        })
                    });
                    
                    const result = await response.json();
                    this.lastResult = {
                        timestamp: new Date().toLocaleString(),
                        tool: this.selectedTool.name,
                        result: result
                    };
                    
                    // Refresh workspace if tool might have changed it
                    if (['terraform_init', 'terraform_plan'].includes(this.selectedTool.name)) {
                        await this.loadWorkspace();
                    }
                    
                    // Re-highlight code
                    setTimeout(() => Prism.highlightAll(), 100);
                } catch (error) {
                    this.lastResult = {
                        timestamp: new Date().toLocaleString(),
                        tool: this.selectedTool.name,
                        result: { error: error.message }
                    };
                } finally {
                    this.executing = false;
                }
            },
            
            async quickAction(action) {
                const tool = this.tools.find(t => t.name === `terraform_${action}`);
                if (tool) {
                    this.selectTool(tool);
                    // Set default path
                    if (this.toolInputs.path !== undefined) {
                        this.toolInputs.path = 'test';
                    }
                    await this.executeTool();
                }
            },
            
            async cloneRepo() {
                if (!this.repoUrl || this.cloning) return;
                
                this.cloning = true;
                try {
                    const response = await fetch('/api/mcp/call', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            tool: 'clone_repository',
                            arguments: { repo_url: this.repoUrl }
                        })
                    });
                    
                    const result = await response.json();
                    if (result.result?.content?.[0]?.text) {
                        const data = JSON.parse(result.result.content[0].text);
                        if (data.success) {
                            alert(`Successfully cloned repository to: ${data.path}`);
                            // Refresh workspace
                            await this.loadWorkspace();
                            // Clear the input
                            this.repoUrl = '';
                        } else {
                            alert(`Clone failed: ${data.error}`);
                        }
                    } else if (result.error) {
                        alert(`Clone failed: ${result.error}`);
                    }
                } catch (error) {
                    alert(`Clone failed: ${error.message}`);
                } finally {
                    this.cloning = false;
                }
            }
        }
    }
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
    
    async def health_check(self, request):
        """Check if MCP server is accessible"""
        try:
            async with ClientSession() as session:
                # Check health on port 8001
                async with session.get("http://localhost:8001/health", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Also check if MCP is responding
                        headers = {
                            "Content-Type": "application/json",
                            "Accept": "application/json, text/event-stream"
                        }
                        test_payload = {"jsonrpc": "2.0", "method": "initialize", "id": 0}
                        async with session.post(f"{MCP_SERVER_URL}/mcp/sse", json=test_payload, headers=headers) as mcp_resp:
                            mcp_ok = mcp_resp.status < 500
                        
                        return web.json_response({"status": "connected" if mcp_ok else "partial", "server": data})
                    else:
                        return web.json_response({"status": "disconnected"}, status=503)
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=503)
    
    async def list_tools(self, request):
        """List available MCP tools"""
        try:
            result = await self.mcp_client.list_tools()
            if "result" in result:
                return web.json_response({"tools": result["result"].get("tools", [])})
            else:
                return web.json_response({"tools": [], "error": result.get("error")})
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return web.json_response({"tools": [], "error": str(e)})
    
    async def mcp_call(self, request):
        """Execute an MCP tool"""
        try:
            data = await request.json()
            tool_name = data.get("tool")
            arguments = data.get("arguments", {})
            
            result = await self.mcp_client.call_tool(tool_name, arguments)
            return web.json_response(result)
                    
        except Exception as e:
            logger.error(f"MCP call failed: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def terraform_action(self, request):
        """Quick terraform action endpoint"""
        action = request.match_info['action']
        try:
            data = await request.json() if request.can_read_body else {}
            path = data.get("path", "test")
            
            tool_name = f"terraform_{action}"
            return await self.mcp_call(web.Request.clone(request, json_data={
                "tool": tool_name,
                "arguments": {"path": path}
            }))
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def list_workspace(self, request):
        """List workspace contents"""
        try:
            result = await self.mcp_client.call_tool("workspace_list", {})
            if "result" in result:
                workspace_data = result["result"].get("content", [{}])[0].get("text", "{}")
                try:
                    parsed = json.loads(workspace_data)
                    items = parsed.get("workspace_list", {}).get("items", [])
                    return web.json_response({"items": items})
                except:
                    return web.json_response({"items": []})
            else:
                return web.json_response({"items": []})
        except Exception as e:
            logger.error(f"Failed to list workspace: {e}")
            return web.json_response({"items": [], "error": str(e)})
    
    def run(self):
        """Start the frontend server"""
        logger.info(f"Starting Terry-Form MCP Frontend on port {FRONTEND_PORT}")
        logger.info(f"Connecting to MCP server at {MCP_SERVER_URL}")
        web.run_app(self.app, host='0.0.0.0', port=FRONTEND_PORT)

def main():
    frontend = TerryFormFrontend()
    frontend.run()

if __name__ == "__main__":
    main()