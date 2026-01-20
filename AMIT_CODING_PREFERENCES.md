# AMIT CODING PREFERENCES v1.0.0

## Session: 2026-01-20 - Fix CI Runner Bandit Check
### Learned
✅ Approved: `subprocess.run(f"{cmd} {args}", shell=True)` → Pattern: When using `shell=True`, pass the command as a single string to ensure arguments are passed to the command, not the shell, especially on POSIX systems.
✅ Approved: Verify Function Signatures → Pattern: When calling internal logic functions (like `_audit_pr_changes_logic`), ensure keyword arguments match the latest definition.
