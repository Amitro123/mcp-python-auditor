# Code Review: Python Auditor Project

**Date:** 2026-05-24
**Reviewer:** Jules (AI Software Engineer)
**Target:** `mcp-python-auditor`

## 1. Executive Summary

The project implements a sophisticated Model Context Protocol (MCP) server for auditing Python projects. It features a rich set of analysis tools (security, quality, structure, testing) and supports advanced features like "Safety-First" auditing, incremental audits, and PR gatekeeping.

However, the codebase suffers from significant **technical debt** due to code duplication and a monolithic server entry point (`mcp_fastmcp_server.py`). The core logic is split between a structured `app/` directory and ad-hoc implementations within the server script. This makes maintenance difficult and increases the risk of inconsistencies (e.g., different exclusion rules for different tools).

## 2. Architecture & Design

### 2.1 The "God Object" Problem
The file `mcp_fastmcp_server.py` is an anti-pattern. It currently handles:
- MCP Server configuration
- Tool execution orchestration
- Background job management
- Report generation (both legacy text manipulation and Jinja2)
- Direct implementation of tool logic (shadowing `app/tools/`)
- Caching logic (partially)

**Recommendation:**
Refactor `mcp_fastmcp_server.py` to be a thin orchestration layer. It should only:
1. Initialize the MCP server.
2. Dispatch requests to dedicated Controllers or Agents.
3. Return results.
Business logic should reside entirely in `app/core` and `app/tools`.

### 2.2 Incomplete Migration to `app/tools`
The project appears to be in the middle of a refactoring that wasn't completed.
- **Exists:** `app/tools/structure_tool.py`, `app/tools/tests_tool.py`, `app/tools/fast_audit_tool.py`.
- **Ignored:** `mcp_fastmcp_server.py` re-implements the logic for these tools in local functions like `run_structure`, `run_tests_coverage`, `run_ruff`.

**Impact:**
- `StructureTool` in `app/tools` has robust file icon logic and centralized exclusions. `run_structure` in the server has a hardcoded list of exclusions and different tree generation logic.
- `TestsTool` has robust regex for coverage parsing. `run_tests_coverage` in the server has a simpler, potentially brittle implementation.

## 3. Code Quality & Standards

### 3.1 Code Duplication
| Feature | `mcp_fastmcp_server.py` Implementation | `app/tools/` Implementation | Status |
|---------|----------------------------------------|-----------------------------|--------|
| Structure Analysis | `run_structure` | `StructureTool` | **Duplicate** |
| Test Analysis | `run_tests_coverage` | `TestsTool` | **Duplicate** |
| Ruff/Linting | `run_ruff`, `run_ruff_comprehensive` | `FastAuditTool` | **Duplicate** |
| Git Info | `run_git_info` | `GitTool` | **Duplicate** |
| Secrets | `run_secrets` | `SecretsTool` | **Duplicate** |

**Recommendation:**
Delete the local functions in `mcp_fastmcp_server.py` and strictly use the classes from `app/tools/`.

### 3.2 Error Handling
- **Generic Exception Handling:** The server uses `except Exception as e` extensively. While this prevents the server from crashing, it often masks the root cause of errors.
- **Logging:** The `log()` function writes to a debug file and `stderr`. Use the standard Python `logging` module configured properly for the application.

### 3.3 Security & Subprocess
- **Subprocess Usage:** The project mostly follows `shell=False` and passes lists of arguments, which is good (complies with Bandit B602).
- **Paths:** `check_path_sanity` provides basic checks, but `subprocess.run` calls should ensure `cwd` is strictly controlled to prevent path traversal issues if arguments are dynamic (though here they seem mostly static or derived from the target path).

### 3.4 Global State
- `JOBS` dictionary is a global variable in `mcp_fastmcp_server.py`. This is not thread-safe (though FastMCP might be async single-threaded, it's bad practice).
- **Recommendation:** Encapsulate job management in a `JobManager` class in `app/core/job_manager.py`.

## 4. Documentation Consistency

### 4.1 README vs Code
- **README** claims: "Ruff Comprehensive: Single tool replaces 6+ linters".
- **Code:** `mcp_fastmcp_server.py` still runs `run_bandit` separately in `run_audit_background`, even though `run_ruff_comprehensive` (and `FastAuditTool`) is supposed to cover security (`S` rules).
- **Impact:** The audit runs Bandit twice (once via `bandit` CLI, once via `ruff` if configured), or worse, provides inconsistent results if one is updated and the other isn't.

### 4.2 Coding Preferences
- `AMIT_CODING_PREFERENCES.md` is generally followed regarding `subprocess` usage (list of args).
- **Verification:** `mcp_fastmcp_server.py` generally uses `check=False` (default) and checks `returncode` manually or ignores it (for tools that return non-zero on issues), which aligns with the preferences.

## 5. Critical Issues & Bugs

1.  **Duplicate Execution:** In `run_audit_background`, the server calls:
    ```python
    async def run_efficiency_cached():
        # ...
        result = await asyncio.to_thread(run_efficiency, target)
    ```
    And `run_efficiency` calls `FastAuditTool().analyze(target)`.
    Meanwhile, `run_ruff` is also called. `FastAuditTool` *is* a Ruff wrapper.
    So Ruff is likely running multiple times with slightly different configurations.

2.  **Hardcoded Exclusions:**
    `run_structure` has a hardcoded set: `exclude_dirs_lower`.
    `get_relevant_files` has a hardcoded `universal_excludes`.
    `app/core/base_tool.py` (assumed) likely has another set.
    **Risk:** A user adding a directory to `.gitignore` or configuring exclusions might find it ignored by some tools but respected by others.

## 6. Action Plan

1.  **Refactor Server:** Rewrite `mcp_fastmcp_server.py` to instantiate and use `app/tools` classes.
2.  **Unify Logic:** Move any unique logic from server functions (like specific parsing logic) into the respective Tool classes if it's missing.
3.  **Centralize Configuration:** Ensure all tools use a single source of truth for file exclusion (e.g., `FileFilter` class mentioned in README but seemingly unused in some server functions).
4.  **Job Management:** Extract `JOBS` and background task logic to `app/core`.
5.  **Logging:** Replace custom `log()` with `logging`.

## 7. Conclusion

The `mcp-python-auditor` is a feature-rich project but is currently in a "split-brain" state. The implementation of tools is duplicated between the main script and the `app/tools` modules. Prioritizing the refactoring of `mcp_fastmcp_server.py` to use the `app/tools` architecture is critical for future maintainability and reliability.
