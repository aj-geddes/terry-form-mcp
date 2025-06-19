import express from "express";
import { getModeConfig } from "../modes/index.js";
import { VERSION, SERVER_NAME, TFC_TOKEN } from "../../config.js";
import { githubAppRouter } from "../github-app/routes.js";
import { getActiveGitHubAppConfig } from "../github-app/storage.js";
import logger from "../utils/logger.js";

export function createWebUI(port: number = 3000): void {
  const app = express();
  
  // Middleware
  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));
  
  // GitHub App routes
  app.use("/github-app", githubAppRouter);
  
  // Health check endpoint
  app.get("/health", (req, res) => {
    res.json({ status: "ok", version: VERSION });
  });
  
  // Mode status endpoint
  app.get("/api/status", (req, res) => {
    const modeConfig = getModeConfig();
    const githubAppConfig = getActiveGitHubAppConfig();
    res.json({
      server: SERVER_NAME,
      version: VERSION,
      mode: modeConfig.mode,
      displayName: modeConfig.displayName,
      description: modeConfig.description,
      features: modeConfig.features,
      terraformCloudEnabled: modeConfig.features.terraformCloud && !!TFC_TOKEN,
      githubAppConfigured: !!githubAppConfig
    });
  });
  
  // Main UI page
  app.get("/", (req, res) => {
    const modeConfig = getModeConfig();
    const githubAppConfig = getActiveGitHubAppConfig();
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terry - ${modeConfig.displayName}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
            color: #333;
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
        .mode-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            margin-left: 1rem;
        }
        .mode-local {
            background: #e7f3ff;
            color: #0066cc;
        }
        .mode-enterprise {
            background: #e6f4ea;
            color: #137333;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        .feature-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .feature-status {
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }
        .enabled {
            color: #137333;
        }
        .disabled {
            color: #999;
        }
        .info {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 4px;
            margin-top: 1rem;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Terry MCP Server 
                <span class="mode-badge mode-${modeConfig.mode}">${modeConfig.displayName}</span>
            </h1>
            <p>${modeConfig.description}</p>
            <div class="info">
                <strong>Version:</strong> ${VERSION}<br>
                <strong>Server Name:</strong> ${SERVER_NAME}
            </div>
        </div>
        
        <h2>Features</h2>
        <div class="feature-grid">
            <div class="feature-card">
                <h3>Terraform Registry</h3>
                <div class="feature-status enabled">✓ Always Available</div>
                <p>Access public Terraform providers, modules, and policies</p>
            </div>
            
            <div class="feature-card">
                <h3>Terraform Cloud</h3>
                <div class="feature-status ${modeConfig.features.terraformCloud && TFC_TOKEN ? 'enabled' : 'disabled'}">
                    ${modeConfig.features.terraformCloud ? (TFC_TOKEN ? '✓ Enabled' : '⚠️ Token Required') : '✗ Not Available'}
                </div>
                <p>Manage workspaces, runs, and private modules</p>
            </div>
            
            <div class="feature-card">
                <h3>Web UI</h3>
                <div class="feature-status ${modeConfig.features.webUI ? 'enabled' : 'disabled'}">
                    ${modeConfig.features.webUI ? '✓ Enabled' : '✗ Disabled'}
                </div>
                <p>Status dashboard and monitoring</p>
            </div>
            
            <div class="feature-card">
                <h3>MCP Bridge</h3>
                <div class="feature-status ${modeConfig.features.mcpBridge ? 'enabled' : 'disabled'}">
                    ${modeConfig.features.mcpBridge ? '✓ Enabled' : '✗ Not Available'}
                </div>
                <p>Integration with LLM services</p>
            </div>
            
            <div class="feature-card">
                <h3>GitHub Integration</h3>
                <div class="feature-status ${githubAppConfig ? 'enabled' : 'disabled'}">
                    ${githubAppConfig ? '✓ Configured' : '✗ Not Configured'}
                </div>
                <p>Read Terraform configs from GitHub repos</p>
                ${!githubAppConfig ? '<a href="/github-app" style="color: #0066cc;">Configure GitHub App</a>' : '<a href="/github-app" style="color: #0066cc;">Manage</a>'}
            </div>
        </div>
        
        <script>
            // Auto-refresh status every 30 seconds
            setInterval(() => {
                fetch('/api/status')
                    .then(res => res.json())
                    .then(data => {
                        console.log('Status update:', data);
                    });
            }, 30000);
        </script>
    </div>
</body>
</html>
    `;
    res.send(html);
  });
  
  app.listen(port, () => {
    logger.info(`Web UI running at http://localhost:${port}`);
  });
}