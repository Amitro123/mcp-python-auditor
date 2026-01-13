# MCP Client Integration Guide

Complete guide for integrating ProjectAuditAgent with AI clients (Claude Desktop, Cursor, Windsurf) via MCP (Model Context Protocol).

## 📋 Prerequisites

### 1. System Requirements
- Python 3.12+
- Virtual environment support
- AI client installed (Claude Desktop, Cursor, or Windsurf)

### 2. Installation

```bash
# Navigate to project directory
cd project-audit

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Get Absolute Paths

You'll need two absolute paths for configuration:

**1. Python executable in venv:**

```bash
# Windows:
where python
# Output: C:\Users\USER\.gemini\antigravity\scratch\project-audit\venv\Scripts\python.exe

# macOS/Linux:
which python
# Output: /Users/username/project-audit/venv/bin/python
```

**2. Project root directory:**

```bash
# Windows:
cd
# Output: C:\Users\USER\.gemini\antigravity\scratch\project-audit

# macOS/Linux:
pwd
# Output: /Users/username/project-audit
```

## 🔧 MCP Configuration

### Claude Desktop

**Config file location:**
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

**Configuration:**

```json
{
  "mcpServers": {
    "project-audit": {
      "command": "C:\\Users\\USER\\.gemini\\antigravity\\scratch\\project-audit\\venv\\Scripts\\python.exe",
      "args": [
        "C:\\Users\\USER\\.gemini\\antigravity\\scratch\\project-audit\\mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\USER\\.gemini\\antigravity\\scratch\\project-audit"
      }
    }
  }
}
```

**macOS/Linux version:**

```json
{
  "mcpServers": {
    "project-audit": {
      "command": "/Users/username/project-audit/venv/bin/python",
      "args": [
        "/Users/username/project-audit/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/username/project-audit"
      }
    }
  }
}
```

### Cursor

**Config file location:**
- **Windows:** `%APPDATA%\Cursor\User\globalStorage\cursor.json`
- **macOS:** `~/Library/Application Support/Cursor/User/globalStorage/cursor.json`

**Configuration:**

```json
{
  "mcp": {
    "servers": {
      "project-audit": {
        "command": "C:\\Users\\USER\\.gemini\\antigravity\\scratch\\project-audit\\venv\\Scripts\\python.exe",
        "args": [
          "C:\\Users\\USER\\.gemini\\antigravity\\scratch\\project-audit\\mcp_server.py"
        ],
        "env": {
          "PYTHONPATH": "C:\\Users\\USER\\.gemini\\antigravity\\scratch\\project-audit"
        }
      }
    }
  }
}
```

### Windsurf

**Config file location:**
- **Windows:** `%APPDATA%\Windsurf\mcp_config.json`
- **macOS:** `~/Library/Application Support/Windsurf/mcp_config.json`

**Configuration:** (Same format as Cursor)

```json
{
  "mcp": {
    "servers": {
      "project-audit": {
        "command": "/path/to/venv/bin/python",
        "args": ["/path/to/project-audit/mcp_server.py"],
        "env": {
          "PYTHONPATH": "/path/to/project-audit"
        }
      }
    }
  }
}
```

## 🚀 Usage Instructions

### 1. Restart AI Client

After updating the configuration file:
1. **Completely quit** the AI client (not just close the window)
2. **Restart** the application
3. The MCP server will auto-connect on startup

### 2. Verify Connection

In your AI client chat, type:

```
List available MCP tools
```

You should see tools like:
- `audit_project` - Full comprehensive audit
- `run_deadcode` - Dead code detection
- `run_complexity` - Complexity analysis
- `run_security` - Security analysis
- `run_typing` - Type coverage analysis
- And 9 more tools...

### 3. Example Prompts

**Full Project Audit:**
```
Use the audit_project tool to analyze the project at C:\Users\USER\MyProject
```

**Security Analysis Only:**
```
Run security analysis on /Users/username/my-fastapi-app using the run_security tool
```

**Dead Code Detection:**
```
Check for dead code in the current project directory using run_deadcode
```

**Complexity Check:**
```
Analyze code complexity for C:\Projects\backend with the run_complexity tool
```

**Type Coverage:**
```
What's the type hint coverage in /home/user/python-project? Use run_typing
```

**Custom Tool Selection:**
```
Audit C:\MyApp but only run security, deadcode, and complexity tools
```

### 4. Understanding Results

The AI will receive:
- **Comprehensive markdown report** with all findings
- **Overall score** (0-100)
- **Detailed metrics** per tool
- **Actionable recommendations**

Example response:
```markdown
# Audit Results

**Score:** 78/100

Analysis complete: 13/13 tools succeeded. Overall score: 78/100. Test coverage: 62%

---

# Project Audit: C:\MyProject
**Date:** 2026-01-03 18:00:00 | **Score:** 78/100

## 🔒 Security Analysis (3 issues)
**Severity Breakdown:**
- 🔴 HIGH: 1
- 🟡 MEDIUM: 2

...
```

## 🔍 Troubleshooting

### Check MCP Server Logs

The MCP server writes logs to `mcp_server.log` in the project directory:

```bash
# View logs
tail -f project-audit/mcp_server.log

# Windows:
Get-Content project-audit\mcp_server.log -Tail 50 -Wait
```

### Common Issues

#### 1. "MCP server not found" or "Connection failed"

**Cause:** Incorrect paths in configuration

**Solution:**
- Verify Python executable path: `where python` (Windows) or `which python` (macOS/Linux)
- Ensure you're using the **venv** python, not system python
- Use **absolute paths**, not relative
- On Windows, use double backslashes `\\` or forward slashes `/`

**Test the command manually:**
```bash
# Windows:
C:\Users\USER\.gemini\antigravity\scratch\project-audit\venv\Scripts\python.exe C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp_server.py

# macOS/Linux:
/Users/username/project-audit/venv/bin/python /Users/username/project-audit/mcp_server.py
```

If this hangs (waiting for input), the server is working correctly. Press Ctrl+C to exit.

#### 2. "Module not found" errors

**Cause:** Missing dependencies or incorrect PYTHONPATH

**Solution:**
```bash
# Activate venv and reinstall
cd project-audit
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

# Verify PYTHONPATH in config points to project root
```

#### 3. "Tool execution failed"

**Cause:** External tools (vulture, radon, bandit) not installed

**Solution:**
```bash
# Install all analysis tools
pip install vulture radon bandit pip-audit pyyaml

# Verify installation
vulture --version
radon --version
bandit --version
```

**Note:** Tools gracefully fallback if not installed, but results will be limited.

#### 4. "Permission denied" on project path

**Cause:** MCP server doesn't have read access to target project

**Solution:**
- Ensure the project path exists and is readable
- On Windows, avoid network drives or restricted folders
- Use local paths when possible

#### 5. AI client doesn't show tools

**Cause:** Configuration not loaded or syntax error in JSON

**Solution:**
- Validate JSON syntax: https://jsonlint.com/
- Check for trailing commas (not allowed in JSON)
- Ensure file is saved after editing
- Restart AI client completely (quit and reopen)

### Enable Debug Logging

Edit `mcp_server.py` to increase log verbosity:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='mcp_server.log'
)
```

### Test Without AI Client

You can test the MCP server directly:

```bash
# Start server
python mcp_server.py

# In another terminal, send a test request:
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python mcp_server.py
```

## 📊 Available Tools

| Tool Name | Description | Use Case |
|-----------|-------------|----------|
| `audit_project` | Full comprehensive audit | Complete project analysis |
| `run_structure` | Directory tree analysis | Understand project layout |
| `run_architecture` | FastAPI/Python best practices | Check architecture patterns |
| `run_deadcode` | Unused code detection (Vulture) | Find dead code |
| `run_complexity` | Cyclomatic complexity (Radon) | Identify complex functions |
| `run_security` | Security analysis (Bandit + pip-audit) | Find vulnerabilities |
| `run_typing` | Type hint coverage | Check type annotations |
| `run_duplication` | Code duplicate detection | Find repeated code |
| `run_efficiency` | Performance anti-patterns | Optimize code |
| `run_cleanup` | Cache/temp file detection | Clean up project |
| `run_tests` | Test coverage analysis | Check test quality |
| `run_gitignore` | Gitignore recommendations | Improve gitignore |

## 🎯 Best Practices

### 1. Use Specific Tools for Focused Analysis

Instead of always running full audit, use specific tools:
- **Before commit:** `run_security`, `run_deadcode`
- **Code review:** `run_complexity`, `run_duplication`
- **Refactoring:** `run_typing`, `run_efficiency`

### 2. Configure Project-Specific Settings

Create `audit.yaml` in your project:

```yaml
audit:
  exclude:
    - "migrations/"
    - "tests/fixtures/"
  
  thresholds:
    complexity: 15
    type_coverage: 70
```

### 3. Interpret Scores

- **90-100:** Excellent - Production ready
- **75-89:** Good - Minor improvements needed
- **60-74:** Fair - Moderate refactoring recommended
- **Below 60:** Needs work - Significant issues

### 4. Iterate on Findings

1. Run audit
2. Fix high-priority issues (security, dead code)
3. Re-run specific tools to verify fixes
4. Gradually improve score over time

## 🔄 Updating the Server

When you update ProjectAuditAgent code:

```bash
# Pull latest changes
cd project-audit
git pull

# Reinstall dependencies (if requirements changed)
pip install -r requirements.txt

# Restart AI client to reload MCP server
```

## 📝 Example Workflow

1. **Initial Setup:**
   ```
   Hey Claude, use audit_project to analyze my FastAPI project at C:\Projects\my-api
   ```

2. **Review Results:**
   - AI shows comprehensive report
   - Identifies 3 security issues, 7 dead functions, type coverage at 45%

3. **Fix Issues:**
   - Fix security vulnerabilities
   - Remove dead code
   - Add type hints

4. **Verify Fixes:**
   ```
   Run security analysis again on C:\Projects\my-api to verify fixes
   ```

5. **Check Improvement:**
   ```
   What's the new type coverage? Use run_typing on C:\Projects\my-api
   ```

## 🆘 Getting Help

If you encounter issues:

1. Check `mcp_server.log` for errors
2. Verify configuration paths are absolute and correct
3. Test Python command manually
4. Ensure all dependencies installed
5. Try with a simple test project first

## 🎉 Success Indicators

You'll know it's working when:
- ✅ AI client shows "project-audit" in available tools
- ✅ Running `audit_project` returns a detailed report
- ✅ No errors in `mcp_server.log`
- ✅ Individual tools (`run_security`, etc.) execute successfully

---

**Ready to audit your projects with AI assistance!** 🚀
