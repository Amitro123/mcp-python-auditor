# Git-Native File Discovery Implementation

## Summary

Successfully implemented Git-native file discovery to eliminate `.venv` noise and ensure the Integrity Validator runs correctly.

## Changes Made

### 1. **Git-Native File Discovery** (`app/core/file_discovery.py`)
- **Primary Method**: Uses `git ls-files --cached --others --exclude-standard` to get files
  - Inherently respects `.gitignore` (no `.venv`, nested repos, etc.)
  - Returns absolute paths of Python files only
- **Fallback Method**: Strict `os.walk` with hardcoded exclusions
  - Skips directories: `.venv`, `venv`, `node_modules`, `__pycache__`, etc.
  - Only used when not in a Git repository

### 2. **Tool Refactoring** (Explicit File Lists)
Modified the following tools to accept `file_list` parameter:

#### `app/tools/security_tool.py` (Bandit)
- Accepts `file_list: List[str] = None`
- When provided: Passes files directly to Bandit (no `-r` flag)
- Fallback: Uses directory-based scanning with exclusions

#### `app/tools/complexity_tool.py` (Radon)
- Accepts `file_list` in `analyze()` method
- Passes to `_get_cyclomatic_complexity()` and `_get_maintainability_index()`
- When provided: Passes files directly to Radon
- Fallback: Uses directory scanning with `-i` exclusions

#### `app/tools/duplication_tool.py`
- Accepts `file_list` in `analyze()` method
- Passes to `_extract_functions()`
- When provided: Converts to Path objects and processes
- Fallback: Uses `walk_project_files()` from BaseTool

#### `app/tools/deadcode_tool.py` (Vulture)
- Accepts `file_list` in `analyze()` method
- When provided: Passes files directly to Vulture
- Fallback: Uses directory scanning with `--exclude` flags

### 3. **Integrity Validator** (`app/core/audit_validator.py`)
- **Function**: `validate_report_integrity(report_content, scanned_files)`
- **Checks**:
  - Verifies no `.venv` or `site-packages` files were scanned
  - Reports total file count
  - Confirms scan method (Git-Native vs Fallback)
- **Output**: Markdown section appended to report

### 4. **Analyzer Agent Integration** (`app/agents/analyzer_agent.py`)
- Added imports for `get_project_files` and `validate_report_integrity`
- **Execution Flow**:
  1. Calls `get_project_files(path)` to get file list
  2. Logs discovered file count
  3. Passes `scanned_files` to tools that support it:
     - `security`, `complexity`, `duplication`, `deadcode`
  4. Passes `scanned_files` to report generator

### 5. **Report Generator Integration** (`app/core/report_generator.py`)
- Added `scanned_files: List[str] = None` parameter
- **Post-Generation**:
  1. Reads generated report
  2. Calls `validate_report_integrity()`
  3. Appends validation section to report
  4. Logs verification confirmation

## Execution Flow

```
┌─────────────────────────────────────┐
│ 1. get_project_files(root_path)    │
│    ├─ Try: git ls-files *.py       │
│    └─ Fallback: os.walk (strict)   │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 2. Pass file_list to tools          │
│    ├─ run_bandit(file_list)         │
│    ├─ run_radon(file_list)          │
│    ├─ run_duplication(file_list)    │
│    └─ run_vulture(file_list)        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 3. Generate main report             │
│    └─ All tool results compiled     │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 4. validate_report_integrity()      │
│    ├─ Check for .venv leaks         │
│    ├─ Verify file count             │
│    └─ Generate validation section   │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│ 5. Append validation to report      │
│    └─ Save final report to disk     │
└─────────────────────────────────────┘
```

## Benefits

1. **No More .venv Leaks**: Git-native discovery inherently excludes gitignored files
2. **No Duplicates**: Git tracks files once, preventing nested repo issues
3. **Explicit Control**: Tools receive exact file lists, can't "escape" to scan unwanted directories
4. **Validation**: Integrity check confirms no leaks occurred
5. **Fallback Safety**: Strict os.walk ensures functionality even without Git

## Testing

To verify the implementation:

```bash
# Run a self-audit
python self_audit.py

# Check the generated report for:
# 1. "Integrity Check" section at the end
# 2. "Files Scanned" count matches discovered files
# 3. No warnings about .venv leaks
```

## Files Modified

- ✅ `app/core/file_discovery.py` (NEW)
- ✅ `app/core/audit_validator.py` (NEW)
- ✅ `app/agents/analyzer_agent.py`
- ✅ `app/core/report_generator.py`
- ✅ `app/tools/security_tool.py`
- ✅ `app/tools/complexity_tool.py`
- ✅ `app/tools/duplication_tool.py`
- ✅ `app/tools/deadcode_tool.py`

## Next Steps

1. Run `python self_audit.py` to test the implementation
2. Verify the "Integrity Check" section appears in the report
3. Confirm no `.venv` files are being scanned
4. Check that Bandit shows correct file counts
