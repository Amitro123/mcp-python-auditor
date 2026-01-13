# Changes Tracker

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
