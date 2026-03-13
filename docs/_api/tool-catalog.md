---
layout: api
title: Tool Catalog
description: Complete catalog of all MCP tools with schemas and parameters
order: 2
toc: true
---

# Tool Catalog

Browse all {{ site.data.tools.tool_count }} tools available in {{ site.title }} v{{ site.data.project.version }}.

Download the machine-readable schema: [`tools.json`]({{ site.data.project.repo_url }}/blob/main/tools.json)

---

## Categories

{% for cat in site.data.tools.categories %}
- **{{ cat[0] }}** (`{{ cat[1].prefix }}`) — {{ cat[1].count }} tools
{% endfor %}

---

{% assign sorted_categories = "Core Terraform,LSP Intelligence,Diagnostics,Security & Recommendations,GitHub Integration,Terraform Cloud" | split: "," %}

{% for cat_name in sorted_categories %}
## {{ cat_name }}

{% for tool in site.data.tools.tools %}
{% if tool.category == cat_name %}

### `{{ tool.name }}`

{{ tool.summary }}

{% if tool.parameters.size > 0 %}
| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
{% for param in tool.parameters %}| `{{ param.name }}` | `{{ param.type }}` | {% if param.required %}yes{% else %}no{% endif %} | {% if param.default != null %}`{{ param.default }}`{% else %}—{% endif %} |
{% endfor %}
{% else %}
*No parameters required.*
{% endif %}

{% if tool.returns != "" %}
**Returns:** {{ tool.returns }}
{% endif %}

<details>
<summary>Input Schema</summary>

```json
{{ tool.inputSchema | jsonify }}
```

</details>

---

{% endif %}
{% endfor %}
{% endfor %}

## Machine-Readable Format

The complete tool catalog is available as [`tools.json`]({{ site.data.project.repo_url }}/blob/main/tools.json) in the MCP native schema format. This file is auto-generated from the server's tool registrations.

```bash
# Regenerate tools.json from the server
python3 scripts/export_tools_json.py
```

Structure:

```json
{
  "server": { "name": "terry-form", "version": "3.1.0" },
  "tool_count": 25,
  "tools": [
    {
      "name": "tool_name",
      "summary": "One-line description",
      "category": "Category Name",
      "parameters": [
        { "name": "param", "type": "string", "required": true }
      ],
      "inputSchema": { ... }
    }
  ],
  "categories": { ... }
}
```
