# 🔌 MCP Configuration & User Guide

This guide explains how to connect the Project Audit Agent to your AI Assistant (Claude Desktop or Cursor) and how to interact with it effectively.

---

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Configuration](#configuration)
3. [Available Commands](#available-commands)
4. [Example Workflows](#example-workflows)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Python Environment
- Python 3.12 or higher installed
- Virtual environment created and activated
- All dependencies installed:
  ```bash
  pip install -r requirements.txt
  pip install bandit detect-secrets vulture radon ruff pip-audit pytest pytest-cov
  ```

### 2. MCP-Compatible Client
- **Claude Desktop** (Mac/Windows)
- **Cursor IDE** with MCP support
- **Any MCP-compatible AI assistant**

---

## Configuration

### Claude Desktop Setup

#### Step 1: Locate Config File
The configuration file location depends on your operating system:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

#### Step 2: Add Server Entry
Edit the config file and add the `project-audit` server:

```json
{
  "mcpServers": {
    "project-audit": {
      "command": "python",
      "args": ["C:\\absolute\\path\\to\\mcp-python-auditor\\mcp_fastmcp_server.py"]
    }
  }
}
```

**Important Notes:**
- ✅ Use **absolute paths** (not relative)
- ✅ Use double backslashes (`\\`) on Windows
- ✅ Ensure the path points to `mcp_fastmcp_server.py`

#### Step 3: Restart Claude
Close and reopen Claude Desktop for changes to take effect.

#### Step 4: Verify Connection
Ask Claude:
```
"What MCP servers are available?"
```

You should see `project-audit` listed.

---

### Cursor IDE Setup

1. Open Cursor Settings (`Ctrl+,` or `Cmd+,`)
2. Navigate to **Features** → **MCP**
3. Add server configuration:
   ```json
   {
     "command": "python",
     "args": ["C:\\absolute\\path\\to\\mcp-python-auditor\\mcp_fastmcp_server.py"]
   }
   ```

---

## Available Commands

The MCP server exposes specific tools through natural language. Here's what you can ask:

### 🛠️ Core Audit Tools

| Goal | Prompt Example | Tool Triggered |
|------|----------------|----------------|
| **Full Project Audit** | "Run a full audit on `C:/Projects/MyApp`" | `start_full_audit` |
| **Check Status** | "Check the status of audit job `abc123`" | `check_audit_status` |
| **Generate Report** | "Generate a full report for the current directory" | `generate_full_report` |

### 🔍 Specific Analysis

| Goal | Prompt Example | Tool Triggered |
|------|----------------|----------------|
| **Code Quality** | "Check code quality and dead code" | `audit_quality` |
| **Architecture** | "Analyze the project architecture" | `audit_architecture` |
| **Cleanup** | "Find files we can clean up" | `audit_cleanup` |
| **Git Changes** | "What are recent git changes?" | `audit_git` |

### 🔧 Auto-Fix

| Goal | Prompt Example | Tool Triggered |
|------|----------------|----------------|
| **Dry Run** | "Show what auto-fix would do (dry run)" | `run_auto_fix(confirm=False)` |
| **Execute** | "Run auto-fix with confirm=True" | `run_auto_fix(confirm=True)` |

---

## Example Workflows

### Workflow 1: New Project Analysis

```
👤 You: "I have a Python project at C:/Code/MyAPI. 
       Run a full audit and tell me the top 3 priorities."

🤖 Claude: [Calls start_full_audit]
          
          📊 Audit Complete!
          Score: 72/100 🟡
          
          Top Priorities:
          1. 🔴 Security: 3 vulnerabilities found (Bandit)
          2. 🟡 Testing: Low coverage (45%)
          3. 🟡 Dead Code: 12 unused functions detected
          
          Full report saved to: reports/FULL_AUDIT_abc123.md
```

### Workflow 2: Incremental Cleanup

```
👤 You: "What cleanup opportunities exist?"

🤖 Claude: [Calls audit_cleanup]
          
          Found 850 MB of cleanup opportunities:
          - __pycache__: 450 MB (1200 files)
          - .pytest_cache: 200 MB
          - htmlcov: 150 MB
          - dist/build: 50 MB
```

```
👤 You: "Run auto-fix dry run to see what would happen"

🤖 Claude: [Calls run_auto_fix(confirm=False)]
          
          Planned Actions:
          1. Backup: Would create backup_20260113.zip
          2. Cleanup: Would delete 1200 cache files (850 MB)
          3. Style: Would run 'ruff check --fix' and 'ruff format'
          4. Git: Would create branch 'fix/audit-20260113'
```

```
👤 You: "Looks good, execute it"

🤖 Claude: [Calls run_auto_fix(confirm=True)]
          
          ✅ Auto-Fix Complete!
          - Backup created: .backups/backup_20260113.zip
          - Deleted: 1200 cache files
          - Fixed: 45 code style issues
          - Branch: fix/audit-20260113 created and committed
```

### Workflow 3: Architecture Review

```
👤 You: "Show me the architecture dependencies"

🤖 Claude: [Calls audit_architecture]
          
          Architecture Analysis:
          - Total Files: 89
          - Dependencies: 124 internal imports
          
          Mermaid Graph Generated:
          [Shows interactive Mermaid diagram grouped by directory]
          
          Recommendation: Consider breaking down the 'core' module
          which has 45 incoming dependencies (potential bottleneck).
```

---

## Understanding Tool Responses

### 1. Full Audit Response Structure

When you run a full audit, you'll receive:

```json
{
  "status": "completed",
  "job_id": "abc123",
  "score": 72,
  "duration": "45.2s",
  "report_path": "reports/FULL_AUDIT_abc123.md",
  "top_priorities": [
    "🔴 Security: 3 vulnerabilities",
    "🟡 Testing: Coverage 45%",
    "🟡 Dead Code: 12 unused functions"
  ]
}
```

### 2. Auto-Fix Response Structure

**Dry Run (`confirm=False`):**
```json
{
  "status": "dry_run",
  "actions_planned": {
    "cleanup": "Would delete 850 MB",
    "style_fix": "Would run ruff",
    "backup": "Would create backup",
    "git": "Would create branch fix/audit-123"
  }
}
```

**Execute (`confirm=True`):**
```json
{
  "status": "completed",
  "fixes": [
    "Backup created: backup.zip",
    "Cleanup: Deleted 1200 files",
    "Code Style: Ran ruff fixes",
    "Git: Created branch fix/audit-123"
  ],
  "errors": []
}
```

---

## Troubleshooting

### Issue: "Tool Not Found"

**Symptom:** Claude says "I don't have access to project-audit tool"

**Solutions:**
1. Restart Claude Desktop completely
2. Check config file path is correct
3. Look at Claude logs:
   - Windows: `%APPDATA%\Claude\logs\mcp*.log`
   - Mac: `~/Library/Logs/Claude/mcp*.log`

### Issue: "Executable Not Found"

**Symptom:** Error about Python not found

**Solutions:**
1. Use full path to Python executable:
   ```json
   {
     "command": "C:\\Python312\\python.exe",
     "args": ["C:\\path\\to\\mcp_fastmcp_server.py"]
   }
   ```

2. Or use virtual environment Python:
   ```json
   {
     "command": "C:\\path\\to\\mcp-python-auditor\\.venv\\Scripts\\python.exe",
     "args": ["C:\\path\\to\\mcp_fastmcp_server.py"]
   }
   ```

### Issue: "Missing Tool: bandit"

**Symptom:** Server logs show "Missing tool: bandit, detect-secrets, vulture..."

**Solution:**
```bash
# Activate your venv first
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install missing tools
pip install bandit detect-secrets vulture radon ruff pip-audit
```

### Issue: "Git dirty check failed"

**Symptom:** Auto-fix aborts with "You have uncommitted changes"

**Solution:**
```bash
# Option 1: Commit your work
git add .
git commit -m "Your changes

"

# Option 2: Stash your changes
git stash

# Then run auto-fix again
```

### Issue: Reports Not Generating

**Symptom:** Audit runs but no report file created

**Solutions:**
1. Check permissions on `reports/` directory
2. Ensure the directory exists:
   ```bash
   mkdir reports
   ```
3. Check disk space

---

## Advanced Usage

### Custom Tool Combinations

You can ask Claude to combine multiple tools:

```
"Run quality audit and architecture analysis, 
then tell me if the code structure matches FastAPI best practices"
```

Claude will intelligently call:
1. `audit_quality` → Dead code, complexity
2. `audit_architecture` → Import structure
3. Synthesize results against FastAPI patterns

### Background Jobs

For large projects, use background jobs:

```
👤: "Start a background audit on /huge/project"
🤖: [Calls start_full_audit]
    Job started: abc123
    
    [wait 30 seconds]
    
👤: "Check status of job abc123"
🤖: [Calls check_audit_status]
    Status: running (60% complete)
    
    [wait more]
    
👤: "Check status again"
🤖: [Calls check_audit_status]
    ✅ Complete! Score: 85/100
    Report: reports/FULL_AUDIT_abc123.md
```

---

## Best Practices

### 1. Start with Dry Runs
Always run auto-fix in dry-run mode first:
```
"Show me what auto-fix would do"
```

### 2. Commit Before Auto-Fix
Auto-fix has a built-in dirty check, but it's good practice:
```bash
git add .
git commit -m "Before auto-fix"
```

### 3. Review Architecture First
Before making changes, understand your codebase:
```
"Analyze architecture and show me the dependency graph"
```

### 4. Incremental Improvements
Don't try to fix everything at once:
```
"Fix only the security issues first"
```

---

## Getting Help

If you encounter issues:

1. **Check Logs:**
   - MCP logs: `%APPDATA%\Claude\logs\`
   - Server logs: `debug_audit.txt` in project root

2. **Test Direct Invocation:**
   ```bash
   python mcp_fastmcp_server.py
   ```
   
3. **Verify Tools:**
   ```bash
   python -c "import bandit, detect_secrets, vulture, radon"
   ```

4. **Minimal Test:**
   Ask Claude:
   ```
   "Run audit_git on the current directory"
   ```
   (Simplest tool, no dependencies)

---

## Summary

**Setup Checklist:**
- ✅ Python 3.12+ installed
- ✅ Dependencies installed (`pip install -r requirements.txt`)
- ✅ Analysis tools installed (bandit, ruff, etc.)
- ✅ Config file updated with **absolute path**
- ✅ Claude restarted
- ✅ Connection verified

**First Commands to Try:**
1. `"What MCP servers are available?"` → Verify connection
2. `"Run audit_git on c:/my/project"` → Simple test
3. `"Run a full audit on c:/my/project"` → Full analysis

---

**Happy Auditing! 🚀**
