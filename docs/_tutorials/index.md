---
layout: page
title: Tutorials
description: Step-by-step tutorials for Terry-Form MCP
---

Learn Terry-Form MCP through hands-on tutorials.

<div class="tutorial-grid">
{% for tutorial in site.tutorials %}
  {% unless tutorial.url contains '/index' %}
  <div class="tutorial-card">
    <div class="tutorial-header">
      <h3><a href="{{ tutorial.url | relative_url }}">{{ tutorial.title }}</a></h3>
      <div class="tutorial-meta">
        {% if tutorial.difficulty %}
        <span class="difficulty difficulty-{{ tutorial.difficulty }}">{{ tutorial.difficulty | capitalize }}</span>
        {% endif %}
        {% if tutorial.duration %}
        <span class="duration">⏱️ {{ tutorial.duration }}</span>
        {% endif %}
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
  {% endunless %}
{% endfor %}
</div>

## Available Tutorials

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

---

## Coming Soon

Additional tutorials are planned for future releases. Check back soon or [contribute your own tutorial](https://github.com/aj-geddes/terry-form-mcp/issues/new)!

## Interactive Examples

### Try It Now

<div class="try-it-box">
  <h4>Quick Example: Validate Terraform Configuration</h4>
  <p>Ask your AI assistant:</p>
  <pre><code>"Can you validate the Terraform configuration in my workspace/example folder?"</code></pre>
  <p>The assistant will use Terry-Form MCP to check your configuration and provide feedback.</p>
</div>

## Need Help?

- 🐛 Report issues on [GitHub](https://github.com/aj-geddes/terry-form-mcp/issues)
- 💬 Join [GitHub Discussions](https://github.com/aj-geddes/terry-form-mcp/discussions)

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