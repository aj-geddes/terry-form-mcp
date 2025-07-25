# GitHub Actions Workflows

This directory contains GitHub Actions workflow files that should be copied to `.github/workflows/` in your repository.

## Available Workflows

### jekyll-gh-pages.yml

Builds and deploys the Jekyll documentation site to GitHub Pages.

**To use this workflow:**

1. Copy the file to `.github/workflows/jekyll-gh-pages.yml`
2. Enable GitHub Pages in your repository settings:
   - Go to Settings → Pages
   - Source: Deploy from a branch
   - Branch: gh-pages (will be created by the workflow)
3. The workflow will run automatically when you push changes to the `docs/` directory

**Features:**
- Automatic deployment on push to main branch
- Build preview for pull requests
- Ruby and Jekyll dependency caching
- Proper base URL configuration for GitHub Pages

**Required Repository Settings:**
- GitHub Pages must be enabled
- Workflow permissions need to include:
  - `contents: read`
  - `pages: write`
  - `id-token: write`

## Why This Directory?

GitHub Actions workflows must be in the `.github/workflows/` directory to be recognized by GitHub. However, since the instructions mentioned that workflows cannot be created properly in that location, these files are provided here for manual copying.

## Setup Instructions

```bash
# Create the workflows directory
mkdir -p .github/workflows

# Copy the workflow file
cp actions/jekyll-gh-pages.yml .github/workflows/

# Commit and push
git add .github/workflows/jekyll-gh-pages.yml
git commit -m "Add Jekyll GitHub Pages workflow"
git push origin main
```

The documentation site will be available at:
`https://[username].github.io/terry-form-mcp/`

Replace `[username]` with your GitHub username or organization name.