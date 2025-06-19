/**
 * GitHub App Authentication
 * 
 * Handles authentication and token generation for GitHub App
 */

import { createAppAuth } from "@octokit/auth-app";
import { Octokit } from "@octokit/rest";
import type { GitHubAppConfig } from "./manifest.js";
import logger from "../utils/logger.js";

export class GitHubAppAuth {
  private appId: number;
  private privateKey: string;
  private installationId?: number;
  private auth: ReturnType<typeof createAppAuth>;

  constructor(config: GitHubAppConfig) {
    this.appId = config.appId;
    this.privateKey = config.privateKey;
    this.installationId = config.installationId;

    this.auth = createAppAuth({
      appId: this.appId,
      privateKey: this.privateKey,
      installationId: this.installationId
    });
  }

  async getInstallationOctokit(installationId?: number): Promise<Octokit> {
    const targetInstallationId = installationId || this.installationId;
    
    if (!targetInstallationId) {
      throw new Error("Installation ID is required");
    }

    try {
      const auth = await this.auth({
        type: "installation",
        installationId: targetInstallationId
      });

      return new Octokit({
        auth: auth.token
      });
    } catch (error) {
      logger.error("Failed to authenticate GitHub App:", error);
      throw new Error("GitHub App authentication failed");
    }
  }

  async getAppOctokit(): Promise<Octokit> {
    try {
      const auth = await this.auth({ type: "app" });
      return new Octokit({
        auth: auth.token
      });
    } catch (error) {
      logger.error("Failed to authenticate as GitHub App:", error);
      throw new Error("GitHub App authentication failed");
    }
  }

  async listInstallations(): Promise<any[]> {
    const octokit = await this.getAppOctokit();
    const { data } = await octokit.apps.listInstallations();
    return data;
  }

  async getInstallationRepos(installationId: number): Promise<any[]> {
    const octokit = await this.getInstallationOctokit(installationId);
    const { data } = await octokit.apps.listReposAccessibleToInstallation();
    return data.repositories;
  }
}

export async function validateGitHubAppCredentials(config: GitHubAppConfig): Promise<boolean> {
  try {
    const auth = new GitHubAppAuth(config);
    await auth.getAppOctokit();
    return true;
  } catch (error) {
    logger.error("GitHub App validation failed:", error);
    return false;
  }
}