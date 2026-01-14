# 🎯 PR Gatekeeper - Quick Reference

## One-Line Summary
**Fast, smart code auditing for PRs - scans ONLY changed files, runs tests as safety net, returns explicit recommendation.**

## Usage

### Via MCP (Claude/AI)
```
"Run PR audit on this project"
"Check my PR changes against main branch"
"Audit only the files I modified"
```

### Via Python
```python
from mcp_fastmcp_server import audit_pr_changes

result = audit_pr_changes(
    path="C:/Projects/MyApp",
    base_branch="main",      # Compare against this branch
    run_tests=True           # Run pytest as safety net
)
```

### Via Command Line
```bash
python test_pr_gatekeeper.py
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | Required | Project directory path |
| `base_branch` | str | `"main"` | Base branch to compare against |
| `run_tests` | bool | `True` | Run pytest if score > 80 |

## Output

### JSON Structure
```json
{
  "status": "success",
  "recommendation": "🟢 Ready for Review",
  "score": 95,
  "changed_files_count": 3,
  "findings": {
    "security_issues": 0,
    "linting_issues": 2,
    "complexity_issues": 0,
    "tests_passed": true
  },
  "report": "# 🚦 PR Gatekeeper Report\n..."
}
```

## Recommendations

| Emoji | Status | Meaning |
|-------|--------|---------|
| 🟢 | Ready for Review | Score ≥ 80, no security issues, tests pass |
| 🔴 | Request Changes | Security issues OR tests fail |
| 🟡 | Needs Improvement | Score < 80, multiple quality issues |

## What Gets Scanned

### Tools Run (on changed files only)
1. **Bandit** - Security vulnerabilities
2. **Ruff** - Code quality and linting
3. **Radon** - Cyclomatic complexity

### Test Execution
- **When**: If `run_tests=True` AND `score > 80`
- **Command**: `pytest -x --tb=short -q`
- **Timeout**: 120 seconds
- **Environment**: Uses project's venv if available

## Scoring

```python
score = 100
score -= min(security_issues × 5, 30)    # Max -30
score -= min(linting_issues × 2, 20)     # Max -20
score -= min(complexity_issues × 3, 15)  # Max -15
```

## Speed Comparison

| Changed Files | Full Audit | PR Gatekeeper | Speedup |
|---------------|-----------|---------------|---------|
| 3 files | 45s | 8s | **5.6x** |
| 10 files | 45s | 15s | **3x** |
| 50 files | 45s | 35s | **1.3x** |

## Common Scenarios

### Scenario 1: Clean PR
```
Changed: 3 files
Security: ✅ 0 issues
Linting: ✅ 0 issues
Complexity: ✅ 0 issues
Tests: ✅ PASSED

→ 🟢 Ready for Review (Score: 100)
```

### Scenario 2: Minor Issues
```
Changed: 5 files
Security: ✅ 0 issues
Linting: ⚠️ 3 issues
Complexity: ⚠️ 1 function
Tests: ✅ PASSED

→ 🟢 Ready for Review (Score: 88)
Note: Minor linting issues (non-blocking)
```

### Scenario 3: Security Issue
```
Changed: 2 files
Security: ❌ 1 issue (hardcoded password)
Linting: ✅ 0 issues
Complexity: ✅ 0 issues
Tests: Not run (blocking issue)

→ 🔴 Request Changes (Score: 95)
Reason: Security vulnerability detected
```

### Scenario 4: Tests Fail
```
Changed: 4 files
Security: ✅ 0 issues
Linting: ✅ 0 issues
Complexity: ✅ 0 issues
Tests: ❌ FAILED

→ 🔴 Request Changes (Score: 100)
Reason: Tests failing (logic regression)
```

### Scenario 5: Low Quality
```
Changed: 8 files
Security: ✅ 0 issues
Linting: ⚠️ 15 issues
Complexity: ⚠️ 5 functions
Tests: Not run (score too low)

→ 🟡 Needs Improvement (Score: 55)
Reason: Multiple quality issues
```

## Troubleshooting

### "No Python changes detected"
✅ **Expected** - No `.py` files modified in this branch

### "Git diff failed"
❌ **Issue** - Not a git repo or base branch doesn't exist  
🔧 **Fix** - Ensure you're in a git repository

### "Tests timed out"
⚠️ **Issue** - Test suite takes > 120s  
🔧 **Fix** - Set `run_tests=False` or optimize tests

### Score seems low
💡 **Tip** - Score is based on changed files only. Run full audit on base branch to see inherited issues.

## Best Practices

### ✅ Do
- Use in CI/CD pipelines for fast feedback
- Keep `run_tests=True` for critical PRs
- Review the markdown report for context
- Compare against stable branch (main/master)

### ❌ Don't
- Use for initial project setup (use full audit)
- Skip tests on production-critical PRs
- Ignore "minor" linting issues (they accumulate)
- Use on non-git repositories

## CI/CD Integration

### GitHub Actions (Minimal)
```yaml
- name: PR Audit
  run: |
    pip install bandit ruff radon pytest
    python test_pr_gatekeeper.py
```

### GitLab CI (Minimal)
```yaml
pr_audit:
  script:
    - pip install bandit ruff radon pytest
    - python test_pr_gatekeeper.py
```

## Files

| File | Purpose |
|------|---------|
| `mcp_fastmcp_server.py` | Implementation (lines 1677-2039) |
| `docs/PR_GATEKEEPER_GUIDE.md` | Comprehensive guide |
| `test_pr_gatekeeper.py` | Test/demo script |
| `README.md` | Updated with PR Gatekeeper info |

## Related Tools

- **Full Audit** - Comprehensive scan of entire codebase
- **Auto-Fix** - Automated code cleanup
- **Architecture Review** - Dependency visualization

## Version

**v1.0** - Released 2026-01-14

---

**📚 Full Documentation**: See `docs/PR_GATEKEEPER_GUIDE.md`  
**🧪 Test Script**: Run `python test_pr_gatekeeper.py`  
**💬 Support**: Check troubleshooting section above
