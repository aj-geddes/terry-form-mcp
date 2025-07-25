#!/usr/bin/env python3
"""
Terraform LSP Client - JSON-RPC client for terraform-ls Language Server

This module provides LSP client functionality to communicate with terraform-ls
and expose language server capabilities through MCP tools.
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Dict


class TerraformLSPClient:
    """LSP client for terraform-ls Language Server"""

    def __init__(self, workspace_root: str = "/mnt/workspace"):
        self.workspace_root = workspace_root
        self.terraform_ls_process = None
        self.request_id = 0
        self.pending_requests = {}
        self.initialized = False
        self.capabilities = {}
        self.initialization_error = None

        # Setup logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def _get_next_id(self) -> int:
        """Generate next request ID"""
        self.request_id += 1
        return self.request_id

    async def start_terraform_ls(self, workspace_path: str) -> bool:
        """Start terraform-ls process and initialize workspace"""
        try:
            self.logger.info(f"Starting terraform-ls for workspace: {workspace_path}")

            # Ensure workspace path exists
            if not os.path.exists(workspace_path):
                self.logger.error(f"Workspace path does not exist: {workspace_path}")
                self.initialization_error = (
                    f"Workspace path does not exist: {workspace_path}"
                )
                return False

            # Ensure terraform-ls binary exists
            result = subprocess.run(
                ["which", "terraform-ls"], capture_output=True, text=True
            )
            if result.returncode != 0:
                self.logger.error("terraform-ls binary not found")
                self.initialization_error = "terraform-ls binary not found"
                return False

            self.logger.info(f"terraform-ls found at: {result.stdout.strip()}")

            # Test terraform-ls version
            version_result = subprocess.run(
                ["terraform-ls", "version"], capture_output=True, text=True
            )
            if version_result.returncode == 0:
                self.logger.info(
                    f"terraform-ls version: {version_result.stdout.strip()}"
                )

            # Start terraform-ls process
            self.logger.info("Starting terraform-ls serve process...")
            self.terraform_ls_process = await asyncio.create_subprocess_exec(
                "terraform-ls",
                "serve",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path,
            )

            # Give the process a moment to start
            await asyncio.sleep(0.1)

            # Check if process is still running
            if self.terraform_ls_process.returncode is not None:
                stderr = await self.terraform_ls_process.stderr.read()
                self.logger.error(
                    f"terraform-ls process exited immediately: {stderr.decode()}"
                )
                self.initialization_error = (
                    f"terraform-ls process exited: {stderr.decode()}"
                )
                return False

            self.logger.info("terraform-ls process started successfully")

            # Initialize the LSP connection
            init_success = await self._initialize(workspace_path)
            if not init_success:
                self.logger.error("LSP initialization failed")
                return False

            self.logger.info("LSP client initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start terraform-ls: {e}")
            self.initialization_error = str(e)
            return False

    async def _send_request(self, method: str, params: Dict = None) -> Dict:
        """Send JSON-RPC request to terraform-ls"""
        if not self.terraform_ls_process:
            raise RuntimeError("terraform-ls process not started")

        request_id = self._get_next_id()
        request = {"jsonrpc": "2.0", "id": request_id, "method": method}

        if params:
            request["params"] = params

        self.logger.debug(f"Sending LSP request: {method}")

        # Send request
        request_json = json.dumps(request)
        content_length = len(request_json.encode("utf-8"))

        message = f"Content-Length: {content_length}\r\n\r\n{request_json}"

        try:
            self.terraform_ls_process.stdin.write(message.encode("utf-8"))
            await self.terraform_ls_process.stdin.drain()

            # Read response with timeout
            response = await asyncio.wait_for(self._read_response(), timeout=30.0)
            self.logger.debug(f"Received LSP response for {method}")
            return response

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout waiting for response to {method}")
            raise RuntimeError(f"Timeout waiting for response to {method}")
        except Exception as e:
            self.logger.error(f"Error sending request {method}: {e}")
            raise

    async def _read_response(self) -> Dict:
        """Read JSON-RPC response from terraform-ls"""
        # Read headers
        headers = {}
        while True:
            line = await self.terraform_ls_process.stdout.readline()
            if not line:
                raise RuntimeError("Connection closed while reading headers")

            line = line.decode("utf-8").strip()

            if not line:
                break

            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # Read content
        content_length = int(headers.get("Content-Length", 0))
        if content_length > 0:
            content = await self.terraform_ls_process.stdout.read(content_length)
            if not content:
                raise RuntimeError("Connection closed while reading content")
            return json.loads(content.decode("utf-8"))

        return {}

    async def _initialize(self, workspace_path: str) -> bool:
        """Initialize LSP connection with terraform-ls"""
        try:
            self.logger.info(f"Initializing LSP for workspace: {workspace_path}")

            params = {
                "processId": os.getpid(),
                "clientInfo": {"name": "terry-form-mcp", "version": "1.0.0"},
                "rootUri": f"file://{workspace_path}",
                "capabilities": {
                    "textDocument": {
                        "completion": {
                            "completionItem": {
                                "snippetSupport": True,
                                "documentationFormat": ["markdown", "plaintext"],
                            }
                        },
                        "hover": {"contentFormat": ["markdown", "plaintext"]},
                        "diagnostic": {},
                        "formatting": {},
                    },
                    "workspace": {"workspaceFolders": True, "configuration": True},
                },
            }

            response = await self._send_request("initialize", params)

            if "result" in response:
                self.capabilities = response["result"].get("capabilities", {})
                self.logger.info(
                    f"Server capabilities: {list(self.capabilities.keys())}"
                )

                # Send initialized notification
                await self._send_notification("initialized", {})
                self.initialized = True
                self.logger.info("LSP initialization completed")
                return True
            elif "error" in response:
                self.logger.error(f"LSP initialization error: {response['error']}")
                self.initialization_error = f"LSP error: {response['error']}"
                return False
            else:
                self.logger.error(f"Unexpected LSP response: {response}")
                self.initialization_error = f"Unexpected response: {response}"
                return False

        except Exception as e:
            self.logger.error(f"LSP initialization failed: {e}")
            self.initialization_error = str(e)
            return False

    async def _send_notification(self, method: str, params: Dict = None):
        """Send JSON-RPC notification to terraform-ls"""
        notification = {"jsonrpc": "2.0", "method": method}

        if params:
            notification["params"] = params

        self.logger.debug(f"Sending LSP notification: {method}")

        notification_json = json.dumps(notification)
        content_length = len(notification_json.encode("utf-8"))

        message = f"Content-Length: {content_length}\r\n\r\n{notification_json}"

        self.terraform_ls_process.stdin.write(message.encode("utf-8"))
        await self.terraform_ls_process.stdin.drain()

    async def validate_document(self, file_path: str) -> Dict:
        """Get diagnostics for a Terraform file"""
        try:
            if not self.initialized:
                return {
                    "error": "LSP client not initialized",
                    "initialization_error": self.initialization_error,
                }

            # Notify LSP about document open
            file_uri = f"file://{file_path}"

            # Read file content
            if not os.path.exists(file_path):
                return {"error": f"File does not exist: {file_path}"}

            with open(file_path, "r") as f:
                content = f.read()

            await self._send_notification(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": file_uri,
                        "languageId": "terraform",
                        "version": 1,
                        "text": content,
                    }
                },
            )

            # Wait a bit for diagnostics
            await asyncio.sleep(1.0)

            # For now, return success - in full implementation we'd listen for diagnostics
            return {
                "success": True,
                "uri": file_uri,
                "diagnostics": [],
                "message": "Document opened successfully, diagnostics would be provided via separate channel",
            }

        except Exception as e:
            return {"error": str(e)}

    async def get_hover_info(self, file_path: str, line: int, character: int) -> Dict:
        """Get hover information for a position in a Terraform file"""
        try:
            if not self.initialized:
                return {
                    "error": "LSP client not initialized",
                    "initialization_error": self.initialization_error,
                }

            file_uri = f"file://{file_path}"

            # First open the document
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read()

                await self._send_notification(
                    "textDocument/didOpen",
                    {
                        "textDocument": {
                            "uri": file_uri,
                            "languageId": "terraform",
                            "version": 1,
                            "text": content,
                        }
                    },
                )

                # Small delay to let LSP process the document
                await asyncio.sleep(0.1)

            response = await self._send_request(
                "textDocument/hover",
                {
                    "textDocument": {"uri": file_uri},
                    "position": {"line": line, "character": character},
                },
            )

            if "result" in response and response["result"]:
                hover_content = response["result"].get("contents", {})
                return {"success": True, "hover": hover_content}

            return {
                "success": True,
                "hover": None,
                "message": "No hover information available",
            }

        except Exception as e:
            return {"error": str(e)}

    async def get_completions(self, file_path: str, line: int, character: int) -> Dict:
        """Get completion suggestions for a position in a Terraform file"""
        try:
            if not self.initialized:
                return {
                    "error": "LSP client not initialized",
                    "initialization_error": self.initialization_error,
                }

            file_uri = f"file://{file_path}"

            # First open the document
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read()

                await self._send_notification(
                    "textDocument/didOpen",
                    {
                        "textDocument": {
                            "uri": file_uri,
                            "languageId": "terraform",
                            "version": 1,
                            "text": content,
                        }
                    },
                )

                # Small delay to let LSP process the document
                await asyncio.sleep(0.1)

            response = await self._send_request(
                "textDocument/completion",
                {
                    "textDocument": {"uri": file_uri},
                    "position": {"line": line, "character": character},
                },
            )

            if "result" in response:
                completions = response["result"]
                if isinstance(completions, list):
                    return {"success": True, "completions": completions}
                elif isinstance(completions, dict) and "items" in completions:
                    return {"success": True, "completions": completions["items"]}

            return {"success": True, "completions": []}

        except Exception as e:
            return {"error": str(e)}

    async def format_document(self, file_path: str) -> Dict:
        """Format a Terraform document"""
        try:
            if not self.initialized:
                return {
                    "error": "LSP client not initialized",
                    "initialization_error": self.initialization_error,
                }

            file_uri = f"file://{file_path}"

            # First open the document
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read()

                await self._send_notification(
                    "textDocument/didOpen",
                    {
                        "textDocument": {
                            "uri": file_uri,
                            "languageId": "terraform",
                            "version": 1,
                            "text": content,
                        }
                    },
                )

                # Small delay to let LSP process the document
                await asyncio.sleep(0.1)

            response = await self._send_request(
                "textDocument/formatting",
                {
                    "textDocument": {"uri": file_uri},
                    "options": {"tabSize": 2, "insertSpaces": True},
                },
            )

            if "result" in response:
                edits = response["result"]
                return {"success": True, "edits": edits}

            return {"success": True, "edits": []}

        except Exception as e:
            return {"error": str(e)}

    async def shutdown(self):
        """Shutdown the LSP client and terraform-ls process"""
        try:
            if self.initialized:
                await self._send_request("shutdown")
                await self._send_notification("exit")

            if self.terraform_ls_process:
                self.terraform_ls_process.terminate()
                await self.terraform_ls_process.wait()

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


# Global LSP client instance
_lsp_client = None


async def get_lsp_client(workspace_path: str = None) -> TerraformLSPClient:
    """Get or create LSP client instance"""
    global _lsp_client

    if _lsp_client is None:
        _lsp_client = TerraformLSPClient()
        if workspace_path and not _lsp_client.initialized:
            success = await _lsp_client.start_terraform_ls(workspace_path)
            if not success:
                # Reset client on failure so next call will retry
                _lsp_client = None
                raise RuntimeError(
                    f"Failed to initialize LSP client: {_lsp_client.initialization_error if _lsp_client else 'Unknown error'}"
                )

    return _lsp_client
