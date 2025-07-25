#!/usr/bin/env python3
"""
GitHub App Authentication Module
Handles OAuth app authentication and token management for GitHub integration.

Security hardened:
- Secure token storage and handling
- JWT token generation with expiration
- Installation token caching with TTL
"""

import os
import time
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
import jwt
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class GitHubAppConfig:
    """Configuration for GitHub App authentication"""
    app_id: str
    private_key: str
    installation_id: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'GitHubAppConfig':
        """Create config from environment variables"""
        app_id = os.environ.get('GITHUB_APP_ID')
        if not app_id:
            raise ValueError("GITHUB_APP_ID environment variable not set")
        
        # Try to load private key from file or environment
        private_key = None
        private_key_path = os.environ.get('GITHUB_APP_PRIVATE_KEY_PATH')
        
        if private_key_path:
            key_path = Path(private_key_path)
            if key_path.exists():
                private_key = key_path.read_text()
            else:
                raise ValueError(f"Private key file not found: {private_key_path}")
        else:
            private_key = os.environ.get('GITHUB_APP_PRIVATE_KEY')
            if not private_key:
                raise ValueError("Neither GITHUB_APP_PRIVATE_KEY nor GITHUB_APP_PRIVATE_KEY_PATH is set")
        
        # Replace literal \n with actual newlines in private key
        private_key = private_key.replace('\\n', '\n')
        
        return cls(
            app_id=app_id,
            private_key=private_key,
            installation_id=os.environ.get('GITHUB_APP_INSTALLATION_ID'),
            webhook_secret=os.environ.get('GITHUB_APP_WEBHOOK_SECRET')
        )


class GitHubAppAuth:
    """Handles GitHub App authentication and token management"""
    
    def __init__(self, config: GitHubAppConfig):
        self.config = config
        self._installation_tokens: Dict[str, Dict[str, Any]] = {}
        self.base_url = "https://api.github.com"
        
    def _generate_jwt(self) -> str:
        """Generate a JWT token for GitHub App authentication"""
        # GitHub Apps use RS256 algorithm
        now = int(time.time())
        
        payload = {
            'iat': now - 60,  # Issued at time (60 seconds in the past to allow for clock drift)
            'exp': now + (10 * 60),  # JWT expiration time (10 minutes from now)
            'iss': self.config.app_id  # GitHub App ID
        }
        
        return jwt.encode(
            payload,
            self.config.private_key,
            algorithm='RS256'
        )
    
    def _get_headers(self, use_jwt: bool = True) -> Dict[str, str]:
        """Get headers for GitHub API requests"""
        headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        if use_jwt:
            headers['Authorization'] = f'Bearer {self._generate_jwt()}'
        
        return headers
    
    def get_installation_token(self, installation_id: Optional[str] = None) -> str:
        """Get an installation access token"""
        install_id = installation_id or self.config.installation_id
        if not install_id:
            raise ValueError("No installation ID provided")
        
        # Check if we have a cached token that's still valid
        if install_id in self._installation_tokens:
            token_data = self._installation_tokens[install_id]
            expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
            
            # If token expires in more than 5 minutes, reuse it
            if expires_at > datetime.now(expires_at.tzinfo) + timedelta(minutes=5):
                logger.debug(f"Using cached installation token for {install_id}")
                return token_data['token']
        
        # Generate new installation token
        logger.info(f"Generating new installation token for {install_id}")
        
        url = f"{self.base_url}/app/installations/{install_id}/access_tokens"
        response = requests.post(
            url,
            headers=self._get_headers(use_jwt=True),
            timeout=30
        )
        
        if response.status_code != 201:
            raise RuntimeError(
                f"Failed to get installation token: {response.status_code} - {response.text}"
            )
        
        token_data = response.json()
        
        # Cache the token
        self._installation_tokens[install_id] = token_data
        
        return token_data['token']
    
    def get_authenticated_headers(self, installation_id: Optional[str] = None) -> Dict[str, str]:
        """Get headers with installation access token"""
        token = self.get_installation_token(installation_id)
        
        return {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
    
    def list_installations(self) -> list[Dict[str, Any]]:
        """List all installations of this GitHub App"""
        url = f"{self.base_url}/app/installations"
        
        response = requests.get(
            url,
            headers=self._get_headers(use_jwt=True),
            timeout=30
        )
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to list installations: {response.status_code} - {response.text}"
            )
        
        return response.json()
    
    def get_installation_repos(self, installation_id: Optional[str] = None) -> list[Dict[str, Any]]:
        """Get repositories accessible to an installation"""
        headers = self.get_authenticated_headers(installation_id)
        
        url = f"{self.base_url}/installation/repositories"
        all_repos = []
        
        while url:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                raise RuntimeError(
                    f"Failed to get installation repos: {response.status_code} - {response.text}"
                )
            
            data = response.json()
            all_repos.extend(data.get('repositories', []))
            
            # Check for pagination
            links = response.links
            url = links.get('next', {}).get('url')
        
        return all_repos
    
    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify a GitHub webhook signature"""
        if not self.config.webhook_secret:
            logger.warning("No webhook secret configured, skipping verification")
            return True
        
        import hmac
        import hashlib
        
        expected_signature = 'sha256=' + hmac.new(
            self.config.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)