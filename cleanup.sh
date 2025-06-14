#!/bin/bash

# ============================================================================
# TERRY-FORM-MCP - Cleanup Script
# ============================================================================
#
# This script performs cleanup after the consolidated project structure
# has been pushed to GitHub.
#
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Terry-Form MCP Project Cleanup${NC}"
echo "=================================="

# Step 1: Rename files
echo -e "${YELLOW}Renaming consolidated files to standard names...${NC}"

# Backup originals first
if [ -f "Dockerfile" ]; then
  mv Dockerfile Dockerfile.bak
  echo "  Backed up original Dockerfile to Dockerfile.bak"
fi

if [ -f "build.sh" ]; then
  mv build.sh build.sh.bak
  echo "  Backed up original build.sh to build.sh.bak"
fi

# Rename consolidated files
mv Dockerfile.consolidated Dockerfile
mv build.consolidated.sh build.sh
chmod +x build.sh

echo -e "${GREEN}✅ Files renamed successfully${NC}"

# Step 2: Remove redundant files
echo -e "\n${YELLOW}Removing redundant files...${NC}"

# List of files to remove
REDUNDANT_FILES=(
  "Dockerfile_alpine_fallback"
  "Dockerfile_enhanced_lsp"
  "Dockerfile_enhanced_lsp_fixed"
  "Dockerfile_with_lsp"
  "build_lsp.sh"
  "build_enhanced_lsp.sh"
  "build_lsp_robust.sh"
  "server.py"
  "server_with_lsp.py"
  "terraform_lsp_client_original.py"
  "README.md.new"
  ".gitignore.new"
)

for file in "${REDUNDANT_FILES[@]}"; do
  if [ -f "$file" ]; then
    rm "$file"
    echo "  Removed $file"
  fi
done

echo -e "${GREEN}✅ Redundant files removed${NC}"

# Step 3: Update local git
echo -e "\n${YELLOW}Updating local git repository...${NC}"

git pull origin main
git checkout main

echo -e "${GREEN}✅ Local git repository updated${NC}"

echo -e "\n${GREEN}🎉 Cleanup complete!${NC}"
echo "The project structure has been simplified and consolidated."
echo "You can now build the Docker image with: ./build.sh"
