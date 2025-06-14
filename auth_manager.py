#!/usr/bin/env python3
"""
Authentication Manager for Terry-Form MCP
Handles GitHub and Azure credentials from Kubernetes secrets
"""
import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

import jwt
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from github import Github
import subprocess

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Manages authentication for GitHub and Azure services"""
    
    def __init__(self):
        self.secrets_path = Path("/var/run/secrets")
        self.github_auth = None
        self.azure_auth = None
        self._load_credentials()
    
    def _load_credentials(self):
        """Load credentials from Kubernetes secrets"""
        try:
            # Load GitHub credentials
            github_secret_path = self.secrets_path / "github-auth" / "credentials"
            if github_secret_path.exists():
                github_data = json.loads(github_secret_path.read_text())
                self.github_auth = self._parse_github_credentials(github_data)
                logger.info("GitHub credentials loaded successfully")
            
            # Load Azure credentials  
            azure_secret_path = self.secrets_path / "azure-auth" / "credentials"
            if azure_secret_path.exists():
                azure_data = json.loads(azure_secret_path.read_text())
                self.azure_auth = self._parse_azure_credentials(azure_data)
                logger.info("Azure credentials loaded successfully")
                
        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")
    
    def _parse_github_credentials(self, data: Dict) -> Dict:
        """Parse GitHub credentials (PAT or GitHub App)"""
        auth_type = data.get("type")
        
        if auth_type == "pat":
            return {
                "type": "pat",
                "token": data["token"],
                "username": data.get("username", "terry-form-mcp")
            }
        elif auth_type == "github_app":
            return {
                "type": "github_app", 
                "app_id": data["app_id"],
                "private_key": data["private_key"],
                "installation_id": data.get("installation_id")
            }
        else:
            raise ValueError(f"Unsupported GitHub auth type: {auth_type}")
    
    def _parse_azure_credentials(self, data: Dict) -> Dict:
        """Parse Azure credentials (User token or Service Principal)"""
        auth_type = data.get("type")
        
        if auth_type == "user_token":
            return {
                "type": "user_token",
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "tenant_id": data.get("tenant_id")
            }
        elif auth_type == "service_principal":
            return {
                "type": "service_principal",
                "client_id": data["client_id"],
                "client_secret": data["client_secret"],
                "tenant_id": data["tenant_id"]
            }
        else:
            raise ValueError(f"Unsupported Azure auth type: {auth_type}")
    
    def get_github_client(self) -> Optional[Github]:
        """Get authenticated GitHub client"""
        if not self.github_auth:
            return None
            
        try:
            if self.github_auth["type"] == "pat":
                return Github(self.github_auth["token"])
            elif self.github_auth["type"] == "github_app":
                # Generate JWT for GitHub App
                token = self._generate_github_app_token()
                return Github(token)
        except Exception as e:
            logger.error(f"Failed to create GitHub client: {e}")
            return None
    
    def _generate_github_app_token(self) -> str:
        """Generate GitHub App installation token"""
        app_id = self.github_auth["app_id"]
        private_key = self.github_auth["private_key"]
        installation_id = self.github_auth.get("installation_id")
        
        # Create JWT
        now = datetime.utcnow()
        payload = {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iss": app_id
        }
        
        jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
        
        # Get installation token
        if installation_id:
            # Use GitHub API to get installation token
            import requests
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            response = requests.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers=headers
            )
            response.raise_for_status()
            return response.json()["token"]
        else:
            return jwt_token
    
    def get_azure_credential(self):
        """Get Azure credential object"""
        if not self.azure_auth:
            return DefaultAzureCredential()
            
        try:
            if self.azure_auth["type"] == "service_principal":
                return ClientSecretCredential(
                    tenant_id=self.azure_auth["tenant_id"],
                    client_id=self.azure_auth["client_id"],
                    client_secret=self.azure_auth["client_secret"]
                )
            elif self.azure_auth["type"] == "user_token":
                # For user tokens, we'll use DefaultAzureCredential
                # and set environment variables
                os.environ["AZURE_ACCESS_TOKEN"] = self.azure_auth["access_token"]
                if self.azure_auth.get("tenant_id"):
                    os.environ["AZURE_TENANT_ID"] = self.azure_auth["tenant_id"]
                return DefaultAzureCredential()
        except Exception as e:
            logger.error(f"Failed to create Azure credential: {e}")
            return DefaultAzureCredential()
    
    def configure_git_auth(self) -> bool:
        """Configure git with authentication credentials"""
        try:
            if self.github_auth:
                if self.github_auth["type"] == "pat":
                    # Configure git credential helper for GitHub
                    token = self.github_auth["token"]
                    username = self.github_auth.get("username", "terry-form-mcp")
                    
                    # Set git credential helper
                    subprocess.run([
                        "git", "config", "--global", "credential.helper", "store"
                    ], check=True)
                    
                    # Store GitHub credentials
                    git_credentials = f"https://{username}:{token}@github.com"
                    credentials_file = Path.home() / ".git-credentials"
                    credentials_file.write_text(git_credentials + "\n")
                    credentials_file.chmod(0o600)
                    
                    # Configure GitHub CLI
                    subprocess.run([
                        "gh", "auth", "login", "--with-token"
                    ], input=token, text=True, check=True)
                    
                    logger.info("Git and GitHub CLI configured with PAT")
                    return True
                    
                elif self.github_auth["type"] == "github_app":
                    # For GitHub App, we'll generate tokens as needed
                    logger.info("GitHub App authentication configured")
                    return True
            
            # Configure Azure CLI if credentials available
            if self.azure_auth:
                if self.azure_auth["type"] == "service_principal":
                    subprocess.run([
                        "az", "login", "--service-principal",
                        "--username", self.azure_auth["client_id"],
                        "--password", self.azure_auth["client_secret"],
                        "--tenant", self.azure_auth["tenant_id"]
                    ], check=True, capture_output=True)
                    logger.info("Azure CLI configured with service principal")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to configure git auth: {e}")
            return False
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status for all services"""
        return {
            "github": {
                "configured": self.github_auth is not None,
                "type": self.github_auth.get("type") if self.github_auth else None
            },
            "azure": {
                "configured": self.azure_auth is not None,
                "type": self.azure_auth.get("type") if self.azure_auth else None
            }
        }

# Global instance
auth_manager = AuthenticationManager()