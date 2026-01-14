# Changes Tracker

## [2026-01-14] Safety-First Execution Engine

### 🎯 Goal
Replace flaky recursive scanning with robust **Git-Native Discovery** and **Windows Chunking** to eliminate `WinError 206` and prevent accidentally scanning ignored directories like `.venv`.

### 📝 Changes
- **New `app/core/command_chunker.py`**:
    - Implemented `run_tool_in_chunks` to split huge file lists into batches of 50.
    - Built-in JSON result merging from multiple chunks.
    - Added guard clauses (`filter_python_files`, `validate_file_list`).

- **New `app/core/file_discovery.py`**:
    - Implemented `get_project_files` strategy:
        1. Primary: `git ls-files` (Fast, respects .gitignore).
        2. Fallback: Strict `os.walk` with hardcoded exclusions.

- **Refactored Tools**:
    - **`security_tool.py`**: Now accepts `file_list`, uses chunking.
    - **`complexity_tool.py`**: Now accepts `file_list`.
    - **`duplication_tool.py`**: Now accepts `file_list`.
    - **`deadcode_tool.py`**: Now accepts `file_list`, uses chunking.

- **Updated `mcp_server.py`**:
    - Individual tools (e.g., `run_security`) now use the Safety-First engine instead of unguided recursion.

### 🧪 Verification
- **Test Suite**: Created `test_safety_first.py` (4/4 passed).
- **MCP E2E**: Created `test_mcp_e2e.py` confirming individual tool execution works via MCP.
- **Self-Audit**: Verified accurate file counts (63 files) and zero `.venv` leaks.

### ✅ Status
- [x] Code implemented
- [x] Verified with test suite
- [x] Verified with self-audit
- [x] Verified with MCP E2E test
- [x] Ready for production

---

## [2026-01-14] PR Gatekeeper & Remote Audit (v2.3/v2.4)

### 🎯 Goal
Enable delta-based auditing for Pull Requests (faster, focused) and auditing of remote Git repositories without manual cloning.

### 📝 Changes
- **New `mcp_fastmcp_server.py` Tools**:
    - `audit_pr_changes`: Scans only changed files vs main branch.
    - `audit_remote_repo`: Clone -> Audit -> Clean workflow.
- **New Helpers**:
    - `get_changed_files`: Uses `git diff` to find delta.
- **Documentation**:
    - Created `PR_GATEKEEPER_GUIDE.md` and `REMOTE_AUDIT_GUIDE.md`.

---

## [2026-01-12] Centralized Exclusion Logic Implementation

### 🎯 Goal
Eliminate false positives and performance issues caused by tools scanning ignored directories (venv, site-packages, node_modules, etc.) by implementing a strict, centralized exclusion mechanism.

### 📝 Changes
- **Modified `app/core/base_tool.py`**:
    - Added `IGNORED_DIRECTORIES` constant containing a comprehensive blacklist.
    - Added `walk_project_files(root, extension)` helper method that strictly filters directories *during* iteration (modifying `dirs` in-place).
    - Updated `validate_path` to check against `IGNORED_DIRECTORIES`.

- **Updated `app/core/config.py`**:
    - Refactored to import `ANALYSIS_EXCLUDES` from `BaseTool.IGNORED_DIRECTORIES` to ensure a single source of truth.

- **Refactored Tools to use Centralized Logic**:
    - **`efficiency_tool.py`**: Replaced manual `rglob` with `self.walk_project_files()`.
    - **`typing_tool.py`**: Replaced manual `rglob` with `self.walk_project_files()`.
    - **`architecture_tool.py`**: Replaced 3 separate `rglob` calls with `self.walk_project_files()`.
    - **`duplication_tool.py`**: Replaced `rglob` with `self.walk_project_files()` and removed unused import.
    - **`structure_tool.py`**: Updated to use `self.IGNORED_DIRECTORIES` for filtering tree generation and file counts.
    - **`cleanup_tool.py`**: Updated logic to detect cache files *before* filtering them from recursion, ensuring correct reporting without traversing ignored directories.
    - **`deadcode_tool.py`**: Updated `vulture` subprocess command to explicitly pass `--exclude` arguments for all ignored directories.

### 🧪 Verification
- **Internal Test**: Created and successfully ran `verify_exclusions.py`.
- **Unit Tests**: All tests passed (`pytest`), including `test_cleanup_tool` which confirmed correct cache detection logic.
- **Result**: `walk_project_files` correctly identifies source files while strictly ignoring external libraries and environments.
- **Impact**: Audit tools are now significantly faster and free of noise from external libraries.

### ✅ Status
- [x] Code implemented
- [x] Verified with test script
- [x] Verified with pytest
- [x] Ready for production audit
