## 📊 Tool Execution Summary

| Tool | Status | Details |
|------|--------|----------|
| 📁 Structure | ℹ️ Info | 268 files, 0 dirs |
| 🏗️ Architecture | ⚠️ Issues | 2 issue(s) found |
| 📝 Type Coverage | ✅ Pass | Type checking complete |
| 🧮 Complexity | ✅ Pass | No high-complexity functions |
| 🎭 Duplication | ✅ Pass | No code duplication found |
| ☠️ Dead Code | ⚠️ Issues | 0 funcs, 3 imports |
| ⚡ Efficiency | ⚠️ Issues | 23 issue(s) found |
| 🧹 Cleanup | ℹ️ Info | 4 item(s), 4.7MB |
| 🔐 Secrets | ✅ Pass | No secrets detected |
| 🔒 Security (Bandit) | ⚠️ Issues | 20 vulnerability(ies) in 63 files |
| ✅ Tests | ℹ️ Info | 69 test files, 12% coverage |
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
├── **2. Types: 250 untyped funcs** (+12 points)
│   └── Add type hints to core logic to prevent runtime errors.

---

## 📁 CLEAN STRUCTURE (Actionable)
```
├── 📁 app/
│   ├── 📁 agents/
│   │   ├── 🐍 __init__.py
│   │   └── 🐍 analyzer_agent.py
│   ├── 📁 core/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 audit_validator.py
│   │   ├── 🐍 base_tool.py
│   │   ├── 🐍 command_chunker.py
│   │   ├── 🐍 config.py
│   │   ├── 🐍 file_discovery.py
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
├── 📁 backups/
│   ├── 📄 auto_fix_backup_20260113_142555.zip
│   ├── 📄 debug_audit.txt
│   └── 📝 FIX_LOG.md
├── 📁 data/
│   ├── 📄 audit_dataset.jsonl
│   ├── 📄 audit_dataset_500.jsonl
│   ├── 📄 audit_dataset_fixed.jsonl
│   └── 📝 README_DATASET.md
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
│   ├── 📝 PRODUCTION_REFINEMENTS.md
│   ├── 📝 QUICK_MCP_SETUP.md
│   ├── 📝 QUICK_REFERENCE_GUIDE.md
│   ├── 📝 SELF_AUDIT_REPORT.md
│   ├── 📝 SESSION_SUMMARY.md
│   ├── 📝 SMART_ROOT_DETECTION.md
│   └── 📝 SMART_ROOT_VISUAL_COMPARISON.md
├── 📁 finetune/
│   ├── 🐍 fix_notebook.py
│   └── 📄 kaggle_finetune.ipynb
├── 📁 mcp-python-auditor/
│   ├── 📁 app/
│   │   ├── 📁 agents/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 analyzer_agent.py
│   │   ├── 📁 core/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 base_tool.py
│   │   │   ├── 🐍 config.py
│   │   │   ├── 🐍 fix_orchestrator.py
│   │   │   ├── 🐍 report_generator.py
│   │   │   ├── 🐍 report_sections.py
│   │   │   ├── 🐍 self_healing.py
│   │   │   ├── 🐍 subprocess_wrapper.py
│   │   │   └── 🐍 tool_registry.py
│   │   ├── 📁 tools/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 architecture_tool.py
│   │   │   ├── 🐍 cleanup_tool.py
│   │   │   ├── 🐍 code_editor_tool.py
│   │   │   ├── 🐍 complexity_tool.py
│   │   │   ├── 🐍 deadcode_tool.py
│   │   │   ├── 🐍 duplication_tool.py
│   │   │   ├── 🐍 efficiency_tool.py
│   │   │   ├── 🐍 git_tool.py
│   │   │   ├── 🐍 gitignore_tool.py
│   │   │   ├── 🐍 secrets_tool.py
│   │   │   ├── 🐍 security_tool.py
│   │   │   ├── 🐍 structure_tool.py
│   │   │   ├── 🐍 tests_tool.py
│   │   │   └── 🐍 typing_tool.py
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 main.py
│   │   └── 🐍 schemas.py
│   ├── 📁 backups/
│   │   ├── 📄 auto_fix_backup_20260113_142555.zip
│   │   ├── 📄 debug_audit.txt
│   │   └── 📝 FIX_LOG.md
│   ├── 📁 docs/
│   │   ├── 📝 AMIT_CODING_PREFERENCES.md
│   │   ├── 📝 AUTOFIX_GUIDE.md
│   │   ├── 📝 AUTOFIX_QUICK_REF.md
│   │   ├── 📝 BEFORE_AFTER_COMPARISON.md
│   │   ├── 📝 CENTRALIZED_EXCLUSIONS_COMPLETE.md
│   │   ├── 📝 CHANGES_TRACKER.md
│   │   ├── 📝 FULL_VISIBILITY_REFACTOR.md
│   │   ├── 📝 IMPLEMENTATION_SUMMARY.md
│   │   ├── 📝 INTEGRATION_GUIDE.md
│   │   ├── 📝 MCP_INTEGRATION.md
│   │   ├── 📝 MCP_USER_GUIDE.md
│   │   ├── 📝 PR_GATEKEEPER_GUIDE.md
│   │   ├── 📝 PR_GATEKEEPER_QUICK_REF.md
│   │   ├── 📝 PRODUCTION_REFINEMENTS.md
│   │   ├── 📝 QUICK_MCP_SETUP.md
│   │   ├── 📝 QUICK_REFERENCE_GUIDE.md
│   │   ├── 📝 REMOTE_AUDIT_GUIDE.md
│   │   ├── 📝 SELF_AUDIT_REPORT.md
│   │   ├── 📝 SESSION_SUMMARY.md
│   │   ├── 📝 SMART_ROOT_DETECTION.md
│   │   └── 📝 SMART_ROOT_VISUAL_COMPARISON.md
│   ├── 📁 reports/
│   │   ├── 📝 audit__20260114_122109.md
│   │   ├── 📝 audit_test_project3_20260114_114232.md
│   │   ├── 📝 audit_test_project3_20260114_121221.md
│   │   ├── 📝 audit_test_project3_20260114_121520.md
│   │   ├── 📝 audit_test_project3_20260114_122140.md
│   │   ├── 📝 audit_test_project3_20260114_122442.md
│   │   ├── 📝 audit_test_project3_20260114_123520.md
│   │   ├── 📝 audit_test_project3_20260114_123528.md
│   │   ├── 📝 audit_test_project3_20260114_132026.md
│   │   ├── 📝 audit_test_project3_20260114_132244.md
│   │   ├── 📝 audit_test_project3_20260114_143343.md
│   │   ├── 📝 FULL_AUDIT_111432ab.md
│   │   ├── 📝 FULL_AUDIT_202cb856.md
│   │   ├── 📝 FULL_AUDIT_2178a9c4.md
│   │   ├── 📝 FULL_AUDIT_6376f435.md
│   │   ├── 📝 FULL_AUDIT_7581b7b8.md
│   │   ├── 📝 FULL_AUDIT_813c8c79.md
│   │   ├── 📝 FULL_AUDIT_95217a6c.md
│   │   ├── 📝 FULL_AUDIT_a22e14f8.md
│   │   ├── 📝 FULL_AUDIT_d82d95f1.md
│   │   ├── 📝 FULL_AUDIT_dd6b709c.md
│   │   ├── 📝 FULL_AUDIT_f3ab53cb.md
│   │   └── 📝 FULL_AUDIT_fa2f153b.md
│   ├── 📁 tests/
│   │   ├── 📁 e2e/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 test_audit_workflows.py
│   │   ├── 📁 integration/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 test_tools_integration.py
│   │   ├── 📁 mcp/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 test_mcp_server.py
│   │   ├── 📁 tools/
│   │   │   ├── 🐍 __init__.py
│   │   │   └── 🐍 test_individual_tools.py
│   │   ├── 📁 unit/
│   │   │   ├── 🐍 __init__.py
│   │   │   ├── 🐍 test_dependencies.py
│   │   │   ├── 🐍 test_scoring.py
│   │   │   └── 🐍 test_venv_exclusion.py
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 conftest.py
│   │   ├── 🐍 debug_remote_tool.py
│   │   ├── 📝 README.md
│   │   ├── 🐍 test_analyzer_agent.py
│   │   ├── 🐍 test_api.py
│   │   ├── 🐍 test_parallel_audit.py
│   │   ├── 🐍 test_pr_gatekeeper.py
│   │   ├── 🐍 test_remote_audit.py
│   │   ├── 🐍 test_tool_fixes.py
│   │   └── 🐍 test_tools.py
│   ├── 📄 all_tests_report.txt
│   ├── 📄 audit.yaml.example
│   ├── 📝 AUDIT_ACCURACY_ANALYSIS.md
│   ├── 📝 CHANGES_TRACKER.md
│   ├── 🐍 dataset_templates.py
│   ├── 📄 debug_audit.txt
│   ├── 🐍 demo_autofix.py
│   ├── ⚙️ docker-compose.yml
│   ├── 📄 Dockerfile
│   ├── 📝 GIT_PUSH_SUMMARY.md
│   ├── 📝 HOW_TO_AVOID_INACCURATE_AUDITS.md
│   ├── 📝 HOW_TO_FIX_AUDIT_FAILURES.md
│   ├── 📝 IMPLEMENTATION_COMPLETE.md
│   ├── 🐍 mcp_fastmcp_server.py
│   ├── 🐍 mcp_server.py
│   ├── ⚙️ pyproject.toml
│   ├── 📝 README.md
│   ├── 📝 README_UPDATES.md
│   ├── 📄 requirements.txt
│   ├── 📝 ROADMAP.md
│   ├── 📝 ROADMAP_AND_REMOTE_AUDIT_COMPLETE.md
│   ├── 🐍 run_tests.py
│   ├── 🐍 self_audit.py
│   ├── 📝 SELF_AUDIT_REPORT.md
│   ├── 📝 SESSION_SUMMARY.md
│   ├── 🐍 test_direct.py
│   ├── 📄 test_failure.txt
│   ├── 📄 test_failure_v2.txt
│   ├── 📄 test_failure_v3.txt
│   ├── 🐍 test_mcp_tools.py
│   ├── 🐍 test_pr_gatekeeper.py
│   ├── 📝 TEST_REPORTING_GAP_EXPLAINED.md
│   ├── 📝 TEST_SUMMARY.md
│   └── 🐍 verify_tools.py
├── 📁 reports/
│   ├── 📝 audit__20260114_194019.md
│   ├── 📝 audit_test_project3_20260113_224213.md
│   ├── 📝 audit_test_project3_20260113_225120.md
│   ├── 📝 FULL_AUDIT_163eecf1.md
│   ├── 📝 FULL_AUDIT_30573dc9.md
│   ├── 📝 FULL_AUDIT_34b8d3bc.md
│   ├── 📝 FULL_AUDIT_4bdf91d9.md
│   ├── 📝 FULL_AUDIT_b2c95374.md
│   ├── 📝 FULL_AUDIT_c048b749.md
│   └── 📝 FULL_AUDIT_e9d71a3d.md
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
│   ├── 🐍 test_tool_fixes.py
│   └── 🐍 test_tools.py
├── 📄 audit.yaml.example
├── 🐍 dataset_templates.py
├── 📄 debug_audit.txt
├── 🐍 demo_autofix.py
├── ⚙️ docker-compose.yml
├── 📄 Dockerfile
├── 📝 GIT_NATIVE_IMPLEMENTATION.md
├── 🐍 mcp_fastmcp_server.py
├── 🐍 mcp_server.py
├── 🐍 new_analyzers.py
├── ⚙️ pyproject.toml
├── ⚙️ pytest.ini
├── 📝 README.md
├── 📄 requirements.txt
├── 🐍 run_tests.py
├── 📝 SAFETY_FIRST_IMPLEMENTATION.md
├── 🐍 self_audit.py
├── 📄 self_audit.py.bak
├── 📝 SELF_AUDIT_REPORT.md
├── 🐍 test_direct.py
├── 🐍 test_mcp_tools.py
├── 🐍 test_safety_first.py
├── 📄 uv.lock
└── 🐍 verify_tools.py
```
*Focusing on 80% code density zones. Filtered docs/, reports/, and scripts/ for clarity.*

## 🔒 Security Analysis (Bandit)

⚠️ **20 security issue(s) found in 63 files:**

🔵 **LOW**: B404 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\command_chunker.py:6`
   - Consider possible security implications associated with the subprocess module.

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\command_chunker.py:51`
   - subprocess call - check for execution of untrusted input.

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\command_chunker.py:67`
   - subprocess call - check for execution of untrusted input.

🔵 **LOW**: B404 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\file_discovery.py:2`
   - Consider possible security implications associated with the subprocess module.

🔵 **LOW**: B607 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\file_discovery.py:52`
   - Starting a process with a partial executable path

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\file_discovery.py:52`
   - subprocess call - check for execution of untrusted input.

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\file_discovery.py:67`
   - subprocess call - check for execution of untrusted input.

🔵 **LOW**: B404 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\self_healing.py:2`
   - Consider possible security implications associated with the subprocess module.

🔵 **LOW**: B404 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\subprocess_wrapper.py:2`
   - Consider possible security implications associated with the subprocess module.

🔵 **LOW**: B603 in `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\subprocess_wrapper.py:43`
   - subprocess call - check for execution of untrusted input.

*...and 10 more issues*

## 🎭 DUPLICATES (Grouped + Actionable)
✅ **Clean:** No significant code duplication found.

## ☠️ Dead Code Detection

⚠️ **6 dead code item(s) found:**

**Unused Imports (3):**
- `app\core\command_chunker.py`
- `app\core\report_generator.py`
- `app\main.py`

## 🧹 CLEANUP READY COMMANDS
```bash
rm -rf cache_group  # cache_group: 3.0MB
rm -rf cache_group  # cache_group: 1.7MB
rm -rf cache_group  # cache_group: 0.0MB
rm -rf cache_group  # cache_group: 0.0MB
```
**Total: 4.7MB → 0MB**

**Example Paths:**

## 📝 RECENT CHANGES

**Last Commit:** `cdcac11` - Amit Rosen, 21 hours ago
*"fix: Resolve virtual environment scanning issues (Verified)"*

**Status:** ⚠️ Uncommitted changes
**Branch:** main

## ✅ TESTS

**Files Found:** 69 (glob test_*.py, *_test.py)
**Coverage:** 12% 

**Test Types:**
- Unit: ✅ (6 files)
- Integration: ✅ (2 files)
- E2E: ✅ (2 files)

*Note: 69 test files found via glob. Run `pytest --collect-only` to see executable tests.*

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

## 🏷️ Type Hint Coverage: 41.5% (Grade: D)

- Fully typed: 187/451 functions
- Partially typed: 14 functions
- Untyped: 250 functions

**Examples of untyped functions:**
- `dataset_templates.py:generate_security_example()`
- `dataset_templates.py:generate_architecture_example()`
- `dataset_templates.py:generate_deadcode_example()`
- `demo_autofix.py:main()`
- `mcp_fastmcp_server.py:log()`

## ⚡ Efficiency Issues (23)

- **nested_loops** in `mcp_fastmcp_server.py:838`
  - Nested loops at depth 3 - consider optimization

- **string_concatenation** in `app\core\command_chunker.py:91`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `app\core\command_chunker.py:94`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `app\core\report_generator.py:170`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `app\core\report_generator.py:170`
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

- **nested_loops** in `mcp-python-auditor\mcp_fastmcp_server.py:838`
  - Nested loops at depth 3 - consider optimization

- **string_concatenation** in `mcp-python-auditor\app\core\report_generator.py:147`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `mcp-python-auditor\app\core\report_generator.py:147`
  - String concatenation in loop - consider using list and join()

- **nested_loops** in `mcp-python-auditor\app\tools\architecture_tool.py:192`
  - Nested loops at depth 3 - consider optimization

- **nested_loops** in `mcp-python-auditor\app\tools\architecture_tool.py:198`
  - Nested loops at depth 3 - consider optimization

- **string_concatenation** in `mcp-python-auditor\app\tools\cleanup_tool.py:85`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `mcp-python-auditor\app\tools\cleanup_tool.py:86`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `mcp-python-auditor\app\tools\cleanup_tool.py:85`
  - String concatenation in loop - consider using list and join()

- **string_concatenation** in `mcp-python-auditor\app\tools\cleanup_tool.py:86`
  - String concatenation in loop - consider using list and join()

- **nested_loops** in `mcp-python-auditor\app\tools\duplication_tool.py:84`
  - Nested loops at depth 3 - consider optimization

- **nested_loops** in `mcp-python-auditor\app\tools\efficiency_tool.py:136`
  - Nested loops at depth 3 - consider optimization

## 🔄 Complexity & Maintainability

**Maintainability Index:** 65.6/100 (Grade: B)
**Average Complexity:** 5.1

**⚠️ Very High Complexity (>15):** 19
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\new_analyzers.py:analyze_type_hints()` - CC: 28
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\agents\analyzer_agent.py:_calculate_score()` - CC: 21
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\agents\analyzer_agent.py:analyze_project()` - CC: 18
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\report_generator.py:_write_top_issues_summary()` - CC: 18
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\report_generator.py:_write_enterprise_tests()` - CC: 16

*...and 14 more*

**High Complexity (>10):** 36
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\core\command_chunker.py:run_tool_in_chunks()` - CC: 14
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\new_analyzers.py:analyze_type_hints()` - CC: 28
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\new_analyzers.py:analyze_architecture_issues()` - CC: 11
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\agents\analyzer_agent.py:_calculate_score()` - CC: 21
- `C:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\app\agents\analyzer_agent.py:analyze_project()` - CC: 18

*...and 31 more*


## 🛡️ Integrity Check

**Files Scanned:** 63
**Scan Method:** Git-Native (Primary) / Strict Allowlist (Fallback)

✅ **Verified:** No virtual environment leaks detected.
✅ **Verified:** Scan scope strictly limited to project source.
