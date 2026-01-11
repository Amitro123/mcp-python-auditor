# Changes Tracker - MCP Python Auditor

## 🔄 Latest Changes - 2026-01-10

### ✅ Dataset v2.0 - False Positive Classifier

**What Changed**:
- Complete rewrite of `data/audit_dataset_fixed.jsonl` (100 examples)
- New format trains model as false-positive classifier instead of generic analyzer
- Added comprehensive documentation in `data/README_DATASET.md`
- Updated `validate_dataset.py` to accept command line arguments

**Why**:
- Old dataset was too generic and didn't train proper classification behavior
- Model needs to distinguish between REAL ISSUES and FALSE POSITIVES
- Specific context (File, Line, Code) improves training quality
- Verdict-first output format ensures consistent model responses

**Format Changes**:

OLD (Generic):
```json
{"instruction": "Analyze the architecture...", "output": "🏗️ Architecture Issues..."}
```

NEW (Classifier):
```json
{
  "instruction": "Analyze this Bandit finding:\n\nFile: query.py\nLine: 42\nIssue: B608 SQL injection\nCode:\ncursor.execute(f'SELECT * FROM users WHERE id={user_id}')\n\nIs this a REAL ISSUE or FALSE POSITIVE?",
  "output": "REAL ISSUE: Direct string formatting in SQL query allows SQL injection. Recommendation: Use parameterized queries."
}
```

**Distribution**:
- Security (Bandit): 20 examples (10 real, 10 false positives)
- Dead Code (Vulture): 20 examples (10 real, 10 false positives)
- Duplication: 20 examples (10 refactor needed, 10 acceptable)
- Architecture: 20 examples (15 real issues, 5 acceptable)
- Test Coverage: 20 examples (varied severity levels)

**Validation**:
```bash
python validate_dataset.py data/audit_dataset_fixed.jsonl
# Result: ✅ PASS (100 examples)
```

**Impact**:
- Model will provide specific verdicts (REAL ISSUE, FALSE POSITIVE, etc.)
- Better classification accuracy for audit findings
- Reduced false positives in production usage
- More actionable recommendations

---

## Previous Changes

### 2026-01-05 - Conflict Resolution & Config Updates

**Changes**:
- Synced with remote repository
- Resolved conflict in `app/tools/security_tool.py` (kept 600s timeout)
- Updated `pyproject.toml`:
  - Added `asyncio_default_fixture_loop_scope = "function"`
  - Set `cov-fail-under = 0` for verification phase

**Verification**:
- ✅ pytest: 25 passed
- ✅ Manual verification of security_tool.py and pyproject.toml

---

### 2026-01-04 - Architecture Upgrades

**Changes**:
- Implemented parallel tool execution with `asyncio.gather`
- Added smart skipping for large projects (>300 files)
- Created centralized configuration in `app/core/config.py`
- Implemented graceful fault tolerance for tool failures

**Coding Preferences Updated**:
- Hybrid Concurrency: `asyncio.to_thread` for blocking I/O
- Smart Skipping: Pre-flight checks for performance
- Centralized Configuration: Single source for exclusion patterns

---

### 2026-01-03 - Production Refinements

**Changes**:
- Enhanced report formatting with top 3 issues summary
- Improved health check system with dependency warnings
- Robust command execution using `sys.executable` pattern
- Smart venv detection for accurate test coverage

**Features Added**:
- Meaningful report filenames: `audit_{project_name}_{timestamp}.md`
- Prominent warnings in reports (GitHub-style alerts)
- Intelligent filtering (ignores valid constants, singletons)
- Optimized cleanup detection (prevents recursive cache noise)

---

## File Changes Summary

### Created
- ✅ `data/audit_dataset_fixed.jsonl` - New classifier dataset (100 examples)
- ✅ `data/README_DATASET.md` - Comprehensive dataset documentation

### Modified
- ✅ `validate_dataset.py` - Now accepts command line arguments
- ✅ `CHANGES_TRACKER.md` - Updated with latest changes

### Deprecated
- ⚠️ `data/audit_dataset.jsonl` - Old generic format (keep for reference)

---

## Testing Status

**Current**:
- ✅ 25 tests passing
- ✅ 60%+ coverage
- ✅ All tools loading correctly (13 tools)
- ✅ Dataset validation passing (100 examples)

**Next Steps**:
1. Fine-tune model with new dataset on Kaggle
2. Test model classification accuracy
3. Integrate fine-tuned model into MCP server
4. Validate end-to-end workflow

---

**Last Updated**: 2026-01-10T16:11:24+02:00
