"""
Module Intelligence System for Terry-Form MCP v3.0.0
Enhanced provider documentation integration and dependency impact analysis
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
from packaging import version

from ..lsp.terraform_lsp_client import TerraformLSPClient

logger = logging.getLogger(__name__)


@dataclass
class ProviderVersion:
    """Represents a provider version with metadata"""
    name: str
    version: str
    published_at: datetime
    breaking_changes: List[str]
    deprecated_features: List[str]
    new_features: List[str]
    api_changes: List[str]


@dataclass
class ModuleDependency:
    """Represents a module dependency"""
    source: str
    version_constraint: Optional[str]
    required_providers: Dict[str, str]
    path: str
    line_number: int


@dataclass
class ImpactAnalysis:
    """Results of dependency impact analysis"""
    affected_modules: List[str]
    breaking_changes: List[Dict[str, Any]]
    compatibility_issues: List[Dict[str, Any]]
    recommended_actions: List[str]
    migration_complexity: str  # low, medium, high
    estimated_effort_hours: int


class ProviderSchemaManager:
    """Manages provider schemas and documentation"""
    
    def __init__(self, cache_dir: Path, lsp_client: TerraformLSPClient):
        self.cache_dir = cache_dir
        self.lsp_client = lsp_client
        self.schemas_cache = {}
        self.documentation_cache = {}
        
    async def get_provider_schema(self, provider: str, version: str) -> Dict[str, Any]:
        """Get provider schema for a specific version"""
        cache_key = f"{provider}:{version}"
        
        if cache_key in self.schemas_cache:
            schema, timestamp = self.schemas_cache[cache_key]
            # Cache for 24 hours
            if datetime.now() - timestamp < timedelta(hours=24):
                return schema
        
        # Try to get schema from terraform-ls
        try:
            schema = await self.lsp_client.get_provider_schema(provider, version)
            self.schemas_cache[cache_key] = (schema, datetime.now())
            return schema
        except Exception as e:
            logger.warning(f"Failed to get schema for {provider}:{version}: {e}")
            return {}
    
    async def get_provider_documentation(self, provider: str, version: str) -> Dict[str, Any]:
        """Get provider documentation"""
        cache_key = f"{provider}:{version}:docs"
        
        if cache_key in self.documentation_cache:
            docs, timestamp = self.documentation_cache[cache_key]
            if datetime.now() - timestamp < timedelta(hours=24):
                return docs
        
        # Fetch from Terraform Registry
        docs = await self._fetch_provider_docs(provider, version)
        self.documentation_cache[cache_key] = (docs, datetime.now())
        return docs
    
    async def _fetch_provider_docs(self, provider: str, version: str) -> Dict[str, Any]:
        """Fetch provider documentation from Terraform Registry"""
        namespace, name = provider.split("/", 1) if "/" in provider else ("hashicorp", provider)
        
        async with aiohttp.ClientSession() as session:
            # Get provider version info
            url = f"https://registry.terraform.io/v1/providers/{namespace}/{name}/{version}"
            
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "provider": provider,
                            "version": version,
                            "published_at": data.get("published_at"),
                            "docs_url": data.get("docs_url", ""),
                            "source_url": data.get("source_url", ""),
                            "description": data.get("description", "")
                        }
            except Exception as e:
                logger.warning(f"Failed to fetch docs for {provider}:{version}: {e}")
        
        return {}
    
    async def compare_provider_versions(
        self,
        provider: str,
        old_version: str,
        new_version: str
    ) -> Dict[str, Any]:
        """Compare two provider versions to identify changes"""
        old_schema = await self.get_provider_schema(provider, old_version)
        new_schema = await self.get_provider_schema(provider, new_version)
        
        changes = {
            "breaking_changes": [],
            "new_features": [],
            "deprecated_features": [],
            "api_changes": []
        }
        
        if not old_schema or not new_schema:
            return changes
        
        # Compare resource schemas
        old_resources = old_schema.get("resource_schemas", {})
        new_resources = new_schema.get("resource_schemas", {})
        
        # Removed resources (breaking)
        removed_resources = set(old_resources.keys()) - set(new_resources.keys())
        for resource in removed_resources:
            changes["breaking_changes"].append({
                "type": "resource_removed",
                "resource": resource,
                "description": f"Resource {resource} has been removed"
            })
        
        # New resources
        new_resources_added = set(new_resources.keys()) - set(old_resources.keys())
        for resource in new_resources_added:
            changes["new_features"].append({
                "type": "resource_added",
                "resource": resource,
                "description": f"New resource {resource} is available"
            })
        
        # Compare attributes for existing resources
        common_resources = set(old_resources.keys()) & set(new_resources.keys())
        for resource in common_resources:
            resource_changes = self._compare_resource_attributes(
                old_resources[resource],
                new_resources[resource],
                resource
            )
            
            for change_type, change_list in resource_changes.items():
                changes[change_type].extend(change_list)
        
        # Compare data sources similarly
        old_datasources = old_schema.get("data_source_schemas", {})
        new_datasources = new_schema.get("data_source_schemas", {})
        
        # Process data sources the same way as resources
        removed_datasources = set(old_datasources.keys()) - set(new_datasources.keys())
        for datasource in removed_datasources:
            changes["breaking_changes"].append({
                "type": "datasource_removed",
                "datasource": datasource,
                "description": f"Data source {datasource} has been removed"
            })
        
        return changes
    
    def _compare_resource_attributes(
        self,
        old_resource: Dict[str, Any],
        new_resource: Dict[str, Any],
        resource_name: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Compare attributes between resource versions"""
        changes = {
            "breaking_changes": [],
            "new_features": [],
            "deprecated_features": [],
            "api_changes": []
        }
        
        old_attrs = old_resource.get("block", {}).get("attributes", {})
        new_attrs = new_resource.get("block", {}).get("attributes", {})
        
        # Removed attributes (potentially breaking)
        removed_attrs = set(old_attrs.keys()) - set(new_attrs.keys())
        for attr in removed_attrs:
            old_attr = old_attrs[attr]
            if old_attr.get("required", False):
                changes["breaking_changes"].append({
                    "type": "required_attribute_removed",
                    "resource": resource_name,
                    "attribute": attr,
                    "description": f"Required attribute {attr} removed from {resource_name}"
                })
            else:
                changes["api_changes"].append({
                    "type": "optional_attribute_removed",
                    "resource": resource_name,
                    "attribute": attr,
                    "description": f"Optional attribute {attr} removed from {resource_name}"
                })
        
        # New attributes
        new_attrs_added = set(new_attrs.keys()) - set(old_attrs.keys())
        for attr in new_attrs_added:
            new_attr = new_attrs[attr]
            if new_attr.get("required", False):
                changes["breaking_changes"].append({
                    "type": "required_attribute_added",
                    "resource": resource_name,
                    "attribute": attr,
                    "description": f"New required attribute {attr} added to {resource_name}"
                })
            else:
                changes["new_features"].append({
                    "type": "optional_attribute_added",
                    "resource": resource_name,
                    "attribute": attr,
                    "description": f"New optional attribute {attr} added to {resource_name}"
                })
        
        # Changed attributes
        common_attrs = set(old_attrs.keys()) & set(new_attrs.keys())
        for attr in common_attrs:
            old_attr = old_attrs[attr]
            new_attr = new_attrs[attr]
            
            # Check if required status changed
            if old_attr.get("required", False) != new_attr.get("required", False):
                if new_attr.get("required", False):
                    changes["breaking_changes"].append({
                        "type": "attribute_now_required",
                        "resource": resource_name,
                        "attribute": attr,
                        "description": f"Attribute {attr} is now required in {resource_name}"
                    })
                else:
                    changes["api_changes"].append({
                        "type": "attribute_now_optional",
                        "resource": resource_name,
                        "attribute": attr,
                        "description": f"Attribute {attr} is now optional in {resource_name}"
                    })
            
            # Check type changes
            old_type = old_attr.get("type")
            new_type = new_attr.get("type")
            if old_type != new_type:
                changes["breaking_changes"].append({
                    "type": "attribute_type_changed",
                    "resource": resource_name,
                    "attribute": attr,
                    "old_type": old_type,
                    "new_type": new_type,
                    "description": f"Attribute {attr} type changed from {old_type} to {new_type} in {resource_name}"
                })
        
        return changes


class ModuleDependencyAnalyzer:
    """Analyzes module dependencies and their impact"""
    
    def __init__(self, lsp_client: TerraformLSPClient, schema_manager: ProviderSchemaManager):
        self.lsp_client = lsp_client
        self.schema_manager = schema_manager
        
    async def analyze_module_dependencies(self, module_path: Path) -> List[ModuleDependency]:
        """Analyze dependencies in a Terraform module"""
        dependencies = []
        
        # Get all .tf files in the module
        tf_files = list(module_path.glob("*.tf"))
        
        for tf_file in tf_files:
            file_deps = await self._analyze_file_dependencies(tf_file)
            dependencies.extend(file_deps)
        
        return dependencies
    
    async def _analyze_file_dependencies(self, file_path: Path) -> List[ModuleDependency]:
        """Analyze dependencies in a single Terraform file"""
        dependencies = []
        
        try:
            content = file_path.read_text()
            
            # Use LSP to get symbols and references
            symbols = await self.lsp_client.get_document_symbols(str(file_path))
            
            # Parse module blocks
            module_blocks = self._extract_module_blocks(content)
            
            for module_block in module_blocks:
                dep = ModuleDependency(
                    source=module_block.get("source", ""),
                    version_constraint=module_block.get("version"),
                    required_providers={},
                    path=str(file_path),
                    line_number=module_block.get("line", 0)
                )
                dependencies.append(dep)
            
            # Parse required_providers blocks
            required_providers = self._extract_required_providers(content)
            
            # Add provider dependencies
            for provider_name, constraint in required_providers.items():
                dep = ModuleDependency(
                    source=provider_name,
                    version_constraint=constraint,
                    required_providers={provider_name: constraint},
                    path=str(file_path),
                    line_number=0  # TODO: get actual line number
                )
                dependencies.append(dep)
                
        except Exception as e:
            logger.warning(f"Failed to analyze dependencies in {file_path}: {e}")
        
        return dependencies
    
    def _extract_module_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract module blocks from Terraform content"""
        modules = []
        
        # Simple regex to find module blocks
        module_pattern = r'module\s+"([^"]+)"\s*\{([^}]*)\}'
        
        for match in re.finditer(module_pattern, content, re.DOTALL):
            module_name = match.group(1)
            module_body = match.group(2)
            
            # Extract source and version
            source_match = re.search(r'source\s*=\s*"([^"]+)"', module_body)
            version_match = re.search(r'version\s*=\s*"([^"]+)"', module_body)
            
            modules.append({
                "name": module_name,
                "source": source_match.group(1) if source_match else "",
                "version": version_match.group(1) if version_match else None,
                "line": content[:match.start()].count('\n') + 1
            })
        
        return modules
    
    def _extract_required_providers(self, content: str) -> Dict[str, str]:
        """Extract required_providers from Terraform content"""
        providers = {}
        
        # Find terraform blocks with required_providers
        terraform_pattern = r'terraform\s*\{([^}]*)\}'
        
        for match in re.finditer(terraform_pattern, content, re.DOTALL):
            terraform_body = match.group(1)
            
            # Find required_providers block
            providers_pattern = r'required_providers\s*\{([^}]*)\}'
            providers_match = re.search(providers_pattern, terraform_body, re.DOTALL)
            
            if providers_match:
                providers_body = providers_match.group(1)
                
                # Extract individual provider declarations
                provider_pattern = r'(\w+)\s*=\s*\{[^}]*version\s*=\s*"([^"]+)"[^}]*\}'
                
                for prov_match in re.finditer(provider_pattern, providers_body):
                    provider_name = prov_match.group(1)
                    version_constraint = prov_match.group(2)
                    providers[provider_name] = version_constraint
        
        return providers
    
    async def perform_impact_analysis(
        self,
        dependencies: List[ModuleDependency],
        provider_updates: Dict[str, Tuple[str, str]]  # provider -> (old_version, new_version)
    ) -> ImpactAnalysis:
        """Perform comprehensive impact analysis for provider updates"""
        
        affected_modules = []
        breaking_changes = []
        compatibility_issues = []
        recommended_actions = []
        
        complexity_score = 0
        effort_hours = 0
        
        for dependency in dependencies:
            # Check if this dependency is affected by provider updates
            for provider, (old_ver, new_ver) in provider_updates.items():
                if provider in dependency.required_providers:
                    affected_modules.append(dependency.path)
                    
                    # Analyze version compatibility
                    required_version = dependency.required_providers[provider]
                    compatibility = self._check_version_compatibility(
                        required_version, new_ver
                    )
                    
                    if not compatibility["compatible"]:
                        compatibility_issues.append({
                            "module": dependency.path,
                            "provider": provider,
                            "required_version": required_version,
                            "new_version": new_ver,
                            "issue": compatibility["reason"]
                        })
                        complexity_score += 3
                        effort_hours += 4
                    
                    # Get provider schema changes
                    changes = await self.schema_manager.compare_provider_versions(
                        provider, old_ver, new_ver
                    )
                    
                    # Analyze breaking changes impact
                    for change in changes["breaking_changes"]:
                        # Check if this module uses the affected resource/attribute
                        if await self._module_uses_feature(dependency.path, change):
                            breaking_changes.append({
                                "module": dependency.path,
                                "provider": provider,
                                "change": change,
                                "severity": "high"
                            })
                            complexity_score += 5
                            effort_hours += 8
                    
                    # Check deprecated features
                    for change in changes["deprecated_features"]:
                        if await self._module_uses_feature(dependency.path, change):
                            recommended_actions.append(
                                f"Update {dependency.path} to replace deprecated "
                                f"{change.get('type', 'feature')} in {provider}"
                            )
                            complexity_score += 2
                            effort_hours += 2
        
        # Determine migration complexity
        if complexity_score == 0:
            migration_complexity = "low"
        elif complexity_score < 10:
            migration_complexity = "medium"
        else:
            migration_complexity = "high"
        
        # Add general recommendations
        if breaking_changes:
            recommended_actions.append("Test all modules in a development environment before applying to production")
            recommended_actions.append("Create backup of current state before upgrading")
        
        if compatibility_issues:
            recommended_actions.append("Update version constraints in affected modules")
        
        return ImpactAnalysis(
            affected_modules=list(set(affected_modules)),
            breaking_changes=breaking_changes,
            compatibility_issues=compatibility_issues,
            recommended_actions=recommended_actions,
            migration_complexity=migration_complexity,
            estimated_effort_hours=effort_hours
        )
    
    def _check_version_compatibility(
        self,
        required_constraint: str,
        new_version: str
    ) -> Dict[str, Any]:
        """Check if a new version satisfies version constraints"""
        try:
            # Parse version constraint
            # This is a simplified implementation
            # In practice, you'd use a proper constraint parser
            
            if required_constraint.startswith(">="):
                min_version = required_constraint[2:].strip()
                if version.parse(new_version) >= version.parse(min_version):
                    return {"compatible": True}
                else:
                    return {
                        "compatible": False,
                        "reason": f"New version {new_version} is less than required minimum {min_version}"
                    }
            
            elif required_constraint.startswith("~>"):
                # Pessimistic constraint
                base_version = required_constraint[2:].strip()
                base_parsed = version.parse(base_version)
                new_parsed = version.parse(new_version)
                
                # Allow patch updates but not minor/major
                if (new_parsed.major == base_parsed.major and 
                    new_parsed.minor == base_parsed.minor and
                    new_parsed.micro >= base_parsed.micro):
                    return {"compatible": True}
                else:
                    return {
                        "compatible": False,
                        "reason": f"New version {new_version} is outside pessimistic constraint {required_constraint}"
                    }
            
            elif "=" in required_constraint:
                exact_version = required_constraint.replace("=", "").strip()
                if new_version == exact_version:
                    return {"compatible": True}
                else:
                    return {
                        "compatible": False,
                        "reason": f"New version {new_version} does not match exact constraint {exact_version}"
                    }
            
            else:
                # Assume any version is acceptable if no constraint
                return {"compatible": True}
                
        except Exception as e:
            logger.warning(f"Failed to parse version constraint {required_constraint}: {e}")
            return {
                "compatible": False,
                "reason": f"Invalid version constraint: {required_constraint}"
            }
    
    async def _module_uses_feature(self, module_path: str, change: Dict[str, Any]) -> bool:
        """Check if a module uses a specific feature that's changing"""
        try:
            # Read module content
            content = Path(module_path).read_text()
            
            change_type = change.get("type", "")
            
            if "resource" in change_type:
                resource_name = change.get("resource", "")
                # Simple check for resource usage
                return f'resource "{resource_name}"' in content or f'data "{resource_name}"' in content
            
            elif "attribute" in change_type:
                resource_name = change.get("resource", "")
                attribute_name = change.get("attribute", "")
                # Check for attribute usage in the resource
                resource_pattern = rf'resource "{resource_name}"[^{{]*\{{[^}}]*{attribute_name}[^}}]*\}}'
                return bool(re.search(resource_pattern, content, re.DOTALL))
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to check feature usage in {module_path}: {e}")
            return False


class ModuleIntelligenceEngine:
    """Main engine for module intelligence operations"""
    
    def __init__(self, cache_dir: Path, lsp_client: TerraformLSPClient):
        self.cache_dir = cache_dir
        self.lsp_client = lsp_client
        self.schema_manager = ProviderSchemaManager(cache_dir, lsp_client)
        self.dependency_analyzer = ModuleDependencyAnalyzer(lsp_client, self.schema_manager)
        
    async def analyze_provider_update_impact(
        self,
        modules_paths: List[Path],
        provider_updates: Dict[str, Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Analyze the impact of provider updates across multiple modules"""
        
        all_dependencies = []
        
        # Analyze dependencies in all modules
        for module_path in modules_paths:
            deps = await self.dependency_analyzer.analyze_module_dependencies(module_path)
            all_dependencies.extend(deps)
        
        # Perform impact analysis
        impact = await self.dependency_analyzer.perform_impact_analysis(
            all_dependencies, provider_updates
        )
        
        # Generate detailed report
        report = {
            "summary": {
                "total_modules_analyzed": len(modules_paths),
                "affected_modules": len(impact.affected_modules),
                "breaking_changes": len(impact.breaking_changes),
                "compatibility_issues": len(impact.compatibility_issues),
                "migration_complexity": impact.migration_complexity,
                "estimated_effort_hours": impact.estimated_effort_hours
            },
            "affected_modules": impact.affected_modules,
            "breaking_changes": impact.breaking_changes,
            "compatibility_issues": impact.compatibility_issues,
            "recommended_actions": impact.recommended_actions,
            "provider_changes": {}
        }
        
        # Add detailed provider change information
        for provider, (old_ver, new_ver) in provider_updates.items():
            changes = await self.schema_manager.compare_provider_versions(
                provider, old_ver, new_ver
            )
            report["provider_changes"][provider] = {
                "old_version": old_ver,
                "new_version": new_ver,
                "changes": changes
            }
        
        return report
    
    async def get_provider_upgrade_recommendations(
        self,
        current_providers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Get recommendations for provider upgrades"""
        recommendations = {}
        
        for provider, current_version in current_providers.items():
            # This would normally query the Terraform Registry for latest versions
            # For now, we'll provide a structure for the recommendations
            recommendations[provider] = {
                "current_version": current_version,
                "latest_version": "unknown",  # Would be fetched from registry
                "recommended_version": "unknown",
                "upgrade_priority": "low",  # low, medium, high
                "reasons": [],
                "risks": [],
                "estimated_effort": "low"
            }
        
        return recommendations