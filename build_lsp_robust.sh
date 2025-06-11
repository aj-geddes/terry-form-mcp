#!/bin/bash

echo "╔═════════════════════════════════════════════════════════════╗"
echo "║ Terry-Form-MCP LSP Docker Build Script - Phase 4/5         ║"
echo "║ Building terry-form-mcp-lsp-enhanced Docker image          ║"
echo "╚═════════════════════════════════════════════════════════════╝"

# Set error handling
set -e

# Function to print status with emoji
print_status() {
  local status=$1
  local message=$2
  
  if [ $status -eq 0 ]; then
    echo "✅ $message"
  else
    echo "❌ $message (exit code: $status)"
    return 1
  fi
}

# Function to print section header
print_section() {
  echo -e "\n----- $1 -----"
  echo -e "$(date '+%Y-%m-%d %H:%M:%S') - $1\n"
}

# Check for Docker
print_section "Checking Docker installation"
if ! command -v docker &> /dev/null; then
  echo "❌ Docker is not installed or not in PATH"
  exit 1
fi
print_status 0 "Docker is installed"

# Attempt to use the official HashiCorp image
print_section "Building Docker image with official HashiCorp base image"
echo "Building image using Dockerfile_enhanced_lsp with official hashicorp/terraform base..."
docker build -t terry-form-mcp-lsp-enhanced -f Dockerfile_enhanced_lsp . && build_status=$? || build_status=$?

# If the official image build fails, try the Alpine fallback
if [ $build_status -ne 0 ]; then
  echo "❌ Official HashiCorp image build failed with status: $build_status"
  
  echo -e "\n📋 Docker Registry Troubleshooting:\n"
  echo "1. The build failed trying to use hashicorp/terraform:latest base image."
  echo "   This usually indicates Docker registry connectivity issues.\n"
  
  echo "2. Attempting to authenticate with Docker Hub:"
  docker login && login_status=$? || login_status=$?
  
  if [ $login_status -ne 0 ]; then
    echo "❌ Docker Hub authentication failed. Using Alpine fallback image instead."
    
    echo -e "\n🔄 Building with Alpine fallback image (this is not recommended for production)\n"
    docker build -t terry-form-mcp-lsp-alpine -f Dockerfile_alpine_fallback . && alpine_status=$? || alpine_status=$?
    
    if [ $alpine_status -eq 0 ]; then
      echo "✅ Alpine fallback image built successfully as terry-form-mcp-lsp-alpine"
      echo "⚠️ Note: The Alpine fallback image may have different behavior than the official HashiCorp image."
      echo "   Please use this only for testing and development."
      
      # Tag the Alpine image with the expected name to make the rest of the script work
      docker tag terry-form-mcp-lsp-alpine terry-form-mcp-lsp-enhanced
    else
      echo "❌ Alpine fallback image build failed with status: $alpine_status"
      exit 1
    fi
  else
    echo "✅ Docker Hub authentication successful, but build still failed."
    echo "   This might indicate other issues. Please check the error messages above."
    exit 1
  fi
else
  print_status $build_status "Docker image terry-form-mcp-lsp-enhanced built successfully!"
fi

# Test 1: Check if terraform-ls is available in the container
print_section "Verifying terraform-ls binary"
docker run --rm terry-form-mcp-lsp-enhanced which terraform-ls && ls_status=$? || ls_status=$?
print_status $ls_status "terraform-ls binary check"

# Test 2: Check terraform-ls version
print_section "Checking terraform-ls version"
docker run --rm terry-form-mcp-lsp-enhanced terraform-ls version && ls_version_status=$? || ls_version_status=$?
print_status $ls_version_status "terraform-ls version check"

# Test 3: Check if Python works in the container
print_section "Testing Python in container"
docker run --rm terry-form-mcp-lsp-enhanced python3 -c "print('Python works!')" && python_status=$? || python_status=$?
print_status $python_status "Python functionality check"

# Test 4: Check if the server files are in the correct location
print_section "Checking server files"
docker run --rm terry-form-mcp-lsp-enhanced ls -la /app && ls_app_status=$? || ls_app_status=$?
print_status $ls_app_status "Server files check"

# Summary
print_section "Build Summary"
echo "Docker image build: $([ $build_status -eq 0 ] && echo "✅ Success" || echo "❌ Failed")"
echo "terraform-ls binary: $([ $ls_status -eq 0 ] && echo "✅ Available" || echo "❌ Not found")"
echo "terraform-ls version: $([ $ls_version_status -eq 0 ] && echo "✅ Verified" || echo "❌ Failed")"
echo "Python functionality: $([ $python_status -eq 0 ] && echo "✅ Working" || echo "❌ Failed")"
echo "Server files: $([ $ls_app_status -eq 0 ] && echo "✅ Present" || echo "❌ Missing")"

# Final result
if [ $build_status -eq 0 ] && [ $ls_status -eq 0 ] && [ $python_status -eq 0 ] && [ $ls_app_status -eq 0 ]; then
  echo -e "\n✅ BUILD SUCCESSFUL! The Terry-Form-MCP with LSP integration is ready!\n"
  
  echo "🚀 You can now use the terry-form-mcp-lsp-enhanced image with Claude Desktop."
  echo -e "\n📚 Update your claude_desktop_config.json to use the new image:"
  echo "
{
  \"mcpServers\": {
    \"terry\": {
      \"command\": \"docker\",
      \"args\": [
        \"run\", \"-i\", \"--rm\",
        \"-v\", \"C:\\\\Users\\\\YourUsername\\\\terraform-projects:/mnt/workspace\",
        \"terry-form-mcp-lsp-enhanced\",
        \"python3\", \"server_enhanced_with_lsp.py\"
      ]
    }
  }
}
"
  
  echo -e "\n📋 Phase 4 of the Terry-Form-MCP LSP Integration Project is complete!"
  echo "   Ready for Phase 5: Production LSP Feature Testing"
  exit 0
else
  echo -e "\n❌ BUILD FAILED! Please check the error messages above."
  exit 1
fi