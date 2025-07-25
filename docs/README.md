# Terry-Form MCP Documentation

This directory contains the Jekyll-based documentation site for Terry-Form MCP.

## 📚 Documentation Structure

```
docs/
├── _config.yml          # Jekyll configuration
├── Gemfile             # Ruby dependencies
├── index.md            # Home page
├── getting-started.md  # Quick start guide
├── guides.md          # Guides index
├── api.md             # API reference index
├── architecture.md    # Architecture index
├── tutorials.md       # Tutorials index
├── 404.md            # Custom 404 page
│
├── _guides/           # Guide documents
│   └── security.md    # Security guide
│
├── _api/             # API reference documents
│   └── mcp-tools.md  # MCP tools reference
│
├── _architecture/    # Architecture documents
│   └── overview.md   # Architecture overview
│
├── _tutorials/       # Tutorial documents
│   └── aws-infrastructure.md  # AWS tutorial
│
├── _layouts/         # Page layouts
│   ├── default.html  # Base layout
│   └── home.html     # Homepage layout
│
└── assets/           # Static assets
    ├── css/
    │   └── style.scss  # Main stylesheet
    ├── js/
    │   └── main.js     # JavaScript functionality
    └── images/         # Images and diagrams
```

## 🚀 Local Development

### Prerequisites

- Ruby 2.7+ and Bundler
- Node.js (for some Jekyll plugins)

### Setup

```bash
cd docs
bundle install
```

### Running Locally

```bash
# Serve with live reload
bundle exec jekyll serve

# Serve with production settings
JEKYLL_ENV=production bundle exec jekyll serve

# Build only
bundle exec jekyll build
```

The site will be available at `http://localhost:4000/terry-form-mcp/`

## 📝 Writing Documentation

### Creating a New Guide

1. Create a file in `_guides/` directory:
   ```markdown
   ---
   title: Your Guide Title
   description: Brief description
   order: 2
   ---
   
   # Your Guide Title
   
   Your content here...
   ```

2. The guide will automatically appear in the guides index

### Creating a Tutorial

1. Create a file in `_tutorials/` directory:
   ```markdown
   ---
   title: Tutorial Title
   description: What users will learn
   duration: 30 minutes
   difficulty: intermediate
   order: 1
   ---
   
   # Tutorial Title
   
   Tutorial content...
   ```

### Adding API Documentation

1. Create a file in `_api/` directory:
   ```markdown
   ---
   title: API Section
   description: API description
   order: 2
   ---
   
   # API Documentation
   
   API details...
   ```

## 🎨 Styling

The site uses:
- **Inter** font family
- Responsive design with mobile support
- Dark mode support (automatic)
- Syntax highlighting with Prism.js
- Mermaid for diagrams

### Color Scheme

- Primary: `#2196F3` (Blue)
- Secondary: `#4CAF50` (Green)
- Danger: `#f44336` (Red)
- Warning: `#ff9800` (Orange)

## 📊 Features

### Implemented Features

- ✅ Responsive navigation
- ✅ Mobile menu
- ✅ Code syntax highlighting
- ✅ Copy code buttons
- ✅ Mermaid diagram support
- ✅ Table of contents generation
- ✅ Search functionality (basic)
- ✅ Dark mode support
- ✅ SEO optimization
- ✅ RSS feed
- ✅ Sitemap generation

### Collections

The site uses Jekyll collections for organized content:

- `guides` - How-to guides and documentation
- `api` - API reference documentation
- `architecture` - Technical architecture docs
- `tutorials` - Step-by-step tutorials

## 🚢 Deployment

### GitHub Pages

1. Copy the workflow file:
   ```bash
   cp ../actions/jekyll-gh-pages.yml ../.github/workflows/
   ```

2. Enable GitHub Pages in repository settings

3. Push to main branch

The site will be deployed to: `https://[username].github.io/terry-form-mcp/`

### Custom Domain

To use a custom domain:

1. Create `CNAME` file in docs directory:
   ```
   docs.terry-form.io
   ```

2. Configure DNS records

3. Update `_config.yml`:
   ```yaml
   url: "https://docs.terry-form.io"
   baseurl: ""
   ```

## 🔧 Configuration

Key configuration in `_config.yml`:

```yaml
title: Terry-Form MCP
description: Enterprise-grade Terraform automation
url: "https://aj-geddes.github.io"
baseurl: "/terry-form-mcp"
```

### Environment Variables

- `JEKYLL_ENV=production` - Enable production optimizations
- `PAGES_REPO_NWO` - Set by GitHub Pages

## 📦 Dependencies

Main dependencies (see Gemfile for full list):
- Jekyll 4.3+
- GitHub Pages gem
- Jekyll plugins:
  - jekyll-feed
  - jekyll-sitemap
  - jekyll-seo-tag
  - jekyll-mermaid

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

### Documentation Style Guide

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Test all links
- Ensure mobile compatibility

## 📄 License

The documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## 🆘 Help

- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Report Documentation Issues](https://github.com/aj-geddes/terry-form-mcp/issues)