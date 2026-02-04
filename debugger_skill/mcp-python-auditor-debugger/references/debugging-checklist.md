# Debug Checklist

## Quick Diagnostics
```bash
# 1. Check environment
python --version  # Must be 3.11+
which ruff bandit vulture radon

# 2. Test file discovery
python -c "from app.core.file_discovery import FileDiscovery; print(len(FileDiscovery().discover_python_files('.')))"

# 3. Clear cache
rm -rf .cache/auditor/

# 4. Run with debug logging
python -c "import logging; logging.basicConfig(level=logging.DEBUG)" -c "exec(open('audit.py').read())"
```

## Common Fixes

**Vulture Timeout**:
- Check file count: Should be <1000
- Verify .venv excluded in file_discovery.py
- Increase timeout in deadcode_tool.py

**Cache Issues**:
- Verify paths are relative, not absolute
- Check hash computation uses file content
- Ensure cache keys include tool name

**Wrong Results**:
- Run tool manually: `bandit -r . -f json`
- Compare with audit output
- Check _parse_output() method
