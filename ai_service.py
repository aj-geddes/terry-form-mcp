#!/usr/bin/env python3
"""
AI Service Manager for Terry-Form MCP
Provides intelligent Terraform assistance using Anthropic Claude or OpenAI GPT
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any, List

import httpx

logger = logging.getLogger(__name__)

class AIServiceManager:
    """Manages AI services for Terry-Form MCP"""
    
    def __init__(self):
        self.config = {}
        # Check both standard and vault paths
        self.secrets_paths = [Path("/var/run/secrets"), Path("/vault/secrets")]
        self._load_ai_config()
    
    def _load_ai_config(self):
        """Load AI configuration from Kubernetes secrets"""
        try:
            # Try each path until we find credentials
            for secrets_path in self.secrets_paths:
                ai_secret_path = secrets_path / "ai-service" / "credentials"
                if ai_secret_path.exists():
                    self.config = json.loads(ai_secret_path.read_text())
                    provider = self.config.get("provider", "anthropic").lower()
                    logger.info(f"AI service configured with {provider} from {secrets_path}")
                    return
                    
            logger.warning("No AI service credentials found in any path")
                
        except Exception as e:
            logger.error(f"Failed to load AI configuration: {e}")
            self.config = {}
    
    def is_configured(self) -> bool:
        """Check if AI service is properly configured"""
        return bool(self.config.get("api_key") and self.config.get("provider"))
    
    async def analyze_terraform_code(self, code: str, context: str = "") -> Dict[str, Any]:
        """Analyze Terraform code and provide insights"""
        if not self.is_configured():
            return {"error": "AI service not configured"}
        
        prompt = f"""
        Please analyze this Terraform code and provide:
        1. Code quality assessment
        2. Security recommendations
        3. Best practices suggestions
        4. Potential issues or improvements
        
        Context: {context}
        
        Terraform Code:
        ```hcl
        {code}
        ```
        
        Please respond in JSON format with the following structure:
        {{
            "quality_score": 1-10,
            "security_issues": ["list of security concerns"],
            "recommendations": ["list of improvement suggestions"],
            "best_practices": ["list of best practice recommendations"],
            "summary": "Overall assessment summary"
        }}
        """
        
        try:
            response = await self._make_ai_request(prompt)
            
            # Try to parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {"analysis": response}
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {"error": str(e)}
    
    async def generate_terraform_code(self, requirements: str, provider: str = "aws") -> Dict[str, Any]:
        """Generate Terraform code based on requirements"""
        if not self.is_configured():
            return {"error": "AI service not configured"}
        
        prompt = f"""
        Generate Terraform code for the following requirements:
        
        Requirements: {requirements}
        Cloud Provider: {provider}
        
        Please provide:
        1. Complete Terraform configuration
        2. Variables file content
        3. Outputs definition
        4. Brief explanation of the infrastructure
        
        Respond in JSON format:
        {{
            "main_tf": "main terraform configuration",
            "variables_tf": "variables definition", 
            "outputs_tf": "outputs definition",
            "explanation": "explanation of the infrastructure",
            "estimated_cost": "rough cost estimate if applicable"
        }}
        
        Follow Terraform best practices and ensure the code is production-ready.
        """
        
        try:
            response = await self._make_ai_request(prompt)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"generated_code": response}
                
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return {"error": str(e)}
    
    async def explain_terraform_resources(self, resources: List[str]) -> Dict[str, Any]:
        """Explain Terraform resources and their purposes"""
        if not self.is_configured():
            return {"error": "AI service not configured"}
        
        resources_text = "\n".join(resources)
        
        prompt = f"""
        Please explain the following Terraform resources:
        
        {resources_text}
        
        For each resource, provide:
        1. Purpose and functionality
        2. Key configuration options
        3. Common use cases
        4. Security considerations
        
        Respond in JSON format:
        {{
            "explanations": {{
                "resource_name": {{
                    "purpose": "description",
                    "key_options": ["list of important options"],
                    "use_cases": ["common use cases"],
                    "security_notes": ["security considerations"]
                }}
            }}
        }}
        """
        
        try:
            response = await self._make_ai_request(prompt)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"explanation": response}
                
        except Exception as e:
            logger.error(f"Resource explanation failed: {e}")
            return {"error": str(e)}
    
    async def suggest_improvements(self, code: str, goals: str = "") -> Dict[str, Any]:
        """Suggest improvements to existing Terraform code"""
        if not self.is_configured():
            return {"error": "AI service not configured"}
        
        prompt = f"""
        Please suggest improvements to this Terraform code.
        
        Goals: {goals or "General optimization and best practices"}
        
        Current Code:
        ```hcl
        {code}
        ```
        
        Provide specific suggestions for:
        1. Performance optimization
        2. Cost optimization  
        3. Security improvements
        4. Maintainability enhancements
        5. Modern Terraform features to adopt
        
        Respond in JSON format:
        {{
            "improvements": [
                {{
                    "category": "performance|cost|security|maintainability|modernization",
                    "suggestion": "specific improvement",
                    "reason": "why this improvement helps",
                    "implementation": "how to implement this change"
                }}
            ],
            "priority": "high|medium|low overall priority",
            "summary": "summary of key improvements"
        }}
        """
        
        try:
            response = await self._make_ai_request(prompt)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"suggestions": response}
                
        except Exception as e:
            logger.error(f"Improvement suggestions failed: {e}")
            return {"error": str(e)}
    
    async def _make_ai_request(self, prompt: str) -> str:
        """Make a request to the configured AI service"""
        if not self.is_configured():
            raise ValueError("AI service not configured")
        
        provider = self.config.get("provider", "anthropic").lower()
        api_key = self.config["api_key"]
        model = self.config.get("model", "claude-3-5-sonnet-20241022" if provider == "anthropic" else "gpt-4")
        max_tokens = self.config.get("max_tokens", 4000)
        temperature = self.config.get("temperature", 0.1)
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if provider == "anthropic":
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    }
                    
                    payload = {
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                    
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result["content"][0]["text"]
                    
                elif provider == "openai":
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    
                    payload = {
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are Terry, an expert Terraform infrastructure assistant. Provide helpful, accurate, and actionable advice."
                            },
                            {"role": "user", "content": prompt}
                        ]
                    }
                    
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
                    
        except Exception as e:
            logger.error(f"AI request failed: {e}")
            raise
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI service status information"""
        if not self.config:
            return {
                "configured": False,
                "provider": None,
                "model": None,
                "status": "No AI configuration found"
            }
        
        provider = self.config.get("provider", "anthropic")
        default_model = "claude-3-5-sonnet-20241022" if provider == "anthropic" else "gpt-4"
        
        return {
            "configured": self.is_configured(),
            "provider": provider,
            "model": self.config.get("model", default_model),
            "max_tokens": self.config.get("max_tokens", 4000),
            "temperature": self.config.get("temperature", 0.1),
            "status": "Ready" if self.is_configured() else "Missing API key or provider"
        }

# Global instance
ai_service = AIServiceManager()