#!/bin/bash
# MCP Client wrapper for Terry-Form MCP in Kubernetes
# This script handles the connection to Terry-Form MCP running in Kubernetes

set -e

# Configuration
NAMESPACE="terry-form-system"
SERVICE_NAME="terry-form-mcp"
LOCAL_PORT="8080"
REMOTE_PORT="8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Terry-Form MCP Client Wrapper${NC}"
echo "================================"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if minikube is running (if using minikube)
if command -v minikube &> /dev/null; then
    if ! minikube status &> /dev/null; then
        echo -e "${YELLOW}Warning: Minikube is not running${NC}"
        echo "Starting minikube..."
        minikube start
    fi
fi

# Check if namespace exists
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo -e "${RED}Error: Namespace $NAMESPACE does not exist${NC}"
    echo "Please deploy Terry-Form MCP first using:"
    echo "  helm install terry-form-mcp ./deploy/kubernetes/helm/terry-form-mcp --namespace $NAMESPACE --create-namespace"
    exit 1
fi

# Check if service exists
if ! kubectl get service $SERVICE_NAME -n $NAMESPACE &> /dev/null; then
    echo -e "${RED}Error: Service $SERVICE_NAME not found in namespace $NAMESPACE${NC}"
    exit 1
fi

# Check if pods are ready
echo "Checking pod status..."
READY_PODS=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=terry-form-mcp -o jsonpath='{.items[?(@.status.conditions[?(@.type=="Ready")].status=="True")].metadata.name}')

if [ -z "$READY_PODS" ]; then
    echo -e "${RED}Error: No ready pods found${NC}"
    echo "Pod status:"
    kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=terry-form-mcp
    exit 1
fi

echo -e "${GREEN}Ready pods found: $READY_PODS${NC}"

# Kill any existing port-forward
echo "Cleaning up existing port forwards..."
pkill -f "kubectl port-forward.*$SERVICE_NAME" || true
sleep 1

# Start port forwarding
echo -e "${YELLOW}Starting port forward to $SERVICE_NAME...${NC}"
kubectl port-forward -n $NAMESPACE service/$SERVICE_NAME $LOCAL_PORT:$REMOTE_PORT &
PF_PID=$!

# Wait for port forward to be ready
echo "Waiting for port forward to be ready..."
sleep 3

# Test connection
echo "Testing connection..."
if curl -s http://localhost:$LOCAL_PORT/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connection successful!${NC}"
    echo ""
    echo "Terry-Form MCP is now available at: http://localhost:$LOCAL_PORT"
    echo ""
    echo "MCP Endpoints:"
    echo "  - Health: http://localhost:$LOCAL_PORT/health"
    echo "  - Ready:  http://localhost:$LOCAL_PORT/ready"
    echo "  - MCP:    http://localhost:$LOCAL_PORT/mcp"
    echo ""
    echo "Port forward PID: $PF_PID"
    echo ""
    echo -e "${YELLOW}Keep this terminal open to maintain the connection${NC}"
    echo "Press Ctrl+C to stop the port forward"
    
    # Keep the script running
    wait $PF_PID
else
    echo -e "${RED}✗ Connection failed!${NC}"
    kill $PF_PID 2>/dev/null || true
    exit 1
fi