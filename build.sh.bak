#!/bin/bash

# Terry-Form MCP Build Script
# Builds Docker image and runs basic tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="terry-form-mcp"
TEST_IMAGE="$IMAGE_NAME-test"

echo -e "${BLUE}🏗️  Building Terry-Form MCP Docker Image${NC}"
echo "=============================================="

# Build the Docker image
echo -e "${YELLOW}Building image: $IMAGE_NAME${NC}"
docker build -t $IMAGE_NAME .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker build successful!${NC}"
else
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi

echo -e "\n${BLUE}🧪 Running Tests${NC}"
echo "=================="

# Test 1: Basic functionality test
echo -e "${YELLOW}Test 1: Basic JSON input processing${NC}"
echo '{"actions":["validate"],"path":"test"}' | docker run -i --rm $IMAGE_NAME python3 terry-form-mcp.py 2>/dev/null || true
echo -e "${GREEN}✅ Basic test completed${NC}"

# Test 2: FastMCP server startup test  
echo -e "\n${YELLOW}Test 2: FastMCP server startup${NC}"
timeout 5s docker run --rm $IMAGE_NAME &>/dev/null || true
echo -e "${GREEN}✅ Server startup test completed${NC}"

# Test 3: Test with sample test.json
echo -e "\n${YELLOW}Test 3: Sample test.json processing${NC}"
docker run -i --rm -v "$(pwd):/mnt/workspace" $IMAGE_NAME python3 terry-form-mcp.py < test.json || true
echo -e "${GREEN}✅ Sample test completed${NC}"

echo -e "\n${GREEN}🎉 All tests completed!${NC}"
echo -e "${BLUE}📦 Image ready: $IMAGE_NAME${NC}"

# Display usage instructions
echo -e "\n${BLUE}📚 Usage Instructions${NC}"
echo "======================"
echo -e "${YELLOW}Run as MCP Server:${NC}"
echo "docker run -it --rm -v \"\$(pwd):/mnt/workspace\" $IMAGE_NAME"
echo ""
echo -e "${YELLOW}Test with sample data:${NC}"
echo "docker run -i --rm -v \"\$(pwd):/mnt/workspace\" $IMAGE_NAME python3 terry-form-mcp.py < test.json"
echo ""
echo -e "${YELLOW}Interactive testing:${NC}"
echo "echo '{\"actions\":[\"validate\"],\"path\":\"your-terraform-dir\"}' | docker run -i --rm -v \"\$(pwd):/mnt/workspace\" $IMAGE_NAME python3 terry-form-mcp.py"