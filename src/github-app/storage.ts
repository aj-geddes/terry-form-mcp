/**
 * GitHub App Configuration Storage
 * 
 * Handles storing and retrieving GitHub App configuration
 */

import * as fs from "fs";
import * as path from "path";
import { homedir } from "os";
import type { GitHubAppConfig } from "./manifest.js";
import logger from "../utils/logger.js";

const CONFIG_DIR = path.join(homedir(), ".terry-mcp");
const GITHUB_APP_CONFIG_FILE = path.join(CONFIG_DIR, "github-app.json");

function ensureConfigDir(): void {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true, mode: 0o700 });
  }
}

export function saveGitHubAppConfig(config: GitHubAppConfig): void {
  try {
    ensureConfigDir();
    
    // Encrypt sensitive data in production
    const configToSave = {
      ...config,
      privateKey: config.privateKey, // In production, encrypt this
      savedAt: new Date().toISOString()
    };
    
    fs.writeFileSync(
      GITHUB_APP_CONFIG_FILE, 
      JSON.stringify(configToSave, null, 2),
      { mode: 0o600 } // Read/write for owner only
    );
    
    logger.info("GitHub App configuration saved");
  } catch (error) {
    logger.error("Failed to save GitHub App configuration:", error);
    throw new Error("Failed to save GitHub App configuration");
  }
}

export function getGitHubAppConfig(): GitHubAppConfig | null {
  try {
    if (!fs.existsSync(GITHUB_APP_CONFIG_FILE)) {
      return null;
    }
    
    const configData = fs.readFileSync(GITHUB_APP_CONFIG_FILE, "utf-8");
    const config = JSON.parse(configData);
    
    // Basic validation
    if (!config.appId || !config.privateKey) {
      logger.warn("Invalid GitHub App configuration found");
      return null;
    }
    
    return {
      appId: config.appId,
      privateKey: config.privateKey,
      installationId: config.installationId,
      clientId: config.clientId,
      clientSecret: config.clientSecret
    };
  } catch (error) {
    logger.error("Failed to load GitHub App configuration:", error);
    return null;
  }
}

export function deleteGitHubAppConfig(): void {
  try {
    if (fs.existsSync(GITHUB_APP_CONFIG_FILE)) {
      fs.unlinkSync(GITHUB_APP_CONFIG_FILE);
      logger.info("GitHub App configuration deleted");
    }
  } catch (error) {
    logger.error("Failed to delete GitHub App configuration:", error);
    throw new Error("Failed to delete GitHub App configuration");
  }
}

// Environment variable support for enterprise deployments
export function getGitHubAppConfigFromEnv(): GitHubAppConfig | null {
  const appId = process.env.GITHUB_APP_ID;
  const privateKey = process.env.GITHUB_APP_PRIVATE_KEY;
  const installationId = process.env.GITHUB_APP_INSTALLATION_ID;
  
  if (!appId || !privateKey) {
    return null;
  }
  
  return {
    appId: parseInt(appId),
    privateKey: privateKey.replace(/\\n/g, '\n'), // Handle escaped newlines
    installationId: installationId ? parseInt(installationId) : undefined,
    clientId: process.env.GITHUB_APP_CLIENT_ID,
    clientSecret: process.env.GITHUB_APP_CLIENT_SECRET
  };
}

// Get config from env first, then from file
export function getActiveGitHubAppConfig(): GitHubAppConfig | null {
  const envConfig = getGitHubAppConfigFromEnv();
  if (envConfig) {
    logger.debug("Using GitHub App config from environment variables");
    return envConfig;
  }
  
  const fileConfig = getGitHubAppConfig();
  if (fileConfig) {
    logger.debug("Using GitHub App config from file");
    return fileConfig;
  }
  
  return null;
}