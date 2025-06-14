FROM hashicorp/terraform:latest

# Install Python, pip, and other dependencies
RUN apk add --no-cache python3 py3-pip curl unzip bash

# Install terraform-ls
RUN TERRAFORM_LS_VERSION="0.33.2" && \
    curl -sSL "https://releases.hashicorp.com/terraform-ls/${TERRAFORM_LS_VERSION}/terraform-ls_${TERRAFORM_LS_VERSION}_linux_amd64.zip" -o terraform-ls.zip && \
    unzip terraform-ls.zip && \
    mv terraform-ls /usr/local/bin/ && \
    chmod +x /usr/local/bin/terraform-ls && \
    rm terraform-ls.zip

# Allow pip to install into protected Alpine Python  
RUN pip install --break-system-packages fastmcp

# Create app directory
WORKDIR /app

# Copy only the required files
COPY terry-form-mcp.py .
COPY terraform_lsp_client.py .
COPY server_enhanced_with_lsp.py .

# Set up entrypoint to run the enhanced server
ENTRYPOINT ["python3", "server_enhanced_with_lsp.py"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.connect(('localhost', 8000)); s.close()" || exit 1
