# Project Audit: 
**Score:** 63.599999999999994/100 → **Target: 90/100** (via 3 fixes)

## 📊 Tool Execution Summary

| Tool | Status | Details |
|------|--------|----------|
| 📁 Structure | ℹ️ Info | 107 files, 0 dirs |
| 🏗️ Architecture | ⚠️ Issues | 2 issue(s) found |
| 📝 Type Coverage | ✅ Pass | Type checking complete |
| 🧮 Complexity | ✅ Pass | No high-complexity functions |
| 🎭 Duplication | ⚠️ Issues | 86 duplicate(s) found |
| ☠️ Dead Code | ⚠️ Issues | 0 funcs, 3 imports |
| ⚡ Efficiency | ⚠️ Issues | 10 issue(s) found |
| 🧹 Cleanup | ℹ️ Info | 3 item(s), 3.3MB |
| 🔐 Secrets | ✅ Pass | No secrets detected |
| 🔒 Security (Bandit) | ⚠️ Issues | 20 vulnerability(ies) in 7838 files |
| ✅ Tests | ℹ️ Info | 17 test files, 43% coverage |
| 📋 Gitignore | ℹ️ Info | 3 suggestion(s) |
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
├── **2. Types: 139 untyped funcs** (+12 points)
│   └── Add type hints to core logic to prevent runtime errors.
├── **3. Duplicates: Cleanup tests\unit\test_scoring.py** (+8 points)
│   └── Extract factory methods for 31 redundant segments.

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
│   │   ├── 🐍 report_sections.py
│   │   ├── 🐍 self_healing.py
│   │   ├── 🐍 subprocess_wrapper.py
│   │   └── 🐍 tool_registry.py
│   ├── 📁 tools/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 architecture_tool.py
│   │   ├── 🐍 cleanup_tool.py
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
│   └── 🐍 schemas.py
├── 📁 backups/
│   ├── 📄 auto_fix_backup_20260113_142555.zip
│   ├── 📄 debug_audit.txt
│   └── 📝 FIX_LOG.md
├── 📁 docs/
│   ├── 📝 AMIT_CODING_PREFERENCES.md
│   ├── 📝 AUTOFIX_GUIDE.md
│   ├── 📝 AUTOFIX_QUICK_REF.md
│   ├── 📝 BEFORE_AFTER_COMPARISON.md
│   ├── 📝 CENTRALIZED_EXCLUSIONS_COMPLETE.md
│   ├── 📝 CHANGES_TRACKER.md
│   ├── 📝 FULL_VISIBILITY_REFACTOR.md
│   ├── 📝 IMPLEMENTATION_SUMMARY.md
│   ├── 📝 INTEGRATION_GUIDE.md
│   ├── 📝 MCP_INTEGRATION.md
│   ├── 📝 MCP_USER_GUIDE.md
│   ├── 📝 PR_GATEKEEPER_GUIDE.md
│   ├── 📝 PR_GATEKEEPER_QUICK_REF.md
│   ├── 📝 PRODUCTION_REFINEMENTS.md
│   ├── 📝 QUICK_MCP_SETUP.md
│   ├── 📝 QUICK_REFERENCE_GUIDE.md
│   ├── 📝 REMOTE_AUDIT_GUIDE.md
│   ├── 📝 SELF_AUDIT_REPORT.md
│   ├── 📝 SESSION_SUMMARY.md
│   ├── 📝 SMART_ROOT_DETECTION.md
│   └── 📝 SMART_ROOT_VISUAL_COMPARISON.md
├── 📁 reports/
│   ├── 📝 audit_test_project3_20260114_114232.md
│   ├── 📝 audit_test_project3_20260114_121221.md
│   ├── 📝 audit_test_project3_20260114_121520.md
│   ├── 📝 FULL_AUDIT_7581b7b8.md
│   ├── 📝 FULL_AUDIT_a22e14f8.md
│   └── 📝 FULL_AUDIT_dd6b709c.md
├── 📁 tests/
│   ├── 📁 e2e/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 test_audit_workflows.py
│   ├── 📁 integration/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 test_tools_integration.py
│   ├── 📁 mcp/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 test_mcp_server.py
│   ├── 📁 tools/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 test_individual_tools.py
│   ├── 📁 unit/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 test_dependencies.py
│   │   ├── 🐍 test_scoring.py
│   │   └── 🐍 test_venv_exclusion.py
│   ├── 🐍 __init__.py
│   ├── 🐍 conftest.py
│   ├── 📝 README.md
│   ├── 🐍 test_analyzer_agent.py
│   ├── 🐍 test_api.py
│   ├── 🐍 test_parallel_audit.py
│   ├── 🐍 test_pr_gatekeeper.py
│   ├── 🐍 test_remote_audit.py
│   ├── 🐍 test_tool_fixes.py
│   └── 🐍 test_tools.py
├── 📄 audit.yaml.example
├── 📝 CHANGES_TRACKER.md
├── 🐍 dataset_templates.py
├── 📄 debug_audit.txt
├── 🐍 demo_autofix.py
├── ⚙️ docker-compose.yml
├── 📄 Dockerfile
├── 📝 IMPLEMENTATION_COMPLETE.md
├── 🐍 mcp_fastmcp_server.py
├── 🐍 mcp_server.py
├── ⚙️ pyproject.toml
├── 📝 README.md
├── 📝 README_UPDATES.md
├── 📄 requirements.txt
├── 📝 ROADMAP.md
├── 📝 ROADMAP_AND_REMOTE_AUDIT_COMPLETE.md
├── 🐍 run_tests.py
├── 🐍 self_audit.py
├── 📝 SESSION_SUMMARY.md
├── 🐍 test_direct.py
├── 🐍 test_mcp_tools.py
├── 🐍 test_pr_gatekeeper.py
├── 📝 TEST_SUMMARY.md
└── 🐍 verify_tools.py
```
*Focusing on 80% code density zones. Filtered docs/, reports/, and scripts/ for clarity.*

## 🔒 Security Analysis (Bandit)

⚠️ **20 security issue(s) found in 7838 files:**

🔵 **LOW**: B404 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\core\self_healing.py:2`
   - Consider possible security implications associated with the subprocess module.

🔵 **LOW**: B404 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\core\subprocess_wrapper.py:2`
   - Consider possible security implications associated with the subprocess module.

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\core\subprocess_wrapper.py:43`
   - subprocess call - check for execution of untrusted input.

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\core\subprocess_wrapper.py:71`
   - subprocess call - check for execution of untrusted input.

🟡 **MEDIUM**: B104 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\main.py:278`
   - Possible binding to all interfaces.

🔵 **LOW**: B110 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\tools\architecture_tool.py:240`
   - Try, Except, Pass detected.

🔵 **LOW**: B110 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\tools\cleanup_tool.py:160`
   - Try, Except, Pass detected.

🔵 **LOW**: B110 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\tools\cleanup_tool.py:162`
   - Try, Except, Pass detected.

🔵 **LOW**: B404 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\tools\deadcode_tool.py:8`
   - Consider possible security implications associated with the subprocess module.

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor\mcp-python-auditor\app\tools\deadcode_tool.py:48`
   - subprocess call - check for execution of untrusted input.

*...and 10 more issues*

## 🎭 DUPLICATES (Grouped + Actionable)
- **tests\test_remote_audit.py** → 15 funcs (heavy redundancy)
  👉 **Fix:** Extract `test_event_factory()` or common test helpers
  - `track_temp_dir` (100% match)
  - `__exit__` (100% match)
- **tests\unit\test_scoring.py** → 15 funcs (heavy redundancy)
  👉 **Fix:** Extract `test_event_factory()` or common test helpers
  - `test_security_penalty / test_secrets_penalty` (94% match)
  - `test_duplicates_penalty / test_secrets_penalty` (91% match)
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

*...and 12 other files*

## ☠️ Dead Code Detection

⚠️ **6 dead code item(s) found:**

**Unused Imports (3):**
- `app\core\report_generator.py`
- `app\main.py`
- `tests\test_remote_audit.py`

## 🧹 CLEANUP READY COMMANDS
```bash
rm -rf cache_group  # cache_group: 2.6MB
rm -rf cache_group  # cache_group: 0.7MB
rm -rf cache_group  # cache_group: 0.0MB
```
**Total: 3.3MB → 0MB**

**Example Paths:**

## 📝 RECENT CHANGES

**Last Commit:** `cdcac11` - Amit Rosen, 13 hours ago
*"fix: Resolve virtual environment scanning issues (Verified)"*

**Status:** ⚠️ Uncommitted changes
**Branch:** main

## ✅ TESTS

**Files Found:** 17 (glob test_*.py, *_test.py)
**Coverage:** 43% 

**Test Types:**
- Unit: ✅ (3 files)
- Integration: ✅ (1 files)
- E2E: ✅ (1 files)

*Note: 17 test files found via glob. Run `pytest --collect-only` to see executable tests.*

## 🔐 Secrets Detection

✅ **Clean:** No potential secrets or credentials detected in codebase.

## 📋 Gitignore Analysis

ℹ️ **3 recommendation(s):**

```gitignore
.dockerignore
.mypy_cache/
.ruff_cache/
```

---

## 🔍 Technical Details

## 🏗️ Architecture Issues (2)

🟡 **No routers/ directory in FastAPI app**
   - Consider organizing endpoints in routers/

🟡 **No models/ or schemas/ directory**
   - Consider separating Pydantic models

## 🏷️ Type Hint Coverage: 38.8% (Grade: F)

- Fully typed: 92/237 functions
- Partially typed: 6 functions
- Untyped: 139 functions

**Examples of untyped functions:**
- `dataset_templates.py:generate_security_example()`
- `dataset_templates.py:generate_architecture_example()`
- `dataset_templates.py:generate_deadcode_example()`
- `demo_autofix.py:main()`
- `mcp_fastmcp_server.py:log()`

## ⚡ Efficiency Issues (10)

- **nested_loops** in `mcp_fastmcp_server.py:838`
  - Nested loops at depth 3 - consider optimization

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

**Maintainability Index:** 65.9/100 (Grade: B)
**Average Complexity:** 5.0

**⚠️ Very High Complexity (>15):** 21
- `mcp_fastmcp_server.py:audit_pr_changes()` - CC: 51
- `mcp_fastmcp_server.py:generate_full_markdown_report()` - CC: 40
- `mcp_fastmcp_server.py:run_architecture_visualizer()` - CC: 26
- `mcp_fastmcp_server.py:run_tests_coverage()` - CC: 23
- `mcp_fastmcp_server.py:run_auto_fix()` - CC: 22

*...and 16 more*

**High Complexity (>10):** 38
- `mcp_fastmcp_server.py:audit_pr_changes()` - CC: 51
- `mcp_fastmcp_server.py:generate_full_markdown_report()` - CC: 40
- `mcp_fastmcp_server.py:run_architecture_visualizer()` - CC: 26
- `mcp_fastmcp_server.py:run_tests_coverage()` - CC: 23
- `mcp_fastmcp_server.py:run_auto_fix()` - CC: 22

*...and 33 more*

