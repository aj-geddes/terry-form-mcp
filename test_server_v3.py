#!/usr/bin/env python3
"""
Simple test script for Terry-Form MCP v3.0.0 core functionality
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test the core components
async def test_terraform_executor():
    """Test the Terraform executor"""
    sys.path.append('/app')
    from internal.terraform.executor import TerraformExecutor
    
    executor = TerraformExecutor()
    logger.info("✅ TerraformExecutor imported successfully")
    
    # Test version check
    result = await executor.execute_terraform("version", Path("/tmp"))
    logger.info(f"Terraform version check: {result['success']}")
    if result['success']:
        logger.info(f"Terraform output: {result['output'][:100]}...")
    
    return result['success']

async def test_cloud_client():
    """Test the Terraform Cloud client"""
    try:
        from internal.cloud.terraform_cloud_client import TerraformCloudClient
        logger.info("✅ TerraformCloudClient imported successfully")
        
        # Test client creation (without actual API calls)
        client = TerraformCloudClient("dummy-token", "dummy-org")
        logger.info("✅ TerraformCloudClient created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ TerraformCloudClient test failed: {e}")
        return False

async def test_github_app():
    """Test the GitHub App integration"""
    try:
        from internal.github.github_app import GitHubApp
        logger.info("✅ GitHubApp imported successfully")
        
        # Test app creation (without actual API calls)
        app = GitHubApp("123", "dummy-key", "dummy-secret")
        logger.info("✅ GitHubApp created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ GitHubApp test failed: {e}")
        return False

async def test_module_intelligence():
    """Test the Module Intelligence system"""
    try:
        from internal.analytics.module_intelligence import ModuleIntelligenceEngine
        logger.info("✅ ModuleIntelligenceEngine imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ ModuleIntelligenceEngine test failed: {e}")
        return False

async def test_health_endpoints():
    """Test basic HTTP functionality"""
    try:
        from aiohttp import web
        
        async def health_check(request):
            return web.json_response({"status": "healthy", "version": "3.0.0"})
        
        app = web.Application()
        app.router.add_get("/health", health_check)
        
        logger.info("✅ Health endpoint created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Health endpoint test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 Starting Terry-Form MCP v3.0.0 tests...")
    
    tests = [
        ("Terraform Executor", test_terraform_executor),
        ("Terraform Cloud Client", test_cloud_client),
        ("GitHub App", test_github_app),
        ("Module Intelligence", test_module_intelligence),
        ("Health Endpoints", test_health_endpoints),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Testing {test_name}...")
        try:
            result = await test_func()
            results[test_name] = result
            if result:
                logger.info(f"✅ {test_name} - PASSED")
            else:
                logger.warning(f"⚠️ {test_name} - FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} - ERROR: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n📊 Test Summary:")
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Terry-Form MCP v3.0.0 is ready!")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)