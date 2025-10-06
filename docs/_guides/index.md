---
layout: page
title: Guides
description: Comprehensive guides for Terry-Form MCP
---

Explore our comprehensive guides to master Terry-Form MCP.

<div class="guide-grid">
{% for guide in site.guides %}
  {% unless guide.url contains '/index' %}
  <div class="guide-card">
    <h3><a href="{{ guide.url | relative_url }}">{{ guide.title }}</a></h3>
    <p>{{ guide.description }}</p>
    <div class="guide-meta">
      {% assign words = guide.content | number_of_words %}
      <span class="read-time">{{ words | divided_by: 200 }} min read</span>
    </div>
  </div>
  {% endunless %}
{% endfor %}
</div>

## Available Guides

Currently available:

### 🔒 [Security Guide]({{ site.baseurl }}/guides/security)
Learn about Terry-Form MCP's security features, best practices, and how to configure security settings for production environments.

---

## Coming Soon

Additional guides are planned for future releases. Check back soon or [contribute your own guide](https://github.com/aj-geddes/terry-form-mcp/issues/new)!

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