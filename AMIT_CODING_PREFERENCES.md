# AMIT CODING PREFERENCES v1.2
Session: 2026-01-04 - Architecture Upgrades (Parallelism + Exclusions + Centralized Config)
Learned:
- Graduated phases + tests [memory:56]
- Docker/.env/FastAPI standards
- React full-stack compatibility
- **Hybrid Concurrency for Tooling**: Use `asyncio.to_thread` for tools involving blocking I/O (like subprocesses) when orchestrating them in an `async` main loop.
- **Smart Skipping**: Implement pre-flight checks to skip computationally expensive tools on large datasets (>300 files).
- **Graceful Fault Tolerance**: Wrap parallel tasks in exception handlers to ensure partial results are still delivered even if some tools fail.
- **Strict Exclusion Patterns**: Security scanning tools (detect-secrets, bandit) MUST exclude `node_modules`, build artifacts (`dist`, `build`), minified files (`*.min.js`), and lock files to prevent massive timeouts on mixed-language projects.
- **Centralized Configuration**: Create a single source of truth for all exclusion patterns. Use helper functions to convert to different formats (comma-separated, regex) as needed by different CLI tools.

## Approved Patterns
✅ **Parallelism**: `asyncio.gather(*[asyncio.to_thread(func, *args) for item in list])` for CPU/IO bound tasks in async contexts.
✅ **Pre-Flight Heuristics**: Project size counting (`rglob('*.py')` with exclusions) to adjust workload dynamically.
✅ **Robust Summaries**: Explicitly calling out skipped or failed components in the final user-facing summary string.
✅ **Security Tool Exclusions**: Always use `--exclude-files` with patterns like `node_modules/.*`, `dist/.*`, `.*\.min\.js` for detect-secrets, and comma-separated exclusions for bandit.
✅ **Centralized Config**: Define `ANALYSIS_EXCLUDES` and `CLEANUP_EXCLUDES` in a central config module. Create helper functions like `get_analysis_excludes_comma()` and `get_analysis_excludes_regex()` for different tool formats.
✅ **Security Timeouts**: Set timeouts to 600s (10 min) for analysis tools to handle large/complex projects.
