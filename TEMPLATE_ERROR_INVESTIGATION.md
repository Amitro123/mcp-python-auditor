# Report Template Error - Investigation Summary

## Issue

The audit report is not reflecting the correct project because the Jinja2 template is failing with:

```
'builtin_function_or_method' object is not subscriptable
```

This causes the system to fall back to the legacy report generator, which produces a different format.

## Root Cause Analysis

The error `'builtin_function_or_method' object is not subscriptable` means that somewhere in the code, we're trying to use bracket notation `[]` on a function/method object instead of calling it first.

### Possible Causes:

1. **Method Reference Instead of Call**: Passing `obj.get` instead of `obj.get()`
2. **Template Accessing Wrong Type**: Template trying to access a method as if it were a dict
3. **Context Building Error**: Error in `build_report_context()` or normalization functions

## Fixes Applied

### 1. ✅ Better Error Logging
**File**: `mcp_fastmcp_server.py` (Lines 1548-1554)

Added full traceback logging to catch the exact error:

```python
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    log(f"[Job {job_id}] Jinja2 failed, using legacy generator: {e}")
    log(f"[Job {job_id}] Full error traceback:\n{error_details}")
```

**Result**: Next audit will show the exact line and function where the error occurs.

### 2. ✅ Fixed Bandit Files Scanned (from previous fix)
**File**: `mcp_fastmcp_server.py` (Lines 372-387)

Fixed the calculation of `files_scanned` for Bandit.

### 3. ✅ Fixed Git Tool NoneType Error (from previous fix)
**File**: `app/tools/git_tool.py` (Lines 137-149)

Added None check for `result.stdout`.

## Next Steps

### To Debug the Template Error:

1. **Run a new audit** to get the full traceback:
   ```
   Via Claude: "Run a full audit on this project"
   ```

2. **Check the debug log** at:
   ```
   c:\Users\USER\.gemini\antigravity\scratch\mcp-python-auditor\debug_audit.txt
   ```

3. **Look for the traceback** that shows:
   - Which template line is failing
   - Which variable is causing the issue
   - The full call stack

### Expected Traceback Format:

```
[Job xxx] Full error traceback:
Traceback (most recent call last):
  File "...", line X, in generate_report
    report_content = template.render(**context)
  File "...", line Y, in render
    ...
  File "...", line Z, in template
    {{ some_variable[key] }}
TypeError: 'builtin_function_or_method' object is not subscriptable
```

This will tell us exactly which variable in the template is the problem.

## Likely Culprits

Based on the template (`audit_report_v3.md.j2`), these lines are most likely to cause issues:

1. **Line 14**: `{{ security.total_issues }}` - if `security` is not properly normalized
2. **Line 47**: `{{ tests.coverage_percent }}` - if `tests` is not a dict
3. **Line 54-56**: `{{ tests.test_breakdown.unit }}` - if `test_breakdown` is missing
4. **Line 198-200**: `{{ cleanup.cleanup_targets.items() }}` - if `cleanup_targets` is not a dict

## Temporary Workaround

The legacy generator is working, so reports are still being generated. They just use the old format instead of the new Jinja2 template.

## Status

⏳ **Waiting for next audit run** to get the full traceback and identify the exact cause.

Once we have the traceback, we can:
1. Fix the specific variable/function that's being passed incorrectly
2. Add defensive checks in the normalization functions
3. Update the template to handle edge cases

---

**Files Modified**:
- `mcp_fastmcp_server.py` - Added better error logging
- `app/tools/git_tool.py` - Fixed NoneType error (previous fix)
- `mcp_fastmcp_server.py` - Fixed Bandit files_scanned (previous fix)
