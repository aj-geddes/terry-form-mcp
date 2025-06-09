FROM hashicorp/terraform:1.8

RUN apk add --no-cache python3 py3-pip

# Allow pip to install into protected Alpine Python
RUN pip install --break-system-packages fastmcp

WORKDIR /app
COPY terry-form-mcp.py .
COPY server.py .

ENTRYPOINT ["python3", "server.py"]
