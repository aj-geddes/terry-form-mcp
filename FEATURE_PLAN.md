# 🚀 Feature: Local and Enterprise Modes for Terry

## Problem Statement
Terry currently operates as a single-mode MCP server. We need to split functionality into:
- **Local Mode**: Lightweight, registry-only features for individual developers
- **Enterprise Mode**: Full-featured K8s deployment with MCP bridge and web UI

## Proposed Solution

### Mode Configuration
- Add `MODE` environment variable: `local` (default) or `enterprise`
- Create mode-specific logic in `src/modes/`
- Feature toggling based on mode

### Local Mode
- **Features**: Terraform Registry tools only (no TFC operations)
- **Deployment**: npm/npx, Docker, or direct execution
- **No authentication required**
- **Simple status endpoint**

### Enterprise Mode
- **Features**: All tools including TFC operations
- **Kubernetes deployment** with Helm charts
- **Architecture**:
  ```
  [Web UI] <-> [Terry MCP Server] <-> [MCP Bridge] <-> [LLM Service]
                         |
                    [TF Registry]
                    [TF Cloud API]
  ```
- **Service mesh** for inter-service communication
- **Web dashboard** showing mode, services, metrics

### Key Changes
1. ✅ Remove any OpenAI/Anthropic API key support (currently none exist)
2. 📊 Add web UI with mode status display
3. 🚢 Create K8s deployment manifests and Helm charts
4. 🌉 Implement MCP bridge for LLM communication
5. 🔧 Mode-specific tool registration

## Implementation Plan

**Phase 1: Mode Infrastructure**
- [ ] Add mode configuration and detection
- [ ] Create mode-specific tool registration
- [ ] Update tests for both modes

**Phase 2: Web UI**
- [ ] Create Express server with status endpoints
- [ ] Build simple HTML dashboard
- [ ] Display current mode and available tools

**Phase 3: Enterprise Deployment**
- [ ] Design K8s architecture
- [ ] Create deployment manifests
- [ ] Implement MCP bridge integration
- [ ] Add Helm chart

**Phase 4: Documentation**
- [ ] Update README with mode information
- [ ] Create deployment guides
- [ ] Add enterprise setup instructions

## Benefits
- **Zero-config local mode** for developers
- **Scalable enterprise mode** with monitoring
- **Clear feature separation**
- **Progressive enhancement** path

## Technical Details
- No breaking changes to existing MCP interface
- Backward compatible with current deployments
- Enterprise mode requires TFC_TOKEN
- Local mode works offline (registry data permitting)

## Open Questions
1. Which MCP bridge solution should we use for LLM integration?
2. Should we support multiple LLM providers in enterprise mode?
3. What metrics should the web UI display?

---
**Branch**: `feature/local-enterprise`