#!/bin/bash

echo "╔═════════════════════════════════════════════════════════════╗"
echo "║ Terry-Form-MCP Environment Check Script                    ║"
echo "║ Validating development and runtime environment             ║"
echo "╚═════════════════════════════════════════════════════════════╝"

# Function to check command availability
check_command() {
  if command -v $1 &> /dev/null; then
    echo "✅ $1 is installed"
    return 0
  else
    echo "❌ $1 is not installed"
    return 1
  fi
}

# Function to check Python package
check_python_package() {
  if python3 -c "import $1" &> /dev/null; then
    echo "✅ Python package '$1' is installed"
    return 0
  else
    echo "❌ Python package '$1' is not installed"
    return 1
  fi
}

# Check basic commands
echo "\n----- Checking Basic Commands -----"
check_command python3
check_command pip3
check_command docker
check_command terraform

# Check required Python packages
echo "\n----- Checking Python Packages -----"
check_python_package fastmcp
check_python_package asyncio
check_python_package json
check_python_package subprocess

# Check Docker status
echo "\n----- Checking Docker Service -----"
if docker info &> /dev/null; then
  echo "✅ Docker service is running"
else
  echo "❌ Docker service is not running or not accessible"
fi

# Check Terraform version
echo "\n----- Checking Terraform Version -----"
TF_VERSION=$(terraform version | head -n 1)
echo "ℹ️ $TF_VERSION"

# Check for terraform-ls
echo "\n----- Checking terraform-ls -----"
if check_command terraform-ls; then
  TF_LS_VERSION=$(terraform-ls version | head -n 1)
  echo "ℹ️ $TF_LS_VERSION"
fi

# Check for existing Terry-Form-MCP Docker images
echo "\n----- Checking Terry-Form-MCP Docker Images -----"
TERRY_IMAGES=$(docker images --format "{{.Repository}}" | grep -E "terry-form-mcp.*" || echo "")

if [ -n "$TERRY_IMAGES" ]; then
  echo "✅ Found Terry-Form-MCP Docker images:"
  docker images --format "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | grep -E "terry-form-mcp.*"
else
  echo "❌ No Terry-Form-MCP Docker images found"
fi

# Check required files
echo "\n----- Checking Required Files -----"
FILES=("server.py" "server_with_lsp.py" "server_enhanced_with_lsp.py" "terry-form-mcp.py" "terraform_lsp_client.py" "Dockerfile" "Dockerfile_with_lsp" "Dockerfile_enhanced_lsp")

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "✅ $file exists"
  else
    echo "❌ $file is missing"
  fi
done

# Check workspace directory
echo "\n----- Checking Workspace Directory -----"
if [ -d "/mnt/workspace" ]; then
  echo "✅ /mnt/workspace directory exists"
else
  echo "❌ /mnt/workspace directory does not exist"
  echo "   This is required for Docker container operation"
fi

echo "\n----- Environment Check Complete -----"

# Summary
echo "\n----- Summary -----"
echo "Development Environment: $(check_command python3 && check_command pip3 && check_python_package fastmcp && check_python_package asyncio > /dev/null && echo "✅ Ready" || echo "❌ Missing components")"
echo "Docker Environment: $(docker info &> /dev/null && echo "✅ Ready" || echo "❌ Not available")"
echo "Terraform Tools: $(check_command terraform && check_command terraform-ls > /dev/null && echo "✅ Ready" || echo "❌ Missing components")"
echo "Required Files: $([ $(ls -1 ${FILES[@]} 2>/dev/null | wc -l) -eq ${#FILES[@]} ] && echo "✅ All present" || echo "❌ Some missing")"
