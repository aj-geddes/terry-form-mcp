---
layout: page
title: Guides
description: Comprehensive guides for Terry-Form MCP
---

# Guides

Explore our comprehensive guides to master Terry-Form MCP.

<div class="guide-grid">
{% for guide in site.guides %}
  <div class="guide-card">
    <h3><a href="{{ guide.url | relative_url }}">{{ guide.title }}</a></h3>
    <p>{{ guide.description }}</p>
    <div class="guide-meta">
      <span class="read-time">{{ guide.content | reading_time }}</span>
    </div>
  </div>
{% endfor %}
</div>

## Featured Guides

### 🔒 [Security Guide]({{ site.baseurl }}/guides/security)
Learn about Terry-Form MCP's security features, best practices, and how to configure security settings for production environments.

### 🚀 [Production Deployment]({{ site.baseurl }}/guides/production)
Step-by-step guide for deploying Terry-Form MCP in production with high availability, monitoring, and scaling.

### 🔧 [Configuration Reference]({{ site.baseurl }}/guides/configuration)
Complete reference for all configuration options, environment variables, and customization settings.

### 🔌 [Integrations]({{ site.baseurl }}/guides/integrations)
Connect Terry-Form MCP with GitHub, Terraform Cloud, CI/CD pipelines, and monitoring systems.

### 🐳 [Docker & Kubernetes]({{ site.baseurl }}/guides/containers)
Container deployment strategies, Kubernetes manifests, and orchestration best practices.

### 📊 [Monitoring & Observability]({{ site.baseurl }}/guides/monitoring)
Set up comprehensive monitoring, logging, and alerting for your Terry-Form MCP deployment.

## Guide Categories

### Getting Started
- [Quick Start]({{ site.baseurl }}/getting-started)
- [Installation Options]({{ site.baseurl }}/guides/installation)
- [First Steps]({{ site.baseurl }}/guides/first-steps)

### Operations
- [Daily Operations]({{ site.baseurl }}/guides/operations)
- [Troubleshooting]({{ site.baseurl }}/guides/troubleshooting)
- [Performance Tuning]({{ site.baseurl }}/guides/performance)

### Advanced Topics
- [Custom Providers]({{ site.baseurl }}/guides/custom-providers)
- [Plugin Development]({{ site.baseurl }}/guides/plugins)
- [API Extensions]({{ site.baseurl }}/guides/api-extensions)

### Best Practices
- [Terraform Best Practices]({{ site.baseurl }}/guides/terraform-best-practices)
- [Security Hardening]({{ site.baseurl }}/guides/security-hardening)
- [Cost Optimization]({{ site.baseurl }}/guides/cost-optimization)

## Contributing

Have a guide idea or found an issue? We welcome contributions!

- [Contributing Guidelines]({{ site.baseurl }}/contributing)
- [Style Guide]({{ site.baseurl }}/guides/style-guide)
- [Submit a Guide](https://github.com/aj-geddes/terry-form-mcp/issues/new?template=guide-proposal.md)

<style>
.guide-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.guide-card {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid #e9ecef;
  transition: transform 0.2s, box-shadow 0.2s;
}

.guide-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.guide-card h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
}

.guide-card a {
  color: inherit;
  text-decoration: none;
}

.guide-card a:hover {
  color: #2196F3;
}

.guide-meta {
  margin-top: 1rem;
  font-size: 0.875rem;
  color: #6c757d;
}

.read-time::before {
  content: "📖 ";
}

@media (prefers-color-scheme: dark) {
  .guide-card {
    background: #2a2a2a;
    border-color: #444;
  }
}
</style>