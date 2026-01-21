# AMIT CODING PREFERENCES v1.1.0

## Session: 2026-01-20 - Fix CI Runner Bandit Check
### Learned
✅ Approved: `subprocess.run(f"{cmd} {args}", shell=True)` → Pattern: When using `shell=True`, pass the command as a single string to ensure arguments are passed to the command, not the shell, especially on POSIX systems.
✅ Approved: Verify Function Signatures → Pattern: When calling internal logic functions (like `_audit_pr_changes_logic`), ensure keyword arguments match the latest definition.

## Session: 2026-01-21 - Fix Remote Audit & Reporting
### Learned
❌ Rejected: `subprocess.run(..., check=True)` in complex logic → Reason: Makes intermediate error handling (like checking stderr for specific git messages) difficult and complicates test mocking.
✅ Approved: `subprocess.run(..., check=False)` + explicit returncode check → Pattern: Allows granular error parsing (e.g. distinguishing authentication fail vs repo not found) and simpler mock side_effects.
✅ Approved: Defensive `Path(x).name` → Pattern: Always wrap file path access in try/except or type check when processing tool results (like Bandit/Radon) which might return dicts or be None.
❌ Rejected: Raw data access in Jinja2 templates (`{{ raw_results.tool.attr }}`) → Reason: Fragile when tools are optional or fail. Raises UndefinedError. Use normalized context instead.
✅ Approved: Normalized Context for Reporting → Pattern: Middleware layer (`report_context.py`) that guarantees default values and structure before rendering templates.
✅ Approved: Robust Status Lists in Tests → Pattern: When asserting status (e.g. `assert status in valid_list`), ensure list covers all possible states (e.g. `cleanup_available`, `not_a_repo`).
