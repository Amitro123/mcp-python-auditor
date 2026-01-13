# AutoFix Orchestrator - Usage Guide

## 🚀 Quick Start

### Interactive Mode (Recommended)
```bash
python -m app.core.fix_orchestrator
```

This will:
1. Scan your project for dead code
2. Show each issue with context (2 lines before/after)
3. Ask for confirmation before each fix
4. Create `.bak` backups automatically

### Auto Mode (Low-Risk Only)
```bash
python -m app.core.fix_orchestrator --auto
```

This will automatically fix **only** low-risk issues (unused imports) without prompting.

### Specify Project Path
```bash
python -m app.core.fix_orchestrator /path/to/project
```

---

## 🎨 Risk Classification

### 🟢 [LOW RISK] - Unused Imports
- **What**: Import statements that are never used
- **Example**: `import os` when `os` is never referenced
- **Safety**: Very safe - only the import line is removed
- **Auto-fixed**: Yes (in `--auto` mode)

### 🔴 [HIGH RISK] - Unused Functions/Variables
- **What**: Function definitions or variables that are never called/referenced
- **Example**: `def unused_helper():` or `unused_var = 42`
- **Safety**: Risky - only removes the **definition line**, not the entire function body
- **Auto-fixed**: No (requires manual confirmation)

---

## 📋 Interactive Session Example

```
══════════════════════════════════════════════════════════════════════
🚀 AUTO-FIX ORCHESTRATOR
══════════════════════════════════════════════════════════════════════
📂 Project: /path/to/mcp-python-auditor

🔍 Scanning for dead code...

⚠️  Found 10 fixable issue(s):
   [LOW RISK]  Unused Imports: 9
   [HIGH RISK] Functions/Variables: 1

──────────────────────────────────────────────────────────────────────
[LOW RISK] Unused Import
📄 File: app/main.py
📍 Line: 12
🏷️  Name: ReportResponse

Context:
     10 | from app.core.analyzer_agent import AnalyzerAgent
     11 | from app.core.report_generator import ReportGenerator
  →  12 | from app.schemas import AuditResult, ToolResult, ReportResponse
     13 | from app.core.self_healing import SelfHealing
     14 | from app.core.tool_registry import registry

Delete this line? [y/N]: y
   🛠️  Applying fix... ✓ Done

──────────────────────────────────────────────────────────────────────
[HIGH RISK] Unused Function
📄 File: app/tools/git_tool.py
📍 Line: 156
🏷️  Name: _parse_log_output

Context:
    154 |     
    155 |     @staticmethod
  → 156 |     def _parse_log_output(output: str) -> List[Dict[str, str]]:
    157 |         """Parse git log output into structured data."""
    158 |         commits = []

Delete this line? [y/N]: n

══════════════════════════════════════════════════════════════════════
📊 MISSION COMPLETE
══════════════════════════════════════════════════════════════════════

✅ Fixes Applied: 9
   • app/main.py (1 fix)
   • self_audit.py (7 fixes)
   • app/tools/cleanup_tool.py (1 fix)

⏭️  Fixes Skipped: 1

💡 TIP: Backup files created with .bak extension
    To restore: use CodeEditorTool.restore_backup()

══════════════════════════════════════════════════════════════════════
```

---

## 🔧 Advanced Usage

### Restore from Backup

If you need to undo changes:

```python
from app.tools.code_editor_tool import CodeEditorTool

editor = CodeEditorTool()
editor.restore_backup("app/main.py")
```

### Programmatic Usage

```python
from app.core.fix_orchestrator import AutoFixOrchestrator

orchestrator = AutoFixOrchestrator(project_path=".")

# Interactive mode
result = orchestrator.run_cleanup_mission(interactive=True)

# Auto mode (low-risk only)
result = orchestrator.run_cleanup_mission(interactive=False)

print(f"Applied {result['fixes_applied']} fixes")
print(f"Modified files: {result['files_modified']}")
```

---

## ⚠️ Important Notes

1. **Backup First**: Always commit your work or create a backup before running AutoFix
2. **Review Changes**: Even with `.bak` files, manually review all changes
3. **High-Risk Fixes**: Currently only deletes the definition line - full function body removal coming soon
4. **Line Order**: Fixes are applied bottom-to-top to preserve line numbers
5. **Test After**: Always run tests after applying fixes

---

## 🐛 Troubleshooting

### "Failed to read file"
- **Cause**: File permissions or encoding issues
- **Solution**: Check file permissions and ensure UTF-8 encoding

### "Line X out of range"
- **Cause**: File was modified between scan and fix
- **Solution**: Re-run the orchestrator to rescan

### Want to restore all backups?
```bash
# Find all .bak files
find . -name "*.bak"

# Restore them (careful!)
for file in $(find . -name "*.bak"); do
    cp "$file" "${file%.bak}"
done
```

---

## 📊 What Gets Fixed?

✅ **Currently Supported:**
- Unused import statements
- Unused variable assignments (with confirmation)
- Unused function definitions (with confirmation, definition line only)

🚧 **Coming Soon:**
- Full function body removal
- Duplicate code consolidation
- Unused class definitions
- Git integration (auto-commit after fixes)

---

**Status: ✅ PRODUCTION READY**

For issues or feature requests, check the project documentation.
