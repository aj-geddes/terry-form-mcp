/**
 * GitHub App Setup Routes
 * 
 * Express routes for GitHub App setup and configuration
 */

import express, { Router, Request, Response } from "express";
import { generateGitHubAppManifest, getManifestUrl } from "./manifest.js";
import { GitHubAppAuth, validateGitHubAppCredentials } from "./auth.js";
import { getGitHubAppConfig, saveGitHubAppConfig } from "./storage.js";
import logger from "../utils/logger.js";

export const githubAppRouter = Router();

// GitHub App info page
githubAppRouter.get("/", (req: Request, res: Response) => {
  const config = getGitHubAppConfig();
  const isConfigured = !!config;
  
  res.send(`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terry - GitHub App Setup</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        .header {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .status {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            margin-left: 1rem;
        }
        .configured {
            background: #e6f4ea;
            color: #137333;
        }
        .not-configured {
            background: #fce8e6;
            color: #c5221f;
        }
        .setup-section {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .button {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #0066cc;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin-top: 1rem;
        }
        .button:hover {
            background: #0052a3;
        }
        code {
            background: #f3f4f6;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: monospace;
        }
        pre {
            background: #f3f4f6;
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
        }
        .warning {
            background: #fef3c7;
            border: 1px solid #f59e0b;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GitHub App Setup
                <span class="status ${isConfigured ? 'configured' : 'not-configured'}">
                    ${isConfigured ? '✓ Configured' : '✗ Not Configured'}
                </span>
            </h1>
            <p>Configure GitHub App to allow Terry to securely access your Terraform repositories.</p>
        </div>
        
        ${!isConfigured ? `
        <div class="setup-section">
            <h2>Setup Instructions</h2>
            <ol>
                <li>
                    <strong>Create your GitHub App</strong>
                    <p>Click the button below to create a GitHub App with the correct permissions:</p>
                    <a href="/github-app/create" class="button">Create GitHub App</a>
                </li>
                <li>
                    <strong>Install the App</strong>
                    <p>After creating the app, you'll be redirected to install it on your repositories.</p>
                </li>
                <li>
                    <strong>Configure Terry</strong>
                    <p>Save the App ID and private key in Terry's configuration.</p>
                </li>
            </ol>
            
            <div class="warning">
                <strong>⚠️ Important:</strong> Keep your private key secure. It provides access to your repositories.
            </div>
        </div>
        ` : `
        <div class="setup-section">
            <h2>✓ GitHub App Configured</h2>
            <p>Your GitHub App is configured and ready to use.</p>
            <p><strong>App ID:</strong> <code>${config.appId}</code></p>
            
            <h3>Available Actions</h3>
            <ul>
                <li><a href="/github-app/installations">View Installations</a></li>
                <li><a href="/github-app/repos">View Accessible Repositories</a></li>
                <li><a href="/github-app/reconfigure">Reconfigure App</a></li>
            </ul>
        </div>
        `}
        
        <div class="setup-section">
            <h2>What is a GitHub App?</h2>
            <p>GitHub Apps are the recommended way to integrate with GitHub. They provide:</p>
            <ul>
                <li>🔒 <strong>Fine-grained permissions</strong> - Only access what's needed</li>
                <li>🏢 <strong>Organization-level installation</strong> - Manage access centrally</li>
                <li>🔑 <strong>No personal access tokens</strong> - More secure authentication</li>
                <li>📊 <strong>Better rate limits</strong> - Higher API limits than personal tokens</li>
            </ul>
        </div>
    </div>
</body>
</html>
  `);
});

// Create GitHub App redirect
githubAppRouter.get("/create", (req: Request, res: Response) => {
  const baseUrl = `${req.protocol}://${req.get("host")}`;
  const manifest = generateGitHubAppManifest(baseUrl);
  const manifestUrl = getManifestUrl(manifest);
  
  res.redirect(manifestUrl);
});

// GitHub App callback
githubAppRouter.get("/callback", async (req: Request, res: Response) => {
  const { code } = req.query;
  
  if (!code) {
    return res.status(400).send("Missing code parameter");
  }
  
  // Exchange code for app credentials
  // This would typically involve calling GitHub's API to complete the app creation
  res.send(`
<!DOCTYPE html>
<html>
<head>
    <title>GitHub App Created</title>
    <style>
        body { font-family: sans-serif; padding: 2rem; }
        .success { color: green; }
        .next-steps { background: #f0f0f0; padding: 1rem; border-radius: 4px; margin-top: 1rem; }
    </style>
</head>
<body>
    <h1 class="success">✓ GitHub App Created Successfully!</h1>
    <div class="next-steps">
        <h2>Next Steps:</h2>
        <ol>
            <li>Copy your App ID and Private Key from GitHub</li>
            <li>Configure Terry with these credentials</li>
            <li>Install the app on your repositories</li>
        </ol>
        <p><a href="/github-app/configure">Configure Terry with App Credentials</a></p>
    </div>
</body>
</html>
  `);
});

// Configuration page
githubAppRouter.get("/configure", (req: Request, res: Response) => {
  res.send(`
<!DOCTYPE html>
<html>
<head>
    <title>Configure GitHub App</title>
    <style>
        body { font-family: sans-serif; padding: 2rem; max-width: 600px; margin: 0 auto; }
        form { display: flex; flex-direction: column; gap: 1rem; }
        label { font-weight: bold; }
        input, textarea { padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; }
        textarea { min-height: 200px; font-family: monospace; }
        button { padding: 0.75rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0052a3; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>Configure GitHub App</h1>
    <form action="/github-app/configure" method="POST">
        <label for="appId">App ID:</label>
        <input type="number" id="appId" name="appId" required>
        
        <label for="privateKey">Private Key (PEM format):</label>
        <textarea id="privateKey" name="privateKey" placeholder="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----" required></textarea>
        
        <label for="installationId">Installation ID (optional):</label>
        <input type="number" id="installationId" name="installationId">
        
        <button type="submit">Save Configuration</button>
    </form>
</body>
</html>
  `);
});

// Save configuration
githubAppRouter.post("/configure", express.json(), async (req: Request, res: Response) => {
  const { appId, privateKey, installationId } = req.body;
  
  if (!appId || !privateKey) {
    return res.status(400).json({ error: "App ID and Private Key are required" });
  }
  
  const config = {
    appId: parseInt(appId),
    privateKey,
    installationId: installationId ? parseInt(installationId) : undefined
  };
  
  // Validate credentials
  const isValid = await validateGitHubAppCredentials(config);
  if (!isValid) {
    return res.status(400).json({ error: "Invalid GitHub App credentials" });
  }
  
  // Save configuration
  saveGitHubAppConfig(config);
  
  res.json({ success: true, message: "GitHub App configured successfully" });
});

// List installations
githubAppRouter.get("/installations", async (req: Request, res: Response) => {
  const config = getGitHubAppConfig();
  if (!config) {
    return res.status(400).json({ error: "GitHub App not configured" });
  }
  
  try {
    const auth = new GitHubAppAuth(config);
    const installations = await auth.listInstallations();
    
    res.json({
      installations: installations.map(inst => ({
        id: inst.id,
        account: inst.account.login,
        type: inst.account.type,
        repository_selection: inst.repository_selection,
        created_at: inst.created_at
      }))
    });
  } catch (error) {
    logger.error("Failed to list installations:", error);
    res.status(500).json({ error: "Failed to list installations" });
  }
});

// List accessible repositories
githubAppRouter.get("/repos", async (req: Request, res: Response) => {
  const config = getGitHubAppConfig();
  if (!config) {
    return res.status(400).json({ error: "GitHub App not configured" });
  }
  
  const { installationId } = req.query;
  const targetInstallationId = installationId ? parseInt(installationId as string) : config.installationId;
  
  if (!targetInstallationId) {
    return res.status(400).json({ error: "Installation ID required" });
  }
  
  try {
    const auth = new GitHubAppAuth(config);
    const repos = await auth.getInstallationRepos(targetInstallationId);
    
    res.json({
      repositories: repos.map(repo => ({
        id: repo.id,
        name: repo.name,
        full_name: repo.full_name,
        private: repo.private,
        default_branch: repo.default_branch,
        url: repo.html_url
      }))
    });
  } catch (error) {
    logger.error("Failed to list repositories:", error);
    res.status(500).json({ error: "Failed to list repositories" });
  }
});