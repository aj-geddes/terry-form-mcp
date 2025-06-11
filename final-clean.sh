cat > final_cleanup.sh << 'EOF'
#!/bin/bash

# ============================================================================
# TERRY-FORM-MCP - Final Cleanup Script
# ============================================================================
#
# This script performs final cleanup of redundant files from the project.
#
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Terry-Form MCP Final Cleanup${NC}"
echo "=================================="

# Step 1: Remove backup files
echo -e "${YELLOW}Removing backup files...${NC}"
BACKUP_FILES=(
  "Dockerfile.bak"
  "build.sh.bak"
)

for file in "${BACKUP_FILES[@]}"; do
  if [ -f "$file" ]; then
    rm "$file"
    echo "  Removed $file"
  fi
done

echo -e "${GREEN}✅ Backup files removed${NC}"

# Step 2: Remove redundant Terraform test files
echo -e "\n${YELLOW}Removing redundant Terraform test files...${NC}"
TEST_FILES=(
  "debug_container.tf"
  "docker_check.tf"
  "execute_build.tf"
  "terraform-ls-test.tf"
)

for file in "${TEST_FILES[@]}"; do
  if [ -f "$file" ]; then
    rm "$file"
    echo "  Removed $file"
  fi
done

echo -e "${GREEN}✅ Terraform test files removed${NC}"

# Step 3: Remove testing and debugging files
echo -e "\n${YELLOW}Removing testing and debugging files...${NC}"
DEBUG_FILES=(
  "check_environment.sh"
  "manual_validation.py"
  "test_lsp.json"
  "test_lsp_fixed.py"
  "test_lsp_integration.py"
  "cleanup.sh"
)

for file in "${DEBUG_FILES[@]}"; do
  if [ -f "$file" ]; then
    rm "$file"
    echo "  Removed $file"
  fi
done

echo -e "${GREEN}✅ Testing and debugging files removed${NC}"

# Step 4: Commit changes
echo -e "\n${YELLOW}Committing changes...${NC}"

git add -A
git commit -m "Final cleanup: Remove redundant files and backups"

# Push changes to the branch
git push origin HEAD

echo -e "${GREEN}✅ Changes committed and pushed${NC}"

# Step 5: Self-destruct
echo -e "\n${YELLOW}Self-destructing cleanup scripts...${NC}"
echo "  This script will be removed after execution"

# We don't remove this script yet since we're still executing it
# But we'll mark it for cleanup in the final message

echo -e "${GREEN}✅ Script marked for self-destruction${NC}"

echo -e "\n${GREEN}🎉 Final cleanup complete!${NC}"
echo "The project has been fully cleaned up and all redundant files removed."
echo "This script (final_cleanup.sh) can now be safely deleted."
EOF
