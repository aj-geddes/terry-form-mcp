---
layout: page
title: Tutorials
description: Step-by-step tutorials for Terry-Form MCP
---

Learn Terry-Form MCP through hands-on tutorials.

{% assign sorted_tutorials = site.tutorials | sort: 'order' %}

### Beginner

<div class="features-grid">
{% for tutorial in sorted_tutorials %}
  {% unless tutorial.url contains '/index' %}
  {% if tutorial.difficulty == "beginner" %}
  <div class="feature-card">
    <h3><a href="{{ tutorial.url | relative_url }}">{{ tutorial.title }}</a></h3>
    <div class="tutorial-meta">
      <span class="difficulty-badge difficulty-{{ tutorial.difficulty }}">{{ tutorial.difficulty }}</span>
      {% if tutorial.duration %}
      <span class="duration"><i class="fas fa-clock"></i> {{ tutorial.duration }}</span>
      {% endif %}
    </div>
    <p>{{ tutorial.description }}</p>
  </div>
  {% endif %}
  {% endunless %}
{% endfor %}
</div>

### Intermediate

<div class="features-grid">
{% for tutorial in sorted_tutorials %}
  {% unless tutorial.url contains '/index' %}
  {% if tutorial.difficulty == "intermediate" %}
  <div class="feature-card">
    <h3><a href="{{ tutorial.url | relative_url }}">{{ tutorial.title }}</a></h3>
    <div class="tutorial-meta">
      <span class="difficulty-badge difficulty-{{ tutorial.difficulty }}">{{ tutorial.difficulty }}</span>
      {% if tutorial.duration %}
      <span class="duration"><i class="fas fa-clock"></i> {{ tutorial.duration }}</span>
      {% endif %}
    </div>
    <p>{{ tutorial.description }}</p>
  </div>
  {% endif %}
  {% endunless %}
{% endfor %}
</div>

### Advanced

<div class="features-grid">
{% for tutorial in sorted_tutorials %}
  {% unless tutorial.url contains '/index' %}
  {% if tutorial.difficulty == "advanced" %}
  <div class="feature-card">
    <h3><a href="{{ tutorial.url | relative_url }}">{{ tutorial.title }}</a></h3>
    <div class="tutorial-meta">
      <span class="difficulty-badge difficulty-{{ tutorial.difficulty }}">{{ tutorial.difficulty }}</span>
      {% if tutorial.duration %}
      <span class="duration"><i class="fas fa-clock"></i> {{ tutorial.duration }}</span>
      {% endif %}
    </div>
    <p>{{ tutorial.description }}</p>
  </div>
  {% endif %}
  {% endunless %}
{% endfor %}
</div>

## Interactive Example

Ask your AI assistant:

```
Can you validate the Terraform configuration in my workspace/example folder?
```

The assistant will use Terry-Form MCP to check your configuration and provide feedback.

## Need Help?

- Report issues on [GitHub]({{ site.data.project.repo_url }}/issues)
- Join [GitHub Discussions]({{ site.data.project.repo_url }}/discussions)
