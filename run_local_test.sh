#!/bin/bash
# Run Terry-Form MCP and Frontend for local testing

set -e

echo "Terry-Form MCP Local Test Environment"
echo "===================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if port forwarding is already running
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Port 8080 already in use (MCP server or port-forward running)${NC}"
else
    # Check if we should use Kubernetes
    if kubectl get namespace terry-form-system >/dev/null 2>&1; then
        echo -e "${YELLOW}Starting port-forward to Kubernetes...${NC}"
        kubectl port-forward -n terry-form-system service/terry-form-mcp 8080:8000 &
        PF_PID=$!
        echo "Port-forward PID: $PF_PID"
        sleep 3
    else
        echo -e "${RED}Terry-Form MCP not found in Kubernetes${NC}"
        echo "Please deploy it first or run locally"
        exit 1
    fi
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ] && [ ! -f "frontend/.deps_installed" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd frontend
    pip install -r requirements.txt
    touch .deps_installed
    cd ..
fi

# Start the frontend
echo -e "${GREEN}Starting frontend on http://localhost:7575${NC}"
cd frontend
python app.py &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}Test environment is ready!${NC}"
echo ""
echo "Frontend: http://localhost:7575"
echo "MCP Server: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop all services"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$PF_PID" ]; then
        kill $PF_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}Cleanup complete${NC}"
    exit 0
}

trap cleanup INT TERM

# Wait for interrupt
wait