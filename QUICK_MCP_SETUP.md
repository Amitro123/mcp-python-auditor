# Quick MCP Setup

## 1. Get Paths

```bash
# Windows - Get Python path
cd C:\Users\USER\.gemini\antigravity\scratch\project-audit
venv\Scripts\activate
where python
# Copy the output

# Get project path
cd
# Copy the output
```

## 2. Configure Claude Desktop

Edit: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "project-audit": {
      "command": "PASTE_PYTHON_PATH_HERE",
      "args": ["PASTE_PROJECT_PATH_HERE\\mcp_server.py"],
      "env": {
        "PYTHONPATH": "PASTE_PROJECT_PATH_HERE"
      }
    }
  }
}
```

## 3. Restart Claude Desktop

Completely quit and reopen.

## 4. Test

In Claude chat:
```
Use audit_project to analyze C:\MyProject
```

See full guide: `INTEGRATION_GUIDE.md`
