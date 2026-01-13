# Project Audit: 
**Score:** 59.0/100 → **Target: 90/100** (via 3 fixes)

## 📊 Tool Execution Summary

| Tool | Status | Details |
|------|--------|----------|
| 📁 Structure | ℹ️ Info | 105 files, 0 dirs |
| 🏗️ Architecture | ⚠️ Issues | 2 issue(s) found |
| 📝 Type Coverage | ✅ Pass | Type checking complete |
| 🧮 Complexity | ✅ Pass | No high-complexity functions |
| 🎭 Duplication | ⚠️ Issues | 39 duplicate(s) found |
| ☠️ Dead Code | ✅ Pass | No dead code detected |
| ⚡ Efficiency | ⚠️ Issues | 9 issue(s) found |
| 🧹 Cleanup | ℹ️ Info | 3 item(s), 2.6MB |
| 🔐 Secrets | ✅ Pass | No secrets detected |
| 🔒 Security (Bandit) | ✅ Pass | Scanned 0 files, 0 issues |
| ✅ Tests | ℹ️ Info | 4 test files, 10% coverage |
| 📋 Gitignore | ℹ️ Info | 4 suggestion(s) |
| 📝 Git Status | ℹ️ Info | Uncommitted changes, 0 days since commit |

## 🔧 SELF-HEALING STATUS

**Dependency Health:** 80%
**Missing:** detect-secrets

👉 **One-Command Fix:**
```bash
pip install detect-secrets
```

## 🚨 TOP 3 PRIORITY FIXES

├── **1. Architecture: Create routers/models/** (+15 points)
│   └── Centralize endpoints and Pydantic models to improve modularity.
├── **2. Duplicates: Cleanup app\core\report_generator.py** (+8 points)
│   └── Extract factory methods for 24 redundant segments.

---

## 📁 CLEAN STRUCTURE (Actionable)
```
├── 📁 app/
│   ├── 📁 agents/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 analyzer_agent.py
│   ├── 📁 core/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 base_tool.py
│   │   ├── 🐍 config.py
│   │   ├── 🐍 fix_orchestrator.py
│   │   ├── 🐍 report_generator.py
│   │   ├── 📄 report_generator.py.bak
│   │   ├── 🐍 report_sections.py
│   │   ├── 🐍 self_healing.py
│   │   ├── 🐍 subprocess_wrapper.py
│   │   └── 🐍 tool_registry.py
│   ├── 📁 tools/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 architecture_tool.py
│   │   ├── 🐍 cleanup_tool.py
│   │   ├── 📄 cleanup_tool.py.bak
│   │   ├── 🐍 code_editor_tool.py
│   │   ├── 🐍 complexity_tool.py
│   │   ├── 🐍 deadcode_tool.py
│   │   ├── 🐍 duplication_tool.py
│   │   ├── 🐍 efficiency_tool.py
│   │   ├── 🐍 git_tool.py
│   │   ├── 🐍 gitignore_tool.py
│   │   ├── 🐍 secrets_tool.py
│   │   ├── 🐍 security_tool.py
│   │   ├── 🐍 structure_tool.py
│   │   ├── 🐍 tests_tool.py
│   │   └── 🐍 typing_tool.py
│   ├── 🐍 __init__.py
│   ├── 🐍 main.py
│   ├── 📄 main.py.bak
│   └── 🐍 schemas.py
├── 📁 data/
│   ├── 📄 audit_dataset.jsonl
│   ├── 📄 audit_dataset_500.jsonl
│   ├── 📄 audit_dataset_fixed.jsonl
│   └── 📝 README_DATASET.md
├── 📁 finetune/
│   ├── 🐍 fix_notebook.py
│   └── 📄 kaggle_finetune.ipynb
├── 📁 reports/
│   ├── 📝 audit__20260112_085618.md
│   ├── 📝 audit__20260112_085711.md
│   ├── 📝 audit__20260112_085841.md
│   ├── 📝 audit__20260112_090507.md
│   ├── 📝 audit__20260112_091917.md
│   ├── 📝 audit__20260112_092230.md
│   ├── 📝 audit__20260112_092715.md
│   ├── 📝 audit__20260112_092933.md
│   ├── 📝 audit__20260112_093232.md
│   ├── 📝 audit__20260112_094020.md
│   ├── 📝 audit__20260112_094633.md
│   ├── 📝 audit__20260112_095024.md
│   ├── 📝 audit__20260112_095414.md
│   ├── 📝 audit__20260112_095747.md
│   ├── 📝 audit__20260112_100440.md
│   ├── 📝 audit_test_project3_20260112_084826.md
│   ├── 📝 audit_test_project3_20260112_084934.md
│   ├── 📝 audit_test_project3_20260112_085850.md
│   ├── 📝 audit_test_project3_20260112_090514.md
│   ├── 📝 audit_test_project3_20260112_091925.md
│   ├── 📝 audit_test_project3_20260112_092236.md
│   ├── 📝 audit_test_project3_20260112_092722.md
│   ├── 📝 audit_test_project3_20260112_092940.md
│   ├── 📝 audit_test_project3_20260112_093238.md
│   ├── 📝 audit_test_project3_20260112_094027.md
│   ├── 📝 audit_test_project3_20260112_094640.md
│   ├── 📝 audit_test_project3_20260112_095031.md
│   ├── 📝 audit_test_project3_20260112_095421.md
│   ├── 📝 audit_test_project3_20260112_095754.md
│   └── 📝 audit_test_project3_20260112_100446.md
├── 📁 tests/
│   ├── 🐍 __init__.py
│   ├── 🐍 conftest.py
│   ├── 🐍 test_analyzer_agent.py
│   ├── 🐍 test_api.py
│   ├── 🐍 test_parallel_audit.py
│   └── 🐍 test_tools.py
├── 📝 AMIT_CODING_PREFERENCES.md
├── 📄 audit.yaml.example
├── 📝 AUTOFIX_GUIDE.md
├── 📝 AUTOFIX_QUICK_REF.md
├── 📝 BEFORE_AFTER_COMPARISON.md
├── 📝 CENTRALIZED_EXCLUSIONS_COMPLETE.md
├── 📝 CHANGES_TRACKER.md
├── 🐍 dataset_templates.py
├── 🐍 demo_autofix.py
├── ⚙️ docker-compose.yml
├── 📄 Dockerfile
├── 📝 FULL_VISIBILITY_REFACTOR.md
├── 📝 IMPLEMENTATION_SUMMARY.md
├── 📝 INTEGRATION_GUIDE.md
├── 📝 MCP_INTEGRATION.md
├── 🐍 mcp_server.py
├── 📝 PRODUCTION_REFINEMENTS.md
├── ⚙️ pyproject.toml
├── 📝 QUICK_MCP_SETUP.md
├── 📝 QUICK_REFERENCE_GUIDE.md
├── 📝 README.md
├── 📄 requirements.txt
├── 🐍 self_audit.py
├── 📄 self_audit.py.bak
├── 📝 SELF_AUDIT_REPORT.md
├── 📝 SESSION_SUMMARY.md
├── 📝 SMART_ROOT_DETECTION.md
├── 📝 SMART_ROOT_VISUAL_COMPARISON.md
└── 🐍 validate_dataset.py
```
*Focusing on 80% code density zones. Filtered docs/, reports/, and scripts/ for clarity.*

## 🔒 Security Analysis (Bandit)

✅ **Security Scan Complete:** No known vulnerabilities found in 0 scanned files.

## 🎭 DUPLICATES (Grouped + Actionable)
- **app\core\report_generator.py** → 12 funcs (heavy redundancy)
  👉 **Fix:** Extract common helper or factory methods
  - `_get_architecture_status / _get_efficiency_status` (93% match)
  - `_get_complexity_status / _get_efficiency_status` (87% match)
- **tests\test_tools.py** → 11 funcs (heavy redundancy)
  👉 **Fix:** Extract `test_event_factory()` or common test helpers
  - `test_architecture_tool / test_efficiency_tool` (93% match)
  - `test_duplication_tool / test_efficiency_tool` (87% match)
- **app\tools\git_tool.py** → 10 funcs (heavy redundancy)
  👉 **Fix:** Extract common helper or factory methods
  - `_get_commit_hash / _get_commit_author` (96% match)
  - `_get_commit_author / _get_commit_date` (96% match)
- **tests\test_analyzer_agent.py** → 1 funcs (heavy redundancy)
  👉 **Fix:** Extract `test_event_factory()` or common test helpers
  - `analyzer` (100% match)
- **app\core\tool_registry.py** → 1 funcs (heavy redundancy)
  👉 **Fix:** Extract common helper or factory methods
  - `enable_tool / disable_tool` (95% match)

*...and 4 other files*

## ☠️ Dead Code Detection

✅ **Clean:** No dead code detected. All functions and imports are used.

## 🧹 CLEANUP READY COMMANDS
```bash
rm -rf cache_group  # cache_group: 2.3MB
rm -rf cache_group  # cache_group: 0.3MB
rm -rf cache_group  # cache_group: 0.0MB
```
**Total: 2.6MB → 0MB**

**Example Paths:**

## 📝 RECENT CHANGES

**Last Commit:** `aef479b` - Amit Rosen, 14 hours ago
*"Merge fix/mcp-auto-repair: Full Visibility Mode + Smart Root Detection"*

**Status:** ⚠️ Uncommitted changes
**Branch:** main

## ✅ TESTS

**Files Found:** 4 (glob test_*.py, *_test.py)
**Coverage:** 10% 

**Test Types:**
- Unit: ✅ (4 files)
- Integration: ❌ (0 files)
- E2E: ❌ (0 files)

*Note: 4 test files found via glob. Run `pytest --collect-only` to see executable tests.*

## 🔐 Secrets Detection

✅ **Clean:** No potential secrets or credentials detected in codebase.

## 📋 Gitignore Analysis

ℹ️ **4 recommendation(s):**

```gitignore
.dockerignore
.mypy_cache/
.ruff_cache/
data/
```

---

## 🔍 Technical Details

## 🏗️ Architecture Issues (2)

🟡 **No routers/ directory in FastAPI app**
   - Consider organizing endpoints in routers/

🟡 **No models/ or schemas/ directory**
   - Consider separating Pydantic models

## 🏷️ Type Hint Coverage: 57.4% (Grade: D)

- Fully typed: 62/108 functions
- Partially typed: 6 functions
- Untyped: 40 functions

**Examples of untyped functions:**
- `dataset_templates.py:generate_security_example()`
- `dataset_templates.py:generate_architecture_example()`
- `dataset_templates.py:generate_deadcode_example()`
- `demo_autofix.py:main()`
- `mcp_server.py:__init__()`

## ⚡ Efficiency Issues (9)

- **string_concatenation** in `app\core\report_generator.py:148`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `app\core\report_generator.py:148`
  - String concatenation in loop - consider using list and join()

- **nested_loops** in `app\tools\architecture_tool.py:192`
  - Nested loops at depth 3 - consider optimization

- **nested_loops** in `app\tools\architecture_tool.py:198`
  - Nested loops at depth 3 - consider optimization

- **string_concatenation** in `app\tools\cleanup_tool.py:85`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `app\tools\cleanup_tool.py:86`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `app\tools\cleanup_tool.py:85`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `app\tools\cleanup_tool.py:86`
  - String concatenation in loop - consider using list and join()

- **nested_loops** in `app\tools\efficiency_tool.py:136`
  - Nested loops at depth 3 - consider optimization

## 🔄 Complexity & Maintainability

**Maintainability Index:** 61.0/100 (Grade: B)
**Average Complexity:** 4.9

**⚠️ Very High Complexity (>15):** 12
- `self_audit.py:run_self_audit()` - CC: 16
- `validate_dataset.py:validate_dataset()` - CC: 23
- `app\agents\analyzer_agent.py:_calculate_score()` - CC: 21
- `app\agents\analyzer_agent.py:analyze_project()` - CC: 18
- `app\core\report_generator.py:_write_top_issues_summary()` - CC: 18

*...and 7 more*

**High Complexity (>10):** 21
- `self_audit.py:run_self_audit()` - CC: 16
- `validate_dataset.py:validate_dataset()` - CC: 23
- `app\agents\analyzer_agent.py:_calculate_score()` - CC: 21
- `app\agents\analyzer_agent.py:analyze_project()` - CC: 18
- `app\core\report_generator.py:_write_top_issues_summary()` - CC: 18

*...and 16 more*

