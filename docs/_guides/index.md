---
layout: page
title: Guides
description: Comprehensive guides for Terry-Form MCP
---

Explore our comprehensive guides to master Terry-Form MCP.

<div class="features-grid">
{% assign sorted_guides = site.guides | sort: 'order' %}
{% for guide in sorted_guides %}
  {% unless guide.url contains '/index' %}
  <div class="feature-card">
    <h3><a href="{{ guide.url | relative_url }}">{{ guide.title }}</a></h3>
    <p>{{ guide.description }}</p>
    <div style="margin-top: var(--space-4); font-size: 0.875rem; color: var(--color-text-muted);">
      {% assign words = guide.content | number_of_words %}
      {{ words | divided_by: 200 | plus: 1 }} min read
    </div>
  </div>
  {% endunless %}
{% endfor %}
</div>
