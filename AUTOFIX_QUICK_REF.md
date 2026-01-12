# AutoFix Quick Reference

## 🚀 Commands

| Command | Description |
|---------|-------------|
| `python -m app.core.fix_orchestrator` | Interactive mode (recommended) |
| `python -m app.core.fix_orchestrator --auto` | Auto-fix low-risk only |
| `python -m app.core.fix_orchestrator /path` | Specify project path |

## 🎨 Risk Levels

| Risk | Type | Safety | Auto-Fixed |
|------|------|--------|------------|
| 🟢 LOW | Unused Imports | Very Safe | Yes |
| 🔴 HIGH | Functions/Variables | Risky (def line only) | No |

## 📋 Workflow

1. **Scan** → Detects dead code via vulture
2. **Classify** → Sorts by risk level
3. **Display** → Shows context (±2 lines)
4. **Confirm** → User approval (interactive mode)
5. **Apply** → Delete line + create .bak
6. **Report** → Summary of changes

## 🛡️ Safety Features

- ✅ Automatic `.bak` backup before each fix
- ✅ Context display (2 lines before/after)
- ✅ Color-coded risk levels
- ✅ User confirmation (interactive mode)
- ✅ Reverse-order application (preserves line numbers)

## 🔄 Restore Backup

```python
from app.tools.code_editor_tool import CodeEditorTool
CodeEditorTool().restore_backup("file.py")
```

## 📊 Example Output

```
══════════════════════════════════════════════════════════════════
🚀 AUTO-FIX ORCHESTRATOR
══════════════════════════════════════════════════════════════════
📂 Project: /mcp-python-auditor

⚠️  Found 10 fixable issue(s):
   [LOW RISK]  Unused Imports: 9
   [HIGH RISK] Functions/Variables: 1

──────────────────────────────────────────────────────────────────
[LOW RISK] Unused Import
📄 File: app/main.py
📍 Line: 12
🏷️  Name: ReportResponse

Context:
     10 | from app.core.analyzer_agent import AnalyzerAgent
     11 | from app.core.report_generator import ReportGenerator
  →  12 | from app.schemas import AuditResult, ToolResult, ReportResponse
     13 | from app.core.self_healing import SelfHealing

Delete this line? [y/N]: y
   🛠️  Applying fix... ✓ Done

══════════════════════════════════════════════════════════════════
📊 MISSION COMPLETE
══════════════════════════════════════════════════════════════════

✅ Fixes Applied: 9
   • app/main.py (1 fix)
   • self_audit.py (7 fixes)

💡 TIP: Backup files created with .bak extension
```

## ⚠️ Best Practices

1. **Commit first** - Always have clean git state
2. **Review changes** - Check modified files
3. **Run tests** - Verify nothing broke
4. **Keep backups** - Don't delete .bak files immediately

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "File not found" | Check project path |
| "Line out of range" | Re-run scan (file was modified) |
| Want to undo all | Restore from .bak files |

---

**Full Guide:** See `AUTOFIX_GUIDE.md`  
**Status:** ✅ Production Ready
