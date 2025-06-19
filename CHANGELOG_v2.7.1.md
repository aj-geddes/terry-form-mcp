# Changelog

## v2.7.1 (2025-01-19)

### 🎉 New Features

#### GitHub App Integration
- **GitHub App Support**: Terry can now securely access Terraform configurations in GitHub repositories
- **Setup Wizard**: Web-based GitHub App configuration at `/github-app`
- **Repository Tools**: New tools for reading and searching Terraform files in GitHub:
  - `listGitHubRepos` - List all accessible repositories
  - `readGitHubFile` - Read files from GitHub repositories
  - `listGitHubFiles` - Browse repository contents
  - `searchGitHubRepo` - Search for content in repositories
- **Secure Authentication**: Uses GitHub App private keys instead of personal access tokens
- **Multiple Installations**: Support for accessing repos across different organizations

#### OpenWebUI Integration
- **Full mcpo Support**: Comprehensive integration guide for OpenWebUI administrators
- **Function Tools**: All Terry tools available as OpenWebUI functions
- **Multiple Deployment Options**: Docker, direct installation, and production configurations
- **Enterprise Ready**: Includes security best practices and high availability setup

### 🔧 Improvements
- Added `createSuccessResponse` utility function for consistent API responses
- Enhanced Web UI to display GitHub App configuration status
- Updated documentation structure with new integration guides

### 📚 Documentation
- New GitHub App Setup Guide (`docs/GITHUB_APP_SETUP.md`)
- New OpenWebUI Integration Guide (`docs/OPENWEBUI_INTEGRATION.md`)
- Updated main documentation with integration links
- Enhanced CLAUDE.md with OpenWebUI quick setup

### 🔒 Security
- GitHub App uses fine-grained permissions (read-only access)
- Support for both file-based and environment variable configuration
- Secure storage of private keys with proper file permissions

### 🏗️ Technical Details
- Added `@octokit/auth-app` and `@octokit/rest` dependencies
- New modules: `src/github-app/` and `src/tools/githubRepo.ts`
- Express routes for GitHub App configuration UI
- Full TypeScript support for all new features