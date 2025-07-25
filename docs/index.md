---
layout: home
title: Terry-Form MCP - Enterprise Terraform Automation
description: Secure, intelligent infrastructure management through Model Context Protocol
---

<div class="hero-section">
  <h1 class="hero-title">Terry-Form MCP</h1>
  <p class="hero-subtitle">Enterprise-grade Terraform automation through Model Context Protocol</p>
  <div class="hero-buttons">
    <a href="{{ site.baseurl }}/getting-started" class="btn btn-primary">Get Started</a>
    <a href="{{ site.baseurl }}/guides/" class="btn btn-secondary">View Guides</a>
    <a href="https://github.com/aj-geddes/terry-form-mcp" class="btn btn-github">
      <i class="fab fa-github"></i> GitHub
    </a>
  </div>
</div>

<div class="features-grid">
  <div class="feature-card">
    <div class="feature-icon">🔒</div>
    <h3>Security First</h3>
    <p>Enterprise-hardened with comprehensive security controls, input validation, and sandboxed execution</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">🤖</div>
    <h3>AI-Powered</h3>
    <p>Intelligent automation with MCP protocol integration for seamless AI assistant workflows</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">☁️</div>
    <h3>Multi-Cloud</h3>
    <p>Support for AWS, Azure, GCP, and Terraform Cloud with unified management interface</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">🔧</div>
    <h3>Developer Friendly</h3>
    <p>LSP integration, GitHub App support, and comprehensive API for modern DevOps workflows</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">📊</div>
    <h3>Analytics & Insights</h3>
    <p>Module intelligence, security scanning, and best practice recommendations</p>
  </div>
  
  <div class="feature-card">
    <div class="feature-icon">🚀</div>
    <h3>Production Ready</h3>
    <p>Docker, Kubernetes, and cloud-native deployment options with monitoring</p>
  </div>
</div>

## What is Terry-Form MCP?

Terry-Form MCP is a secure, enterprise-grade Terraform automation server that integrates with AI assistants through the Model Context Protocol (MCP). It provides a controlled environment for infrastructure-as-code operations while maintaining strict security boundaries.

```mermaid
graph LR
    A[AI Assistant] -->|MCP Protocol| B[Terry-Form Server]
    B --> C[Terraform Executor]
    B --> D[Security Layer]
    B --> E[Cloud Providers]
    C --> F[Infrastructure]
    D --> G[Validation]
    D --> H[Sandboxing]
```

## Key Features

### 🛡️ **Security Hardened**
- **Input Validation**: Comprehensive request validation and sanitization
- **Path Traversal Protection**: Secure file system access controls
- **Command Injection Prevention**: Safe subprocess execution
- **Sandboxed Execution**: Isolated Terraform operations

### 🔌 **MCP Protocol Integration**
- **Native MCP Support**: Built for AI assistant integration
- **Tool Discovery**: Automatic tool registration and documentation
- **Streaming Responses**: Real-time operation feedback
- **Error Handling**: Graceful error reporting and recovery

### 🏗️ **Infrastructure Management**
- **Multi-Workspace**: Manage multiple Terraform workspaces
- **State Management**: Secure state file handling
- **Plan Analysis**: Intelligent plan review and recommendations
- **Module Intelligence**: Best practice analysis and optimization

### 🔗 **Integrations**
- **GitHub App**: Direct repository integration
- **Terraform Cloud**: Native Terraform Cloud support
- **LSP Support**: Language Server Protocol for IDE integration
- **Web Dashboard**: Real-time monitoring and control

## Quick Start

```bash
# Using Docker
docker run -d \
  -p 3000:3000 \
  -v /path/to/workspace:/mnt/workspace \
  aj-geddes/terry-form-mcp:latest

# Using Docker Compose
docker-compose up -d

# Configure your AI assistant
{
  "mcpServers": {
    "terry-form": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-v", "./workspace:/mnt/workspace", "terry-form-mcp"]
    }
  }
}
```

## Use Cases

<div class="use-cases">
  <div class="use-case">
    <h3>🏢 Enterprise Infrastructure</h3>
    <p>Manage complex multi-cloud environments with security controls and compliance</p>
  </div>
  
  <div class="use-case">
    <h3>🔄 CI/CD Integration</h3>
    <p>Automate infrastructure provisioning in your deployment pipelines</p>
  </div>
  
  <div class="use-case">
    <h3>👥 Team Collaboration</h3>
    <p>Enable safe infrastructure changes through AI-assisted workflows</p>
  </div>
  
  <div class="use-case">
    <h3>📚 Learning Platform</h3>
    <p>Safe environment for learning and experimenting with Terraform</p>
  </div>
</div>

## Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        A[Claude/AI Assistant]
        B[Web Dashboard]
        C[CLI Tools]
    end
    
    subgraph "Terry-Form MCP"
        D[MCP Server]
        E[Web Server]
        F[Security Layer]
        G[Terraform Executor]
        H[GitHub App Handler]
        I[Cloud Integrations]
    end
    
    subgraph "Infrastructure"
        J[AWS]
        K[Azure]
        L[GCP]
        M[Terraform Cloud]
    end
    
    A -->|MCP| D
    B -->|HTTP| E
    C -->|MCP| D
    D --> F
    E --> F
    F --> G
    F --> H
    F --> I
    G --> J
    G --> K
    G --> L
    I --> M
```

## Getting Help

<div class="help-section">
  <div class="help-card">
    <h3>📖 Documentation</h3>
    <p>Comprehensive guides and API reference</p>
    <a href="{{ site.baseurl }}/guides/">View Guides →</a>
  </div>
  
  <div class="help-card">
    <h3>💬 Community</h3>
    <p>Join our community for support and discussions</p>
    <a href="https://github.com/aj-geddes/terry-form-mcp/discussions">GitHub Discussions →</a>
  </div>
  
  <div class="help-card">
    <h3>🐛 Issues</h3>
    <p>Report bugs or request features</p>
    <a href="https://github.com/aj-geddes/terry-form-mcp/issues">GitHub Issues →</a>
  </div>
</div>

## Latest Updates

{% for post in site.posts limit:3 %}
<article class="update-card">
  <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
  <time>{{ post.date | date: "%B %d, %Y" }}</time>
  <p>{{ post.excerpt }}</p>
</article>
{% endfor %}

---

<div class="footer-cta">
  <h2>Ready to get started?</h2>
  <p>Deploy Terry-Form MCP in minutes and start automating your infrastructure</p>
  <a href="{{ site.baseurl }}/getting-started" class="btn btn-large">Get Started Now →</a>
</div>