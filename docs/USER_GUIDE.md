# Terry User Guide - Local Mode Setup

Welcome! This guide will help you set up Terry (Terraform Assistant) on your computer using Docker Desktop. Terry helps AI assistants understand and work with Terraform infrastructure code.

## What You'll Need

Before starting, make sure you have:
- ✅ Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop/))
- ✅ Your favorite AI coding assistant (Cursor, Claude Desktop, etc.)
- ✅ 5 minutes of time

## Step 1: Start Docker Desktop

1. **Open Docker Desktop** 
   - On Windows: Click the Docker whale icon in your system tray
   - On Mac: Click the Docker whale icon in your menu bar
   
2. **Wait for Docker to start**
   - You'll see "Docker Desktop is running" when it's ready
   - The whale icon will stop animating

## Step 2: Get Terry Running

### Option A: The Simplest Way (Recommended)

Open your terminal (Command Prompt on Windows, Terminal on Mac) and copy-paste this command:

```bash
docker run -d --name terry -p 3000:3000 terraform-mcp-server:latest
```

### Option B: With Docker Desktop UI

1. Open Docker Desktop
2. Click on "Images" in the left sidebar
3. Click "Search images to run"
4. Search for `terraform-mcp-server`
5. Click "Run"
6. Expand "Optional Settings"
7. Set:
   - Container name: `terry`
   - Ports: `3000` → `3000`
8. Click "Run"

## Step 3: Check Terry is Working

1. **Open your web browser**
2. **Go to**: http://localhost:3000
3. **You should see**: Terry's status page showing "Local Mode"

🎉 **Success!** You should see a page that looks like this:

```
Terry MCP Server - Local Mode
✓ Terraform Registry - Always Available
✗ Terraform Cloud - Not Available
✓ Web UI - Enabled
✗ MCP Bridge - Not Available
```

## Step 4: Connect Terry to Your IDE

### For Cursor Users

1. **Open Cursor Settings**
   - Press `Cmd+,` (Mac) or `Ctrl+,` (Windows)
   
2. **Find MCP Settings**
   - Search for "MCP" in the settings search bar
   - Click on "MCP" in the results

3. **Add Terry**
   - Click "+ Add new MCP server"
   - Fill in:
     - Name: `terry-local`
     - Type: `stdio`
     - Command: `docker`
     - Arguments: `exec -i terry node dist/index.js`
   - Click "Add"

4. **Enable Terry**
   - Find "terry-local" in your MCP servers list
   - Click the toggle to enable it

5. **Restart Cursor**
   - Close and reopen Cursor
   - Terry is now available to help with Terraform!

### For Claude Desktop Users

1. **Open Claude Desktop Settings**
   - Press `Cmd+,` (Mac) or `Ctrl+,` (Windows)
   - Go to "Developer" tab

2. **Edit Configuration**
   - Click "Edit Config"
   - Add this configuration:

```json
{
  "mcpServers": {
    "terry-local": {
      "command": "docker",
      "args": ["exec", "-i", "terry", "node", "dist/index.js"]
    }
  }
}
```

3. **Save and Restart**
   - Save the file
   - Restart Claude Desktop

## Using Terry

Once connected, you can ask your AI assistant Terraform questions like:

- "What arguments does the AWS S3 bucket resource accept?"
- "Show me how to use the AWS VPC module"
- "Search for Azure storage modules"
- "What data sources are available for Google Cloud?"

### Example Conversations

**You**: "Help me create an AWS S3 bucket"

**AI Assistant** (powered by Terry): "I'll help you create an S3 bucket. Let me look up the current syntax..."
*Terry automatically provides the latest resource documentation*

**You**: "Find me a good Terraform module for creating a VPC"

**AI Assistant**: "Let me search for popular VPC modules..."
*Terry searches the Terraform Registry and suggests highly-rated modules*

## Keeping Terry Running

### Starting Terry
If Docker Desktop was closed:
1. Open Docker Desktop
2. Go to "Containers"
3. Find "terry"
4. Click the play button ▶️

### Stopping Terry
When you don't need Terry:
1. Open Docker Desktop
2. Go to "Containers"
3. Find "terry"
4. Click the stop button ⏹️

### Checking Terry's Status
Visit http://localhost:3000 anytime to see if Terry is running.

## Troubleshooting

### "Cannot connect to Terry"
1. **Check Docker Desktop is running**
2. **Check Terry container is running**:
   - Open Docker Desktop → Containers
   - "terry" should show as "Running"
3. **Try restarting Terry**:
   - Click stop button, wait 5 seconds, click play button

### "Port 3000 is already in use"
Another application is using port 3000. Fix:
```bash
docker run -d --name terry -p 3001:3000 terraform-mcp-server:latest
```
Then visit http://localhost:3001 instead.

### "Terry commands not working in IDE"
1. **Restart your IDE** after adding Terry
2. **Check the command** in your IDE's MCP settings:
   - Should be: `docker exec -i terry node dist/index.js`
3. **Ensure Terry container is running** in Docker Desktop

### Getting Help

- **Container Logs**: Docker Desktop → Containers → terry → View logs
- **Status Page**: http://localhost:3000
- **GitHub Issues**: Report problems at the Terry repository

## Updating Terry

When a new version is available:

1. **Stop and remove old Terry**:
```bash
docker stop terry
docker rm terry
```

2. **Get the latest version**:
```bash
docker pull terraform-mcp-server:latest
```

3. **Start new Terry**:
```bash
docker run -d --name terry -p 3000:3000 terraform-mcp-server:latest
```

## Tips for Success

- 🚀 **Keep Docker Desktop running** when using Terry
- 📊 **Check status page** if things seem wrong: http://localhost:3000
- 🔄 **Restart your IDE** after Terry configuration changes
- 💡 **Local mode is perfect** for personal use - no cloud tokens needed!

## What's Next?

Now that Terry is running, try asking your AI assistant:
- "What Terraform providers are available?"
- "Show me examples of AWS EC2 instances"
- "Find modules for Kubernetes deployment"

Enjoy using Terry to make your Terraform work easier!