/**
 * GitHub App Manifest Generator for Terry
 * 
 * This generates a GitHub App manifest that users can use to create
 * their own GitHub App instance for Terry.
 */

import { SERVER_NAME, VERSION } from "../../config.js";

export interface GitHubAppManifest {
  name: string;
  url: string;
  hook_attributes: {
    url: string;
    active: boolean;
  };
  redirect_url: string;
  callback_urls: string[];
  setup_url: string;
  description: string;
  public: boolean;
  default_events: string[];
  default_permissions: {
    contents: string;
    metadata: string;
    pull_requests: string;
    issues: string;
  };
}

export function generateGitHubAppManifest(baseUrl: string = "http://localhost:3000"): GitHubAppManifest {
  return {
    name: `Terry MCP - ${new Date().getTime()}`,
    url: `${baseUrl}/github-app`,
    hook_attributes: {
      url: `${baseUrl}/github-app/webhook`,
      active: false // We don't need webhooks for reading repos
    },
    redirect_url: `${baseUrl}/github-app/callback`,
    callback_urls: [
      `${baseUrl}/github-app/callback`
    ],
    setup_url: `${baseUrl}/github-app/setup`,
    description: "Terry (Terraform MCP Server) - Secure access to Terraform configurations in your repositories",
    public: false,
    default_events: [],
    default_permissions: {
      contents: "read",      // Read repository contents
      metadata: "read",      // Read repository metadata
      pull_requests: "read", // Read PR information
      issues: "read"         // Read issues (for terraform plans in issues)
    }
  };
}

export function getManifestUrl(manifest: GitHubAppManifest): string {
  const manifestString = JSON.stringify(manifest);
  const encodedManifest = encodeURIComponent(manifestString);
  return `https://github.com/settings/apps/new?manifest=${encodedManifest}`;
}

export interface GitHubAppConfig {
  appId: number;
  privateKey: string;
  installationId?: number;
  clientId?: string;
  clientSecret?: string;
}

export function validateGitHubAppConfig(config: Partial<GitHubAppConfig>): config is GitHubAppConfig {
  return !!(config.appId && config.privateKey);
}