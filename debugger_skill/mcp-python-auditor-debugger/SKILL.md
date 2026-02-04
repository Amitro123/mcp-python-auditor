---
name: mcp-python-auditor-debugger
description: Expert debugging workflow for MCP Python Auditor. Use when fixing bugs, timeouts, caching issues, or inaccurate results. Provides architecture understanding, systematic debugging, testing strategies, and automated fix scripts.
license: MIT
---

# MCP Python Auditor Debugger

## Critical Issues & Quick Fixes

### 1. Vulture Timeout (>120s)
**Problem**: Too many files passed to Vulture
**Fix**: Check `app/core/file_discovery.py` - ensure `.venv`, `node_modules`, `__pycache__` are filtered
**Verify**: Add logging to see file count before Vulture runs

### 2. Inaccurate Results
**Check**:
- Tool command in `app/tools/*_tool.py` matches manual run
- Output parsing in `_parse_output()` is correct
- Results aggregation in `report_generator.py`

### 3. Cache Not Working
**Check**:
- Paths normalized (relative vs absolute)
- Hash includes file content, not just mtime
- Cache keys unique per tool

### 4. Slow Performance
**Fix**:
- Use `--fast` mode (skips coverage/secrets)
- Enable Git-based file discovery
- Verify tools run in parallel (`asyncio.gather`)

## Diagnostic Scripts

Run these first:
```bash
python scripts/diagnose.py    # Full diagnostic
python scripts/quickfix.py    # Auto-fix common issues
```

## Systematic Debugging

1. **Reproduce**: Can you consistently reproduce it?
2. **Isolate**: Which component? (file discovery, tools, cache, report)
3. **Enable logging**: `logging.basicConfig(level=logging.DEBUG)`
4. **Add breakpoints**: `import pdb; pdb.set_trace()`
5. **Test fix**: Write failing test first
6. **Verify**: Run full test suite

## Architecture Quick Reference

```
audit.py → cli_adapter → orchestrator → [file_discovery, cache_manager, tools] → report_generator
```

**Key files**:
- `app/core/audit_orchestrator.py` - Main engine
- `app/core/file_discovery.py` - File filtering
- `app/core/cache_manager.py` - Caching logic
- `app/tools/*.py` - Individual tools

## References

- `references/architecture.md` - Detailed component diagram
- `references/debugging-checklist.md` - Step-by-step debugging
- `references/testing-guide.md` - Test patterns & fixtures
