"""
GitHub App integration for Terry-Form MCP v3.0.0
Handles webhook events, PR validation, and GitHub API interactions
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import jwt
from aiohttp import web

logger = logging.getLogger(__name__)


class GitHubApp:
    """GitHub App client for Terry-Form MCP"""
    
    def __init__(self, app_id: str, private_key: str, webhook_secret: str):
        self.app_id = app_id
        self.private_key = private_key
        self.webhook_secret = webhook_secret
        self.session = None
        self._jwt_cache = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication"""
        # Check cache first
        cache_key = "app_jwt"
        if cache_key in self._jwt_cache:
            token, expiry = self._jwt_cache[cache_key]
            if datetime.utcnow() < expiry:
                return token
        
        # Generate new JWT
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 60 seconds ago
            "exp": now + 600,  # Expires in 10 minutes
            "iss": self.app_id
        }
        
        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        
        # Cache the token
        self._jwt_cache[cache_key] = (token, datetime.utcnow() + timedelta(minutes=9))
        
        return token
    
    async def get_installation_token(self, installation_id: int) -> str:
        """Get an installation access token"""
        cache_key = f"installation_{installation_id}"
        
        # Check cache
        if cache_key in self._jwt_cache:
            token, expiry = self._jwt_cache[cache_key]
            if datetime.utcnow() < expiry:
                return token
        
        # Get new token
        jwt_token = self.generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json"
        }
        
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        async with self.session.post(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            
        token = data["token"]
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        
        # Cache with 5-minute buffer
        self._jwt_cache[cache_key] = (token, expires_at - timedelta(minutes=5))
        
        return token
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature"""
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(f"sha256={expected}", signature)
    
    async def create_check_run(
        self,
        installation_id: int,
        repo_full_name: str,
        head_sha: str,
        name: str,
        status: str = "in_progress",
        conclusion: Optional[str] = None,
        output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create or update a check run"""
        token = await self.get_installation_token(installation_id)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        }
        
        data = {
            "name": name,
            "head_sha": head_sha,
            "status": status
        }
        
        if conclusion:
            data["conclusion"] = conclusion
            data["completed_at"] = datetime.utcnow().isoformat() + "Z"
            
        if output:
            data["output"] = output
        
        url = f"https://api.github.com/repos/{repo_full_name}/check-runs"
        async with self.session.post(url, headers=headers, json=data) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def create_pr_comment(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        body: str
    ) -> Dict[str, Any]:
        """Create a comment on a pull request"""
        token = await self.get_installation_token(installation_id)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        }
        
        data = {"body": body}
        
        url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
        async with self.session.post(url, headers=headers, json=data) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def get_pr_files(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int
    ) -> List[Dict[str, Any]]:
        """Get list of files changed in a pull request"""
        token = await self.get_installation_token(installation_id)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        }
        
        files = []
        page = 1
        per_page = 100
        
        while True:
            url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/files"
            params = {"page": page, "per_page": per_page}
            
            async with self.session.get(url, headers=headers, params=params) as resp:
                resp.raise_for_status()
                page_files = await resp.json()
                
                if not page_files:
                    break
                    
                files.extend(page_files)
                
                if len(page_files) < per_page:
                    break
                    
                page += 1
        
        return files
    
    async def get_file_content(
        self,
        installation_id: int,
        repo_full_name: str,
        path: str,
        ref: str
    ) -> str:
        """Get file content from repository"""
        token = await self.get_installation_token(installation_id)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.raw"
        }
        
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
        params = {"ref": ref}
        
        async with self.session.get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            return await resp.text()


class GitHubWebhookHandler:
    """Handles GitHub webhook events"""
    
    def __init__(self, github_app: GitHubApp, terraform_validator):
        self.github_app = github_app
        self.terraform_validator = terraform_validator
        
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming GitHub webhook"""
        # Verify signature
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = await request.read()
        
        if not self.github_app.verify_webhook_signature(body, signature):
            return web.Response(text="Invalid signature", status=401)
        
        # Parse event
        event_type = request.headers.get("X-GitHub-Event", "")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return web.Response(text="Invalid JSON", status=400)
        
        # Route to appropriate handler
        if event_type == "pull_request":
            await self.handle_pull_request(payload)
        elif event_type == "push":
            await self.handle_push(payload)
        elif event_type == "check_run":
            await self.handle_check_run(payload)
        
        return web.Response(text="OK", status=200)
    
    async def handle_pull_request(self, payload: Dict[str, Any]):
        """Handle pull request events"""
        action = payload.get("action")
        if action not in ["opened", "synchronize", "reopened"]:
            return
        
        pr = payload["pull_request"]
        repo = payload["repository"]
        installation_id = payload["installation"]["id"]
        
        # Start validation
        await self.validate_terraform_pr(
            installation_id,
            repo["full_name"],
            pr["number"],
            pr["head"]["sha"]
        )
    
    async def handle_push(self, payload: Dict[str, Any]):
        """Handle push events"""
        # Could be used for branch protection or other validations
        pass
    
    async def handle_check_run(self, payload: Dict[str, Any]):
        """Handle check run events"""
        # Could be used for re-running checks
        pass
    
    async def validate_terraform_pr(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        head_sha: str
    ):
        """Validate Terraform configuration in a pull request"""
        # Create initial check run
        check_run = await self.github_app.create_check_run(
            installation_id,
            repo_full_name,
            head_sha,
            "Terry-Form Validation",
            status="in_progress"
        )
        
        try:
            # Get PR files
            files = await self.github_app.get_pr_files(
                installation_id,
                repo_full_name,
                pr_number
            )
            
            # Filter Terraform files
            tf_files = [
                f for f in files
                if f["filename"].endswith((".tf", ".tfvars"))
            ]
            
            if not tf_files:
                await self.github_app.create_check_run(
                    installation_id,
                    repo_full_name,
                    head_sha,
                    "Terry-Form Validation",
                    status="completed",
                    conclusion="neutral",
                    output={
                        "title": "No Terraform Files",
                        "summary": "No Terraform files found in this pull request."
                    }
                )
                return
            
            # Run validation
            results = await self.terraform_validator.validate_files(
                installation_id,
                repo_full_name,
                pr_number,
                tf_files
            )
            
            # Update check run with results
            conclusion = "success" if results["valid"] else "failure"
            
            await self.github_app.create_check_run(
                installation_id,
                repo_full_name,
                head_sha,
                "Terry-Form Validation",
                status="completed",
                conclusion=conclusion,
                output={
                    "title": results["title"],
                    "summary": results["summary"],
                    "annotations": results.get("annotations", [])
                }
            )
            
            # Create PR comment with detailed results
            if results.get("comment"):
                await self.github_app.create_pr_comment(
                    installation_id,
                    repo_full_name,
                    pr_number,
                    results["comment"]
                )
                
        except Exception as e:
            logger.exception("Error validating PR")
            await self.github_app.create_check_run(
                installation_id,
                repo_full_name,
                head_sha,
                "Terry-Form Validation",
                status="completed",
                conclusion="failure",
                output={
                    "title": "Validation Error",
                    "summary": f"An error occurred during validation: {str(e)}"
                }
            )