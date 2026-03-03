---
title: CI/CD Integration
description: Using Terry-Form MCP in GitHub Actions and other CI/CD pipelines
order: 8
---

# CI/CD Integration Guide

Terry-Form MCP can be used in CI/CD pipelines to validate and plan Terraform configurations automatically.

## GitHub Actions

### Basic Validation Workflow

```yaml
name: Terraform Validation

on:
  pull_request:
    paths:
      - 'terraform/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Terry-Form MCP
        run: docker build -t terry-form-mcp .

      - name: Validate Terraform
        run: |
          echo '{"tool": "terry", "arguments": {"path": ".", "actions": ["init", "validate"]}}' | \
          docker run -i --rm \
            -v ${{ github.workspace }}/terraform:/mnt/workspace \
            terry-form-mcp:latest \
            python3 terry-form-mcp.py
```

### Plan on Pull Request

```yaml
name: Terraform Plan

on:
  pull_request:
    paths:
      - 'terraform/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Terry-Form MCP
        run: docker build -t terry-form-mcp .

      - name: Run Terraform Plan
        id: plan
        run: |
          RESULT=$(echo '{"tool": "terry", "arguments": {"path": ".", "actions": ["init", "validate", "plan"]}}' | \
          docker run -i --rm \
            -v ${{ github.workspace }}/terraform:/mnt/workspace \
            -e AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }} \
            -e AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }} \
            -e AWS_DEFAULT_REGION=${{ secrets.AWS_DEFAULT_REGION }} \
            terry-form-mcp:latest \
            python3 terry-form-mcp.py)
          echo "result<<EOF" >> $GITHUB_OUTPUT
          echo "$RESULT" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Comment Plan on PR
        uses: actions/github-script@v7
        with:
          script: |
            const plan = `${{ steps.plan.outputs.result }}`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan\n\`\`\`json\n${plan}\n\`\`\``
            });
```

### Security Scan on Push

```yaml
name: Terraform Security

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Terry-Form MCP
        run: docker build -t terry-form-mcp .

      - name: Security Scan
        run: |
          echo '{"tool": "terry_security_scan", "arguments": {"path": ".", "severity": "medium"}}' | \
          docker run -i --rm \
            -v ${{ github.workspace }}/terraform:/mnt/workspace \
            terry-form-mcp:latest \
            python3 terry-form-mcp.py
```

## Docker-Based CI Execution

Terry-Form MCP can be used in any CI system that supports Docker.

### General Pattern

```bash
# 1. Build the image (or pull from registry)
docker build -t terry-form-mcp .

# 2. Run validation
echo '{"tool": "terry", "arguments": {"path": ".", "actions": ["init", "validate"]}}' | \
  docker run -i --rm \
    -v $(pwd)/terraform:/mnt/workspace \
    terry-form-mcp:latest \
    python3 terry-form-mcp.py

# 3. Run security scan
echo '{"tool": "terry_security_scan", "arguments": {"path": ".", "severity": "high"}}' | \
  docker run -i --rm \
    -v $(pwd)/terraform:/mnt/workspace \
    terry-form-mcp:latest \
    python3 terry-form-mcp.py
```

### GitLab CI

```yaml
terraform-validate:
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t terry-form-mcp .
    - echo '{"tool":"terry","arguments":{"path":".","actions":["init","validate"]}}' |
      docker run -i --rm -v $CI_PROJECT_DIR/terraform:/mnt/workspace terry-form-mcp:latest python3 terry-form-mcp.py
```

## Credential Management

### GitHub Actions Secrets

Store credentials as GitHub Actions secrets:

1. Go to Repository > Settings > Secrets and variables > Actions
2. Add secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.
3. Reference in workflows: `${{ secrets.AWS_ACCESS_KEY_ID }}`

### Best Practices

- **Use OIDC** where possible (e.g., AWS IAM roles for GitHub Actions)
- **Scope credentials** to the minimum required permissions
- **Rotate secrets** regularly
- **Never log secrets** — Terry-Form MCP's forced `TF_INPUT=false` helps prevent accidental exposure

<div class="alert alert-danger">
<strong>Important</strong><br>
Terry-Form MCP blocks <code>apply</code> and <code>destroy</code> operations. CI pipelines should use it for validation and planning only. Actual infrastructure changes should go through your standard deployment process.
</div>

## Parsing Results

Terry-Form MCP returns JSON results. Parse them in your CI pipeline:

```bash
# Check if validation succeeded
RESULT=$(echo '...' | docker run -i --rm ... python3 terry-form-mcp.py)
SUCCESS=$(echo "$RESULT" | jq -r '.["terry-results"][-1].success')
if [ "$SUCCESS" != "true" ]; then
  echo "Terraform validation failed"
  exit 1
fi
```
