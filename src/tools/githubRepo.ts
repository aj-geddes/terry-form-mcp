/**
 * GitHub Repository Tools
 * 
 * Tools for reading Terraform configurations from GitHub repositories
 */

import { z } from "zod";
import { GitHubAppAuth } from "../github-app/auth.js";
import { getActiveGitHubAppConfig } from "../github-app/storage.js";
import { createSuccessResponse, handleToolError } from "../utils/responseUtils.js";
import logger from "../utils/logger.js";

// Input schemas
export const ReadFileParams = z.object({
  owner: z.string().describe("Repository owner (user or organization)"),
  repo: z.string().describe("Repository name"),
  path: z.string().describe("File path in the repository"),
  ref: z.string().optional().describe("Git ref (branch, tag, or commit SHA)")
});

export const ListFilesParams = z.object({
  owner: z.string().describe("Repository owner (user or organization)"),
  repo: z.string().describe("Repository name"),
  path: z.string().optional().describe("Directory path in the repository"),
  ref: z.string().optional().describe("Git ref (branch, tag, or commit SHA)"),
  pattern: z.string().optional().describe("File pattern to filter (e.g., '*.tf')")
});

export const SearchRepoParams = z.object({
  owner: z.string().describe("Repository owner (user or organization)"),
  repo: z.string().describe("Repository name"),
  query: z.string().describe("Search query"),
  path: z.string().optional().describe("Limit search to this path"),
  extension: z.string().optional().describe("File extension filter (e.g., 'tf')")
});

async function getGitHubClient(installationId?: number) {
  const config = getActiveGitHubAppConfig();
  if (!config) {
    throw new Error("GitHub App not configured. Please set up GitHub App first.");
  }
  
  const auth = new GitHubAppAuth(config);
  return auth.getInstallationOctokit(installationId);
}

export async function handleReadGitHubFile(params: z.infer<typeof ReadFileParams>) {
  try {
    const { owner, repo, path, ref } = params;
    logger.info(`Reading file from GitHub: ${owner}/${repo}/${path}`);
    
    const octokit = await getGitHubClient();
    
    const response = await octokit.repos.getContent({
      owner,
      repo,
      path,
      ref
    });
    
    if (Array.isArray(response.data)) {
      return createSuccessResponse({
        error: "Path is a directory, not a file"
      });
    }
    
    if (response.data.type !== "file") {
      return createSuccessResponse({
        error: `Path is a ${response.data.type}, not a file`
      });
    }
    
    // Decode base64 content
    const content = Buffer.from(response.data.content, "base64").toString("utf-8");
    
    return createSuccessResponse({
      file: {
        path: response.data.path,
        name: response.data.name,
        size: response.data.size,
        sha: response.data.sha,
        content: content,
        url: response.data.html_url
      }
    });
  } catch (error: any) {
    if (error.status === 404) {
      return createSuccessResponse({
        error: "File not found"
      });
    }
    return handleToolError("readGitHubFile", error);
  }
}

export async function handleListGitHubFiles(params: z.infer<typeof ListFilesParams>) {
  try {
    const { owner, repo, path = "", ref, pattern } = params;
    logger.info(`Listing files in GitHub: ${owner}/${repo}/${path}`);
    
    const octokit = await getGitHubClient();
    
    const response = await octokit.repos.getContent({
      owner,
      repo,
      path,
      ref
    });
    
    if (!Array.isArray(response.data)) {
      return createSuccessResponse({
        error: "Path is a file, not a directory"
      });
    }
    
    let files = response.data.filter(item => item.type === "file");
    
    // Apply pattern filter if provided
    if (pattern) {
      const regex = new RegExp(pattern.replace(/\*/g, ".*"));
      files = files.filter(file => regex.test(file.name));
    }
    
    return createSuccessResponse({
      files: files.map(file => ({
        name: file.name,
        path: file.path,
        size: file.size,
        sha: file.sha,
        url: file.html_url
      })),
      directories: response.data
        .filter(item => item.type === "dir")
        .map(dir => ({
          name: dir.name,
          path: dir.path
        }))
    });
  } catch (error: any) {
    if (error.status === 404) {
      return createSuccessResponse({
        error: "Directory not found"
      });
    }
    return handleToolError("listGitHubFiles", error);
  }
}

export async function handleSearchGitHubRepo(params: z.infer<typeof SearchRepoParams>) {
  try {
    const { owner, repo, query, path, extension } = params;
    logger.info(`Searching in GitHub repo: ${owner}/${repo} for "${query}"`);
    
    const octokit = await getGitHubClient();
    
    // Build search query
    let searchQuery = `${query} repo:${owner}/${repo}`;
    if (path) {
      searchQuery += ` path:${path}`;
    }
    if (extension) {
      searchQuery += ` extension:${extension}`;
    }
    
    const response = await octokit.search.code({
      q: searchQuery,
      per_page: 20
    });
    
    return createSuccessResponse({
      total_count: response.data.total_count,
      matches: response.data.items.map(item => ({
        name: item.name,
        path: item.path,
        repository: item.repository.full_name,
        url: item.html_url,
        score: item.score
      }))
    });
  } catch (error) {
    return handleToolError("searchGitHubRepo", error);
  }
}

export async function handleListGitHubRepos() {
  try {
    logger.info("Listing accessible GitHub repositories");
    
    const config = getActiveGitHubAppConfig();
    if (!config) {
      return createSuccessResponse({
        error: "GitHub App not configured. Please set up GitHub App first."
      });
    }
    
    const auth = new GitHubAppAuth(config);
    const installations = await auth.listInstallations();
    
    const allRepos = [];
    for (const installation of installations) {
      try {
        const repos = await auth.getInstallationRepos(installation.id);
        allRepos.push({
          installation: {
            id: installation.id,
            account: installation.account.login,
            type: installation.account.type
          },
          repositories: repos.map(repo => ({
            name: repo.name,
            full_name: repo.full_name,
            private: repo.private,
            default_branch: repo.default_branch,
            url: repo.html_url,
            has_terraform: repo.topics?.includes("terraform") || false
          }))
        });
      } catch (error) {
        logger.error(`Failed to list repos for installation ${installation.id}:`, error);
      }
    }
    
    return createSuccessResponse({
      installations: allRepos
    });
  } catch (error) {
    return handleToolError("listGitHubRepos", error);
  }
}