// Configuration constants for the Terraform MCP Server

// Static version - updated during release process
export const VERSION = "2.7.1";
export const SERVER_NAME = "terraform-registry-mcp";

// Server mode configuration
export const SERVER_MODE = process.env.MODE || "local";
export const MODES = {
  LOCAL: "local",
  ENTERPRISE: "enterprise"
} as const;
export type ServerMode = typeof MODES[keyof typeof MODES];

// Terraform Registry API URLs
export const REGISTRY_API_BASE = process.env.TERRAFORM_REGISTRY_URL || "https://registry.terraform.io";
export const REGISTRY_API_V1 = `${REGISTRY_API_BASE}/v1`;
export const REGISTRY_API_V2 = `${REGISTRY_API_BASE}/v2`;

// Terraform Cloud API configuration
export const TF_CLOUD_API_BASE = "https://app.terraform.io/api/v2";
export const TFC_TOKEN = process.env.TFC_TOKEN;

// Default namespace for providers when not specified
export const DEFAULT_NAMESPACE = process.env.DEFAULT_PROVIDER_NAMESPACE || "hashicorp";

// Logging configuration
export const LOG_LEVEL = process.env.LOG_LEVEL || "info"; // Default log level
export const LOG_LEVELS = {
  ERROR: "error",
  WARN: "warn",
  INFO: "info",
  DEBUG: "debug"
};

// Default compatibility info
export const DEFAULT_TERRAFORM_COMPATIBILITY =
  process.env.DEFAULT_TERRAFORM_COMPATIBILITY || "Terraform 0.12 and later";

// Response statuses
export const RESPONSE_STATUS = {
  SUCCESS: "success",
  ERROR: "error"
};

// Rate limiting configuration
export const RATE_LIMIT_ENABLED = process.env.RATE_LIMIT_ENABLED === "true";
export const RATE_LIMIT_REQUESTS = parseInt(process.env.RATE_LIMIT_REQUESTS || "60", 10);
export const RATE_LIMIT_WINDOW_MS = parseInt(process.env.RATE_LIMIT_WINDOW_MS || "60000", 10);

// Request timeouts in milliseconds
export const REQUEST_TIMEOUT_MS = parseInt(process.env.REQUEST_TIMEOUT_MS || "10000", 10);

// Web UI configuration
export const WEB_UI_PORT = parseInt(process.env.WEB_UI_PORT || "3000", 10);

// GitHub App configuration
export const GITHUB_APP_ID = process.env.GITHUB_APP_ID;
export const GITHUB_APP_PRIVATE_KEY = process.env.GITHUB_APP_PRIVATE_KEY;
export const GITHUB_APP_INSTALLATION_ID = process.env.GITHUB_APP_INSTALLATION_ID;
export const GITHUB_APP_CLIENT_ID = process.env.GITHUB_APP_CLIENT_ID;
export const GITHUB_APP_CLIENT_SECRET = process.env.GITHUB_APP_CLIENT_SECRET;

// Algolia search configuration for Terraform Registry
export const ALGOLIA_CONFIG = {
  APPLICATION_ID: process.env.ALGOLIA_APPLICATION_ID || "YY0FFNI7MF",
  API_KEY: process.env.ALGOLIA_API_KEY || "0f94cddf85f28139b5a64c065a261696",
  MODULES_INDEX: "tf-registry:prod:modules",
  PROVIDERS_INDEX: "tf-registry:prod:providers",
  POLICIES_INDEX: "tf-registry:prod:policy-libraries"
};
