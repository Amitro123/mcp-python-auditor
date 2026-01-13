# ProjectAuditAgent - MCP Integration Update

## 🎯 New Files Added

### 1. **mcp_server.py** - MCP Stdio Adapter
- JSON-RPC protocol implementation
- Stdio transport for AI clients
- Exposes all 13 analysis tools via MCP
- Logs to `mcp_server.log` (not stdout)

### 2. **INTEGRATION_GUIDE.md** - Complete Setup Guide
- Prerequisites and installation
- Configuration for Claude Desktop, Cursor, Windsurf
- Absolute path instructions
- Usage examples and prompts
- Comprehensive troubleshooting

### 3. **QUICK_MCP_SETUP.md** - Fast Setup
- Minimal steps to get started
- Copy-paste configuration template
- Quick test instructions

## 🔧 How It Works

### Architecture

```
AI Client (Claude/Cursor/Windsurf)
    ↓ (stdio transport)
MCP Server (mcp_server.py)
    ↓ (Python imports)
Analyzer Agent + Tool Registry
    ↓
13 Analysis Tools
```

### MCP Protocol Flow

1. AI client starts `mcp_server.py` as subprocess
2. Communication via stdin/stdout (JSON-RPC)
3. Server exposes tools via `tools/list`
4. AI calls tools via `tools/call`
5. Results returned as formatted text

### Available MCP Tools

- `audit_project` - Full audit with all tools
- `run_structure` - Directory analysis
- `run_architecture` - Best practices
- `run_deadcode` - Vulture-based detection
- `run_complexity` - Radon metrics
- `run_security` - Bandit + pip-audit
- `run_typing` - Type coverage
- `run_duplication` - Code duplicates
- `run_efficiency` - Performance checks
- `run_cleanup` - Temp files
- `run_tests` - Coverage analysis
- `run_gitignore` - Recommendations
- `run_secrets` - Credential detection

## 📝 Configuration Example

**Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "project-audit": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\project-audit\\mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\project-audit"
      }
    }
  }
}
```

## 🎬 Usage Examples

**In AI Chat:**

```
Use audit_project to analyze my FastAPI project at C:\Projects\my-api
```

```
Run security analysis on /Users/me/python-app using run_security
```

```
Check type coverage in the current project with run_typing
```

## 🐛 Debugging

Check logs:
```bash
tail -f mcp_server.log
```

Test manually:
```bash
python mcp_server.py
# Should wait for stdin (Ctrl+C to exit)
```

## ✅ Verification

After setup:
1. Restart AI client
2. Type: "List available MCP tools"
3. Should see `project-audit` tools
4. Try: "Use audit_project on C:\TestProject"

## 🎉 Benefits

- **No HTTP server needed** - Direct stdio communication
- **AI-native integration** - Tools appear in AI's context
- **Natural language** - Just describe what you want
- **Comprehensive analysis** - All 13 tools available
- **Production libraries** - Vulture, Radon, Bandit, pip-audit

---

**Your AI can now audit Python projects!** 🚀
