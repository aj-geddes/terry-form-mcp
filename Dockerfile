FROM hashicorp/terraform:1.12

# Install Python, pip, and other dependencies
RUN apk add --no-cache python3 py3-pip curl unzip bash git

# Install terraform-ls
RUN TERRAFORM_LS_VERSION="0.38.5" && \
    curl -sSL "https://releases.hashicorp.com/terraform-ls/${TERRAFORM_LS_VERSION}/terraform-ls_${TERRAFORM_LS_VERSION}_linux_amd64.zip" -o terraform-ls.zip && \
    unzip terraform-ls.zip && \
    mv terraform-ls /usr/local/bin/ && \
    chmod +x /usr/local/bin/terraform-ls && \
    rm terraform-ls.zip

# Install Python dependencies (before COPY app files for better layer caching)
COPY requirements.txt .
RUN pip install --break-system-packages -r requirements.txt

# Create non-root user for security (Alpine syntax)
RUN addgroup -g 1001 -S terraform && \
    adduser -u 1001 -S terraform -G terraform

# Create app directory
WORKDIR /app

# Copy only the required files
COPY server_enhanced_with_lsp.py .
COPY terraform_lsp_client.py .
COPY mcp_request_validator.py .
COPY github_app_auth.py .
COPY github_repo_handler.py .
COPY terry-form-mcp.py .

# Create workspace directory with proper ownership
RUN mkdir -p /mnt/workspace && \
    chown -R terraform:terraform /mnt/workspace

# Set proper file permissions
RUN chown -R terraform:terraform /app && \
    chmod -R 755 /app && \
    chmod 644 /app/*.py

# Switch to non-root user
USER terraform

# Set up entrypoint to run the enhanced server
ENTRYPOINT ["python3", "server_enhanced_with_lsp.py"]

# Health check - verify server files and dependencies are present
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import sys; sys.path.append('/app'); import server_enhanced_with_lsp" || exit 1
