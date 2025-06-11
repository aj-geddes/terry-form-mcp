#!/bin/bash

# ============================================================================
# TERRY-FORM-MCP - Terraform MCP Server with LSP Integration
# ============================================================================
#
# This build script creates a Docker image for the Terry-Form MCP server
# with integrated Terraform Language Server Protocol (LSP) capabilities.
#
# Features:
# - Builds on official HashiCorp Terraform image
# - Includes terraform-ls v0.33.2 for language server functionality
# - Comprehensive diagnostic and utility tools
# - Enhanced LSP client with robust error handling
#
# ============================================================================

set -e

# Configuration
IMAGE_NAME="terry-form-mcp"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Building Terry-Form MCP Server with LSP Integration${NC}"
echo "========================================================="

# Step 1: Check Docker connectivity
echo -e "${YELLOW}Checking Docker connectivity...${NC}"
if ! docker info &>/dev/null; then
    echo -e "${RED}⚠️  Docker daemon is not running or not accessible!${NC}"
    echo "Please make sure Docker is installed and running."
    exit 1
fi

# Step 2: Build the Docker image
echo -e "${YELLOW}Building Docker image: ${FULL_IMAGE_NAME}${NC}"
docker build -f Dockerfile.consolidated -t ${FULL_IMAGE_NAME} .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker build successful!${NC}"

# Step 3: Verify the image
echo -e "\n${YELLOW}Verifying the built image...${NC}"

# Test 1: Check terraform-ls availability
echo "Test 1: Checking terraform-ls availability..."
TERRAFORM_LS_VERSION=$(docker run --rm ${FULL_IMAGE_NAME} terraform-ls version 2>/dev/null | head -1)
if [[ -n "$TERRAFORM_LS_VERSION" && "$TERRAFORM_LS_VERSION" == *"0.33.2"* ]]; then
    echo -e "${GREEN}✅ terraform-ls v0.33.2 is available${NC}"
else
    echo -e "${RED}❌ terraform-ls verification failed${NC}"
    echo "  Output: $TERRAFORM_LS_VERSION"
fi

# Test 2: Check Terraform availability
echo "Test 2: Checking Terraform availability..."
TERRAFORM_VERSION=$(docker run --rm ${FULL_IMAGE_NAME} terraform version 2>/dev/null | head -1)
if [[ -n "$TERRAFORM_VERSION" && "$TERRAFORM_VERSION" == *"Terraform"* ]]; then
    echo -e "${GREEN}✅ Terraform is available${NC}"
    echo "  Version: $TERRAFORM_VERSION"
else
    echo -e "${RED}❌ Terraform verification failed${NC}"
fi

# Test 3: Check Python and server availability
echo "Test 3: Checking Python and server availability..."
if docker run --rm ${FULL_IMAGE_NAME} ls /app/server_enhanced_with_lsp.py &>/dev/null; then
    echo -e "${GREEN}✅ Server files are available${NC}"
else
    echo -e "${RED}❌ Server files verification failed${NC}"
fi

echo -e "\n${GREEN}🎉 Build and Verification Complete!${NC}"
echo -e "${BLUE}📦 Image: ${FULL_IMAGE_NAME}${NC}"

# Usage instructions
echo -e "\n${BLUE}📚 Usage Instructions${NC}"
echo "======================"
echo -e "${YELLOW}Run as MCP Server:${NC}"
echo "docker run -it --rm -p 8000:8000 -v \"\$(pwd):/mnt/workspace\" ${FULL_IMAGE_NAME}"
echo ""
echo -e "${YELLOW}Test with direct command:${NC}"
echo "docker run -i --rm -v \"\$(pwd):/mnt/workspace\" ${FULL_IMAGE_NAME} python3 terry-form-mcp.py < test.json"
echo ""
echo -e "${YELLOW}Environment check:${NC}"
echo "docker run -i --rm ${FULL_IMAGE_NAME} python3 -c \"import json; import sys; sys.path.append('/app'); from server_enhanced_with_lsp import terry_environment_check; print(json.dumps(terry_environment_check(), indent=2))\""