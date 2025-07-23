# GitHub Integration Workflows for Terry-Form MCP

This document provides example workflows for using Terry-Form MCP with GitHub repositories.

## Basic Workflow: Clone and Validate

```javascript
// 1. Clone a repository containing Terraform configurations
github_clone_repo(
  owner="terraform-modules",
  repo="aws-infrastructure",
  branch="main"
)

// 2. List available Terraform configurations
github_list_terraform_files(
  owner="terraform-modules",
  repo="aws-infrastructure"
)

// 3. Validate a specific configuration
terry(
  path="terraform-modules/aws-infrastructure/environments/dev",
  actions=["init", "validate"]
)
```

## Advanced Workflow: Multi-Environment Deployment Planning

```javascript
// 1. Check available installations and repositories
github_list_installations()

// 2. Get repository information
github_repo_info(
  owner="mycompany",
  repo="infrastructure"
)

// 3. Prepare workspaces for different environments
// Development
github_prepare_workspace(
  owner="mycompany",
  repo="infrastructure",
  config_path="environments/dev",
  workspace_name="dev-deployment"
)

// Staging
github_prepare_workspace(
  owner="mycompany",
  repo="infrastructure",
  config_path="environments/staging",
  workspace_name="staging-deployment"
)

// 4. Run Terraform plan for each environment
// Development
terry(
  path="terraform-workspaces/dev-deployment",
  actions=["init", "plan"],
  vars={
    "environment": "dev",
    "region": "us-east-1"
  }
)

// Staging
terry(
  path="terraform-workspaces/staging-deployment",
  actions=["init", "plan"],
  vars={
    "environment": "staging",
    "region": "us-west-2"
  }
)
```

## Module Development Workflow

```javascript
// 1. Clone module repository
github_clone_repo(
  owner="terraform-modules",
  repo="vpc-module",
  branch="feature/new-subnet-logic"
)

// 2. Get module structure information
github_get_terraform_config(
  owner="terraform-modules",
  repo="vpc-module",
  config_path="."
)

// 3. Initialize LSP for intelligent development
terry_lsp_init(
  workspace_path="github-repos/terraform-modules_vpc-module"
)

// 4. Validate module syntax with LSP
terraform_validate_lsp(
  file_path="github-repos/terraform-modules_vpc-module/main.tf"
)

// 5. Format the module code
terraform_format_lsp(
  file_path="github-repos/terraform-modules_vpc-module/variables.tf"
)

// 6. Run comprehensive validation
terry(
  path="github-repos/terraform-modules_vpc-module",
  actions=["init", "validate", "fmt"]
)
```

## Compliance and Security Workflow

```javascript
// 1. Clone security policies repository
github_clone_repo(
  owner="security-team",
  repo="terraform-policies"
)

// 2. Clone infrastructure repository
github_clone_repo(
  owner="mycompany",
  repo="production-infrastructure"
)

// 3. List all Terraform files for audit
github_list_terraform_files(
  owner="mycompany",
  repo="production-infrastructure",
  pattern="*.tf"
)

// 4. Validate each configuration
terry(
  path="mycompany/production-infrastructure/services/api",
  actions=["init", "validate"]
)

// 5. Generate plan for security review
terry(
  path="mycompany/production-infrastructure/services/api",
  actions=["plan"],
  vars={
    "environment": "prod",
    "enable_encryption": "true",
    "enable_logging": "true"
  }
)
```

## Disaster Recovery Workflow

```javascript
// 1. Check repository status
github_repo_info(
  owner="mycompany",
  repo="dr-infrastructure"
)

// 2. Clone DR configuration
github_clone_repo(
  owner="mycompany",
  repo="dr-infrastructure",
  branch="main",
  force=true  // Force fresh clone
)

// 3. Prepare DR workspace
github_prepare_workspace(
  owner="mycompany",
  repo="dr-infrastructure",
  config_path="regions/us-west-2",
  workspace_name="dr-failover"
)

// 4. Initialize and plan DR infrastructure
terry(
  path="terraform-workspaces/dr-failover",
  actions=["init", "plan"],
  vars={
    "dr_mode": "active",
    "source_region": "us-east-1",
    "target_region": "us-west-2"
  }
)
```

## Workspace Management Workflow

```javascript
// 1. Check current workspace status
terry_workspace_info()

// 2. List all GitHub repositories in workspace
terry_workspace_info("github-repos")

// 3. Clean up old repositories (older than 3 days)
github_cleanup_repos(days=3)

// 4. Check environment status
terry_environment_check()
```

## Troubleshooting Workflow

```javascript
// 1. Check GitHub App configuration
terry_environment_check()

// 2. Test GitHub connectivity
github_list_installations()

// 3. If issues, check specific repository access
github_repo_info(
  owner="mycompany",
  repo="infrastructure"
)

// 4. Force re-clone if needed
github_clone_repo(
  owner="mycompany",
  repo="infrastructure",
  branch="main",
  force=true
)

// 5. Check LSP status for intelligent features
terraform_lsp_status()
```

## Best Practices

1. **Always validate before planning**: Run `validate` action before `plan`
2. **Use workspaces for isolation**: Prepare separate workspaces for different environments
3. **Clean up regularly**: Use `github_cleanup_repos()` to manage disk space
4. **Check access first**: Use `github_list_installations()` to verify repository access
5. **Use branches wisely**: Specify branches explicitly for different environments
6. **Leverage LSP features**: Initialize LSP for better validation and development experience

## Common Patterns

### Pattern 1: Environment-Specific Branches
```javascript
// Development from develop branch
github_clone_repo(owner="myco", repo="infra", branch="develop")
terry(path="myco/infra/env/dev", actions=["plan"])

// Production from main branch
github_clone_repo(owner="myco", repo="infra", branch="main")
terry(path="myco/infra/env/prod", actions=["plan"])
```

### Pattern 2: Module Testing
```javascript
// Clone module
github_clone_repo(owner="modules", repo="network")

// Create test configuration
terry_workspace_setup(path="test-network", project_name="network-test")

// Copy module and create test
// ... (additional setup steps)

// Test module
terry(path="test-network", actions=["init", "validate", "plan"])
```

### Pattern 3: Multi-Region Deployment
```javascript
const regions = ["us-east-1", "us-west-2", "eu-west-1"];

for (const region of regions) {
  // Prepare workspace for each region
  github_prepare_workspace(
    owner="myco",
    repo="global-infra",
    config_path=`regions/${region}`,
    workspace_name=`deploy-${region}`
  );
  
  // Plan for each region
  terry(
    path=`terraform-workspaces/deploy-${region}`,
    actions=["init", "plan"],
    vars={ "region": region }
  );
}
```