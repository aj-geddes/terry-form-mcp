#!/bin/bash

# ============================================================================
# Terry-Form MCP - Verification Script
# ============================================================================
# Verifies that the Docker image is built correctly and all components work
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

IMAGE_NAME="terry-form-mcp:latest"
PASS_COUNT=0
FAIL_COUNT=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Terry-Form MCP - Verification Script              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print test result
test_result() {
    local test_name="$1"
    local result="$2"
    local details="$3"

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC} - $test_name"
        [ -n "$details" ] && echo -e "   ${BLUE}→${NC} $details"
        ((PASS_COUNT++))
    else
        echo -e "${RED}❌ FAIL${NC} - $test_name"
        [ -n "$details" ] && echo -e "   ${RED}→${NC} $details"
        ((FAIL_COUNT++))
    fi
}

# Test 1: Check if Docker is running
echo -e "${YELLOW}[1/8]${NC} Checking Docker..."
if docker info &>/dev/null; then
    test_result "Docker connectivity" "PASS" "Docker daemon is running"
else
    test_result "Docker connectivity" "FAIL" "Docker daemon is not accessible"
    exit 1
fi

# Test 2: Check if image exists
echo -e "${YELLOW}[2/8]${NC} Checking Docker image..."
if docker images | grep -q "terry-form-mcp"; then
    IMAGE_SIZE=$(docker images terry-form-mcp:latest --format "{{.Size}}")
    test_result "Docker image exists" "PASS" "Image size: $IMAGE_SIZE"
else
    test_result "Docker image exists" "FAIL" "Run ./build.sh first"
    exit 1
fi

# Test 3: Check Terraform availability
echo -e "${YELLOW}[3/8]${NC} Checking Terraform..."
TF_VERSION=$(docker run --rm $IMAGE_NAME sh -c "terraform version 2>&1 | head -1" 2>/dev/null || echo "")
if echo "$TF_VERSION" | grep -q "Terraform"; then
    test_result "Terraform CLI" "PASS" "$TF_VERSION"
else
    test_result "Terraform CLI" "FAIL" "Terraform not found"
fi

# Test 4: Check terraform-ls availability
echo -e "${YELLOW}[4/8]${NC} Checking terraform-ls..."
TF_LS_VERSION=$(docker run --rm $IMAGE_NAME sh -c "terraform-ls version 2>&1 | head -1" 2>/dev/null || echo "")
if echo "$TF_LS_VERSION" | grep -q "0.33.2"; then
    test_result "Terraform Language Server" "PASS" "$TF_LS_VERSION"
else
    test_result "Terraform Language Server" "FAIL" "Expected v0.33.2"
fi

# Test 5: Check Python and FastMCP
echo -e "${YELLOW}[5/8]${NC} Checking Python and FastMCP..."
PYTHON_VERSION=$(docker run --rm $IMAGE_NAME python3 --version 2>&1)
if echo "$PYTHON_VERSION" | grep -q "Python 3"; then
    test_result "Python runtime" "PASS" "$PYTHON_VERSION"
else
    test_result "Python runtime" "FAIL" "Python 3 not found"
fi

# Test 6: Check server files
echo -e "${YELLOW}[6/8]${NC} Checking server files..."
MISSING_FILES=""
for file in server_enhanced_with_lsp.py terry-form-mcp.py terraform_lsp_client.py mcp_request_validator.py github_app_auth.py github_repo_handler.py; do
    if ! docker run --rm $IMAGE_NAME test -f "/app/$file"; then
        MISSING_FILES="$MISSING_FILES $file"
    fi
done

if [ -z "$MISSING_FILES" ]; then
    test_result "Required server files" "PASS" "All 6 files present"
else
    test_result "Required server files" "FAIL" "Missing:$MISSING_FILES"
fi

# Test 7: Check MCP tool count
echo -e "${YELLOW}[7/8]${NC} Checking MCP tools..."
TOOL_COUNT=$(docker run --rm $IMAGE_NAME python3 -c "
import sys
sys.path.append('/app')
import re

with open('/app/server_enhanced_with_lsp.py', 'r') as f:
    content = f.read()
    tools = re.findall(r'@mcp\.tool\(\)', content)
    print(len(tools))
" 2>/dev/null || echo "0")

if [ "$TOOL_COUNT" = "25" ]; then
    test_result "MCP tools count" "PASS" "All 25 tools defined"
else
    test_result "MCP tools count" "FAIL" "Found $TOOL_COUNT tools (expected 25)"
fi

# Test 8: Test server startup (brief check)
echo -e "${YELLOW}[8/8]${NC} Testing server startup..."
STARTUP_TEST=$(timeout 3 docker run --rm $IMAGE_NAME 2>&1 | grep -o "Starting MCP server" || echo "")
if [ -n "$STARTUP_TEST" ]; then
    test_result "Server startup" "PASS" "Server initializes successfully"
else
    test_result "Server startup" "FAIL" "Server failed to start"
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Test Summary                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS_COUNT"
echo -e "${RED}Failed:${NC} $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ All Tests Passed - Server is Production Ready!        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Run server: ${YELLOW}docker run -it --rm -v \"\$(pwd):/mnt/workspace\" $IMAGE_NAME${NC}"
    echo -e "  2. See QUICKSTART.md for configuration examples"
    echo -e "  3. Configure your MCP client (Claude Desktop, etc.)"
    echo ""
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ Some Tests Failed - Please Review Errors Above        ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi
