---
layout: page
title: Tutorials
description: Step-by-step tutorials for Terry-Form MCP
---

# Tutorials

Learn Terry-Form MCP through hands-on tutorials.

<div class="tutorial-grid">
{% for tutorial in site.tutorials %}
  <div class="tutorial-card">
    <div class="tutorial-header">
      <h3><a href="{{ tutorial.url | relative_url }}">{{ tutorial.title }}</a></h3>
      <div class="tutorial-meta">
        <span class="difficulty difficulty-{{ tutorial.difficulty }}">{{ tutorial.difficulty | capitalize }}</span>
        <span class="duration">⏱️ {{ tutorial.duration }}</span>
      </div>
    </div>
    <p>{{ tutorial.description }}</p>
    {% if tutorial.topics %}
    <div class="tutorial-topics">
      {% for topic in tutorial.topics %}
      <span class="topic">{{ topic }}</span>
      {% endfor %}
    </div>
    {% endif %}
  </div>
{% endfor %}
</div>

## Featured Tutorials

### 🚀 Getting Started

<div class="featured-tutorial">
  <h4><a href="{{ site.baseurl }}/tutorials/first-steps">Your First Terry-Form Project</a></h4>
  <p>Learn the basics of Terry-Form MCP by creating your first infrastructure project.</p>
  <ul>
    <li>Setting up your workspace</li>
    <li>Basic Terraform operations</li>
    <li>Understanding MCP tools</li>
  </ul>
</div>

### ☁️ Cloud Providers

<div class="featured-tutorial">
  <h4><a href="{{ site.baseurl }}/tutorials/aws-infrastructure">Building AWS Infrastructure</a></h4>
  <p>Complete guide to managing AWS resources with Terry-Form MCP.</p>
  <ul>
    <li>VPC and networking setup</li>
    <li>EC2 and Auto Scaling</li>
    <li>RDS and storage solutions</li>
  </ul>
</div>

<div class="featured-tutorial">
  <h4><a href="{{ site.baseurl }}/tutorials/multi-cloud">Multi-Cloud Deployment</a></h4>
  <p>Deploy infrastructure across AWS, Azure, and GCP simultaneously.</p>
  <ul>
    <li>Provider configuration</li>
    <li>Cross-cloud networking</li>
    <li>Unified state management</li>
  </ul>
</div>

### 🔧 Advanced Topics

<div class="featured-tutorial">
  <h4><a href="{{ site.baseurl }}/tutorials/gitops-workflow">GitOps with Terry-Form</a></h4>
  <p>Implement GitOps workflows using GitHub integration.</p>
  <ul>
    <li>Repository structure</li>
    <li>Pull request automation</li>
    <li>CI/CD integration</li>
  </ul>
</div>

<div class="featured-tutorial">
  <h4><a href="{{ site.baseurl }}/tutorials/module-development">Creating Terraform Modules</a></h4>
  <p>Build reusable Terraform modules with best practices.</p>
  <ul>
    <li>Module structure</li>
    <li>Input validation</li>
    <li>Testing and documentation</li>
  </ul>
</div>

## Tutorial Series

### Infrastructure as Code Fundamentals
1. [Introduction to IaC]({{ site.baseurl }}/tutorials/iac-intro)
2. [Terraform Basics]({{ site.baseurl }}/tutorials/terraform-basics)
3. [State Management]({{ site.baseurl }}/tutorials/state-management)
4. [Module Composition]({{ site.baseurl }}/tutorials/module-composition)

### Security and Compliance
1. [Security Scanning]({{ site.baseurl }}/tutorials/security-scanning)
2. [Policy as Code]({{ site.baseurl }}/tutorials/policy-as-code)
3. [Compliance Automation]({{ site.baseurl }}/tutorials/compliance)
4. [Secret Management]({{ site.baseurl }}/tutorials/secrets)

### Production Workflows
1. [Environment Management]({{ site.baseurl }}/tutorials/environments)
2. [Blue-Green Deployments]({{ site.baseurl }}/tutorials/blue-green)
3. [Disaster Recovery]({{ site.baseurl }}/tutorials/disaster-recovery)
4. [Cost Optimization]({{ site.baseurl }}/tutorials/cost-optimization)

## Interactive Examples

### Try It Now

<div class="try-it-box">
  <h4>Quick Example: Validate Terraform Configuration</h4>
  <p>Ask your AI assistant:</p>
  <pre><code>"Can you validate the Terraform configuration in my workspace/example folder?"</code></pre>
  <p>The assistant will use Terry-Form MCP to check your configuration and provide feedback.</p>
</div>

## Video Tutorials

<div class="video-section">
  <div class="video-card">
    <h4>🎥 Getting Started with Terry-Form MCP</h4>
    <p>15-minute introduction covering installation and basic usage.</p>
    <a href="#" class="video-link">Watch on YouTube →</a>
  </div>
  
  <div class="video-card">
    <h4>🎥 Advanced Terraform Patterns</h4>
    <p>Deep dive into advanced patterns and best practices.</p>
    <a href="#" class="video-link">Watch on YouTube →</a>
  </div>
</div>

## Contributing Tutorials

We welcome tutorial contributions! If you have a tutorial idea:

1. Check our [tutorial guidelines]({{ site.baseurl }}/contributing#tutorials)
2. Create a pull request with your tutorial
3. Use our [tutorial template]({{ site.baseurl }}/templates/tutorial)

## Need Help?

- 💬 Join our [Community Discord](https://discord.gg/terry-form)
- 📧 Email us at [tutorials@terry-form.io](mailto:tutorials@terry-form.io)
- 🐛 Report issues on [GitHub](https://github.com/aj-geddes/terry-form-mcp/issues)

<style>
.tutorial-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.tutorial-card {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid #e9ecef;
  transition: transform 0.2s;
}

.tutorial-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.tutorial-header {
  margin-bottom: 1rem;
}

.tutorial-meta {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.difficulty {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 500;
}

.difficulty-beginner {
  background: #e8f5e9;
  color: #2e7d32;
}

.difficulty-intermediate {
  background: #fff3e0;
  color: #f57c00;
}

.difficulty-advanced {
  background: #ffebee;
  color: #d32f2f;
}

.tutorial-topics {
  margin-top: 1rem;
}

.topic {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background: #e3f2fd;
  color: #1565c0;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  margin-right: 0.5rem;
}

.featured-tutorial {
  background: #f0f7ff;
  padding: 1.5rem;
  border-radius: 0.5rem;
  margin: 1rem 0;
  border-left: 4px solid #2196F3;
}

.featured-tutorial h4 {
  margin-top: 0;
}

.try-it-box {
  background: #e8f5e9;
  padding: 1.5rem;
  border-radius: 0.5rem;
  margin: 2rem 0;
  border-left: 4px solid #4CAF50;
}

.try-it-box pre {
  background: rgba(255,255,255,0.8);
  padding: 1rem;
  border-radius: 0.25rem;
  margin: 1rem 0;
}

.video-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin: 2rem 0;
}

.video-card {
  background: #f5f5f5;
  padding: 1.5rem;
  border-radius: 0.5rem;
  text-align: center;
}

.video-link {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #ff0000;
  color: white;
  border-radius: 0.25rem;
  text-decoration: none;
}

.video-link:hover {
  background: #dc0000;
}

@media (prefers-color-scheme: dark) {
  .tutorial-card {
    background: #2a2a2a;
    border-color: #444;
  }
  
  .featured-tutorial {
    background: #1a1a2e;
  }
  
  .try-it-box {
    background: #1e3a1e;
  }
  
  .try-it-box pre {
    background: rgba(0,0,0,0.3);
  }
  
  .video-card {
    background: #2a2a2a;
  }
}
</style>