"""
FastMCP Server for Python Auditor.

This exposes our audit tools via the Model Context Protocol (MCP),
allowing AI agents (Claude, GPT, etc.) to invoke them directly.

Run with: python mcp_fastmcp_server.py
Or: fastmcp run mcp_fastmcp_server.py
"""
from fastmcp import FastMCP
from pathlib import Path
import json
import sys
import time
import datetime
import asyncio
import uuid
import os
import ast
import re
import shutil
import subprocess
from typing import Dict, Any, List

# Import our internal tools
from app.tools.structure_tool import StructureTool
from app.tools.fast_audit_tool import FastAuditTool
from app.tools.secrets_tool import SecretsTool
from app.tools.tests_tool import TestsTool
from app.tools.deadcode_tool import DeadcodeTool
from app.tools.architecture_tool import ArchitectureTool
from app.tools.duplication_tool import DuplicationTool
from app.tools.gitignore_tool import GitignoreTool
from app.tools.git_tool import GitTool
from app.tools.typing_tool import TypingTool
from app.core.cache_manager import CacheManager
from app.core.incremental_engine import IncrementalEngine
# Trigger reload for report_context changes
from app.core.report_generator_v2 import ReportGeneratorV2
from app.core.scoring_engine import ScoringEngine

# Create the MCP Server
mcp = FastMCP("Python Auditor")

# Define reports directory
REPORTS_DIR = Path(__file__).parent / "reports"
DEBUG_LOG = Path(__file__).parent / "debug_audit.txt"

# GLOBAL STATE FOR BACKGROUND JOBS
JOBS: Dict[str, Any] = {}


def log(msg):
    """Writes logs to a file to bypass MCP stdout capture."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    
    # Write to file
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception:
        pass  # nosec B110

    # Also try writing to stderr (sometimes visible in console)
    print(log_msg, file=sys.stderr, flush=True)


def check_path_sanity(path: str) -> list:
    """Checks for common path issues before scanning."""
    warnings = []
    p = Path(path).resolve()
    
    # Check 1: Nested duplicate (e.g., automation-service/automation-service)
    nested_duplicate = p / p.name
    if nested_duplicate.exists() and nested_duplicate.is_dir():
        warnings.append(f"POTENTIAL CONFIG ERROR: Detected nested duplicate folder: '{p.name}/{p.name}'. Are you scanning the outer wrapper instead of the code?")
    
    # Check 2: No code found at all
    has_py_files = any(p.glob("*.py")) or any(p.glob("src/*.py")) or any(p.glob("app/*.py"))
    if not has_py_files:
        # Check deeper
        has_py_files = len(list(p.glob("**/*.py"))) > 0
    
    if not has_py_files:
        warnings.append("WARNING: No Python files found in the target directory. Check your path.")
    
    # Check 3: Path doesn't exist
    if not p.exists():
        warnings.append(f"ERROR: Path does not exist: {p}")
    
    return warnings


def ensure_dependencies() -> list:
    """
    STRICT VALIDATION: Verifies required tools are installed.
    Raises ValueError if tools are missing (NO auto-install).
    """
    REQUIRED_TOOLS = ["bandit", "ruff", "vulture", "radon", "pip-audit", "pytest", "detect-secrets"]
    missing = []
    
    for tool in REQUIRED_TOOLS:
        # Check PATH first
        if shutil.which(tool):
            continue
            
        # Check Python Module (more reliable on Windows)
        module_name = tool.replace("-", "_")
        try:
            # fast check with --version or --help
            subprocess.run(
                [sys.executable, "-m", module_name, "--version"],
                capture_output=True, check=True, timeout=5
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(tool)
    
    if missing:
        cmd = f"{sys.executable} -m pip install {' '.join(missing)}"
        error_msg = f"""
❌ MISSING DEVELOPMENT TOOLS
The following tools are required to run the audit but were not found:
{missing}

👉 Please run this command to install them:
{cmd}
"""
        # Raise error to stop execution
        raise ValueError(error_msg)
    
    return [] # Return empty list to maintain compatibility with report generator


# ============================================================
# SMART FILE FILTERING - Skip Irrelevant Files
# ============================================================

def get_relevant_files(project_path: Path, tool_name: str) -> List[Path]:
    """
    Get only relevant files for each tool.
    Massively speeds up analysis by skipping:
    - node_modules, .venv, venv, .git
    - frontend/, dist/, build/
    - test files (for some tools)
    - generated files
    """
    
    # Universal excludes
    universal_excludes = {
        'node_modules', '.venv', 'venv', 'env', '.git', 
        'dist', 'build', '__pycache__', '.pytest_cache',
        '.mypy_cache', '.ruff_cache', '.tox',
        'frontend', 'static', 'public', '.audit_cache'
    }
    
    # Tool-specific patterns
    tool_patterns = {
        'bandit': {
            'include': ['**/*.py'],
            'exclude': ['**/test_*.py', '**/*_test.py', '**/conftest.py'],
            'reason': 'Security checks on production code only'
        },
        'ruff': {
            'include': ['**/*.py'],
            'exclude': [],
            'reason': 'Check all Python files'
        },
        'tests': {
            'include': ['**/test_*.py', '**/*_test.py'],
            'exclude': [],
            'reason': 'Only test files'
        },
        'pip-audit': {
            'include': ['requirements.txt', 'pyproject.toml', 'setup.py'],
            'exclude': [],
            'reason': 'Only dependency files'
        },
        'deadcode': {
            'include': ['**/*.py'],
            'exclude': ['**/test_*.py', '**/*_test.py'],
            'reason': 'Production code only'
        }
    }
    
    config = tool_patterns.get(tool_name, {'include': ['**/*.py'], 'exclude': []})
    
    files = []
    
    for pattern in config['include']:
        for file in project_path.rglob(pattern):
            # Skip if in excluded directory
            if any(exc in file.parts for exc in universal_excludes):
                continue
            
            # Skip if matches exclude pattern
            if any(file.match(exc) for exc in config['exclude']):
                continue
            
            files.append(file)
    
    return files


# ============================================================
# COMPREHENSIVE RUFF - Replaces Multiple Tools
# ============================================================

def run_bandit(path: Path) -> dict:
    """Run Bandit security analysis using BanditTool."""
    from app.tools.bandit_tool import BanditTool
    tool = BanditTool()
    return tool.analyze(Path(path))


def run_secrets(path: Path) -> dict:
    """Run detect-secrets scan using SecretsTool."""
    from app.tools.secrets_tool import SecretsTool
    tool = SecretsTool()
    return tool.analyze(Path(path))


def run_ruff(path: Path) -> dict:
    """Run Ruff linter using FastAuditTool."""
    tool = FastAuditTool()
    return tool.analyze(Path(path))


def run_pip_audit(path: Path) -> dict:
    """Run pip-audit vulnerability scan using PipAuditTool."""
    from app.tools.pip_audit_tool import PipAuditTool
    tool = PipAuditTool()
    return tool.analyze(Path(path))


def run_structure(target: str) -> dict:
    """Analyze project structure using StructureTool."""
    tool = StructureTool()
    return tool.analyze(Path(target))


def run_dead_code(path: Path) -> dict:
    """Run Vulture for dead code detection using Safety-First engine."""
    try:
        from app.core.file_discovery import get_project_files
        from app.tools.deadcode_tool import DeadcodeTool
        
        target_path = Path(path).resolve()
        files = get_project_files(target_path)
        
        tool = DeadcodeTool()
        return tool.analyze(target_path, file_list=files)
    except Exception as e:
        return {"tool": "vulture", "status": "error", "error": str(e), "items": [], "total_dead_code": 0}


def run_efficiency(path: Path) -> dict:
    """Run FastAudit (Ruff) for complexity and performance checks."""
    tool = FastAuditTool()
    return tool.analyze(Path(path))


def run_duplication(path: Path) -> dict:
    """Run duplication detection using Safety-First engine."""
    try:
        from app.core.file_discovery import get_project_files
        from app.tools.duplication_tool import DuplicationTool
        
        target_path = Path(path).resolve()
        files = get_project_files(target_path)
        
        tool = DuplicationTool()
        return tool.analyze(target_path, file_list=files)
    except Exception as e:
        return {"tool": "duplication", "status": "error", "error": str(e)}


def run_git_info(path: Path) -> dict:
    """Get git repository information using GitTool."""
    tool = GitTool()
    return tool.analyze(Path(path))


def run_cleanup_scan(path: Path) -> dict:
    """Scan for cleanup opportunities using CleanupTool."""
    from app.tools.cleanup_tool import CleanupTool
    tool = CleanupTool()
    return tool.analyze(Path(path))


def run_tests_coverage(path: Path) -> dict:
    """Analyze tests using TestsTool."""
    tool = TestsTool()
    return tool.analyze(Path(path))


def run_architecture_visualizer(path: Path) -> dict:
    """Generate a Mermaid.js dependency graph using ArchitectureTool."""
    tool = ArchitectureTool()
    return tool.generate_dependency_graph(Path(path))


async def run_audit_background(job_id: str, path: str):
    """Run a full audit in the background using AuditOrchestrator."""
    from app.core.audit_orchestrator import AuditOrchestrator, create_default_tool_runners

    log(f"[Job {job_id}] Starting FULL AUDIT on {path}...")
    JOBS[job_id] = {"status": "running", "start_time": time.time()}

    target = Path(path).resolve()

    try:
        # Initialize orchestrator
        orchestrator = AuditOrchestrator(target, REPORTS_DIR)
        orchestrator.set_log_callback(lambda msg: log(f"[Job {job_id}] {msg}"))

        # Get default tool runners
        tool_runners = create_default_tool_runners(target)

        # Run audit
        result_dict = await orchestrator.run_full_audit(tool_runners, job_id)

        # Generate report
        report_path = orchestrator.generate_report(job_id, result_dict)

        # Calculate duration
        duration = f"{time.time() - JOBS[job_id]['start_time']:.2f}s"

        # Update job status
        JOBS[job_id] = {
            "status": "completed",
            "duration": duration,
            "report_path": str(report_path),
            "summary": f"{len(tool_runners)} tools completed. Report: {report_path.name}",
            "result": result_dict
        }
        log(f"[Job {job_id}] COMPLETED. Report saved to: {report_path}")

    except Exception as e:
        log(f"[Job {job_id}] FAILED: {e}")
        JOBS[job_id] = {"status": "failed", "error": str(e)}


def check_dependencies() -> list:
    """
    Check which required tools are missing (non-raising version of ensure_dependencies).
    Returns a list of missing tool names.
    """
    REQUIRED_TOOLS = ["bandit", "ruff", "vulture", "radon", "pip-audit", "pytest", "detect-secrets"]
    missing = []
    
    for tool in REQUIRED_TOOLS:
        if shutil.which(tool): continue
        try:
            subprocess.run(
                [sys.executable, "-m", tool.replace("-", "_"), "--version"],
                capture_output=True, check=True, timeout=5, stdin=subprocess.DEVNULL
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(tool)
    
    return missing


@mcp.tool()
def install_dependencies() -> str:
    """
    Install all required audit dependencies (bandit, detect-secrets, vulture, radon, ruff, pip-audit).
    Returns confirmation message or error.
    """
    TOOLS_TO_INSTALL = ["bandit", "detect-secrets", "vulture", "radon", "ruff", "pip-audit"]
    
    try:
        log("Installing audit dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + TOOLS_TO_INSTALL,
            capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL
        )
        
        if result.returncode == 0:
            log(f"✅ Successfully installed: {', '.join(TOOLS_TO_INSTALL)}")
            return f"✅ **Installation Successful!**\n\nInstalled tools: {', '.join(TOOLS_TO_INSTALL)}\n\nYou can now run the audit."
        else:
            return f"❌ **Installation Failed**\n\nError: {result.stderr or result.stdout}"
            
    except subprocess.TimeoutExpired:
        return "❌ **Installation Timeout** - Please try manually: `pip install bandit detect-secrets vulture radon ruff pip-audit`"
    except Exception as e:
        return f"❌ **Installation Error:** {str(e)}"


@mcp.tool()
async def start_full_audit(path: str) -> str:
    """Starts a FULL code audit (Security, Secrets, Quality, Dependencies) in the background."""
    # Check dependencies first (agentic flow)
    missing = check_dependencies()
    if missing:
        missing_list = ", ".join(missing)
        return f"""❌ **Missing Dependencies Detected:** {missing_list}

I cannot run the audit yet.
**Please ask the user:** "Essential audit tools are missing ({missing_list}). Would you like me to install them for you now?"

If the user says **Yes**, please call the `install_dependencies` tool, and then re-run the audit."""
    
    job_id = str(uuid.uuid4())[:8]  # Short ID
    
    # Sanity check the path first
    warnings = check_path_sanity(path)
    for w in warnings: log(f"[SANITY CHECK] {w}")
    
    log(f"=== STARTING FULL AUDIT JOB {job_id} for: {path} ===")
    
    # Fire and forget! We do not await this.
    asyncio.create_task(run_audit_background(job_id, path))
    
    response = {
        "status": "started",
        "job_id": job_id,
        "tools": ["Bandit (Security)", "Secrets", "Ruff (Quality)", "Pip-Audit (Dependencies)"],
        "message": "Full audit started. Use 'check_audit_status' with the job_id. Report auto-saves on completion."
    }
    
    if warnings: response["warnings"] = warnings
    
    return json.dumps(response, indent=2)


@mcp.tool()
def check_audit_status(job_id: str) -> str:
    """Checks the progress of a background audit job."""
    job = JOBS.get(job_id)
    if not job:
        return json.dumps({"status": "error", "message": f"Job ID '{job_id}' not found. Available jobs: {list(JOBS.keys())}"})
    
    if job["status"] == "running":
        elapsed = time.time() - job["start_time"]
        return json.dumps({
            "status": "running", 
            "elapsed_seconds": f"{elapsed:.1f}s",
            "message": "Still scanning... please wait and check again."
        })
    
    return json.dumps(job, indent=2)


def _auto_fix_dry_run(target: Path, files_to_delete: List[str]) -> str:
    """Generates the dry run report for auto-fix."""
    return json.dumps({
        "status": "dry_run",
        "message": "To apply these changes, run with confirm=True",
        "actions_planned": {
            "cleanup": f"Would delete {len(files_to_delete)} cache/build directories",
            "style_fix": "Would run 'ruff check --fix' and 'ruff format'",
            "backup": f"Would create backup zip in {target / '.backups'}",
            "git": f"Would create a new branch 'auto-fix-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}'"
        },
        "cleanup_details": files_to_delete[:10]
    }, indent=2)

def _auto_fix_execute(target: Path, files_to_delete: List[str]) -> str:
    """Executes the auto-fix operations."""
    fixes_applied = []
    errors = []
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = f"fix/audit-{timestamp}"
    backup_zip = None
    
    # 1. Backup
    try:
        backup_dir = target / ".backups"
        backup_dir.mkdir(exist_ok=True)
        backup_zip = backup_dir / f"backup_{timestamp}"
        shutil.make_archive(str(backup_zip), 'zip', str(target))
        fixes_applied.append(f"Backup created: {backup_zip}.zip")
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Backup failed: {e}. Aborting."})

    # 2. Cleanup
    deleted_count = 0
    for rel_path in files_to_delete:
        try:
            full_path = target / rel_path
            if full_path.exists():
                shutil.rmtree(full_path)
                deleted_count += 1
        except Exception as e:  # nosec B110 - cleanup failures are non-critical
            log(f"Cleanup: Could not delete {rel_path}: {e}")
    if deleted_count: fixes_applied.append(f"Cleanup: Deleted {deleted_count} cache directories")

    # 3. Style Fixes (Ruff)
    try:
        subprocess.run([sys.executable, "-m", "ruff", "check", ".", "--fix"], cwd=str(target), capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
        subprocess.run([sys.executable, "-m", "ruff", "format", "."], cwd=str(target), capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
        fixes_applied.append("Code Style: Ran 'ruff check --fix' and 'ruff format'")
    except Exception as e: errors.append(f"Ruff fix failed: {e}")

    # 4. Write Log & Commit
    try:
        log_file = target / "FIX_LOG.md"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n## Auto-Fix {timestamp}\n")
            for fix in fixes_applied: f.write(f"- {fix}\n")
            if errors:
                f.write(f"\n**Errors:**\n")
                for err in errors: f.write(f"- {err}\n")

        git_kwargs = {"cwd": str(target), "capture_output": True, "timeout": 30, "stdin": subprocess.DEVNULL}
        subprocess.run(["git", "checkout", "-b", branch_name], **git_kwargs)  # nosec B607
        subprocess.run(["git", "add", "."], **git_kwargs)  # nosec B607
        subprocess.run(["git", "commit", "-m", f"Auto-fix: {', '.join(fixes_applied[:3])}"], **git_kwargs)  # nosec B607
        fixes_applied.append(f"Git: Created branch '{branch_name}' with commit")
    except Exception as e: errors.append(f"Git operations failed: {e}")

    return json.dumps({
        "status": "completed",
        "timestamp": timestamp,
        "backup": str(backup_zip) + ".zip" if backup_zip else None,
        "branch": branch_name,
        "fixes": fixes_applied,
        "errors": errors
    }, indent=2)

@mcp.tool()
def run_auto_fix(path: str, confirm: bool = False) -> str:
    """
    SAFE Auto-Fix tool with Dry Run and Backup capabilities.
    """
    target = Path(path).resolve()

    # STEP 0: Check for dirty git state
    if confirm:
        try:
            git_check = subprocess.run(
                ["git", "status", "--porcelain"],  # nosec B607
                cwd=str(target), capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL
            )

            if git_check.stdout.strip():
                return json.dumps({
                    "status": "error",
                    "error": "❌ **Action Aborted:** You have uncommitted changes. Please commit or stash first.",
                    "dirty_files": git_check.stdout.strip().split('\n')[:10]
                }, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "error": f"Git check failed: {e}"}, indent=2)

    # Identify cleanup targets
    cleanup_targets = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", "dist", "build"]
    files_to_delete = []

    for pattern in cleanup_targets:
        for item in target.rglob(pattern):
            if item.is_dir() and "venv" not in str(item) and ".venv" not in str(item):
                files_to_delete.append(str(item.relative_to(target)))

    if not confirm:
        return _auto_fix_dry_run(target, files_to_delete)

    return _auto_fix_execute(target, files_to_delete)
    
@mcp.tool()
def save_report_to_file(job_id: str) -> str:
    """Generates a Markdown report from a completed background job."""
    job = JOBS.get(job_id)
    if not job:
        return json.dumps({"status": "error", "message": f"Job ID '{job_id}' not found."})
    
    if job["status"] != "completed":
        return json.dumps({"status": "error", "message": f"Job is still {job['status']}. Wait for completion."})
    
    # Save File
    report_path = REPORTS_DIR / f"SECURITY_REPORT_{job_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Audit Report {job_id}\n\nGenerated by Python Auditor.")
    
    log(f"Report saved to: {report_path}")
    return json.dumps({"status": "success", "message": f"Report saved successfully!", "path": str(report_path)})


@mcp.tool()
def audit_quality(path: str) -> str:
    """Checks code quality (Dead code, Structure, Tests)."""
    target = Path(path).resolve()
    results = {
        "deadcode": DeadcodeTool().analyze(target),
        "structure": StructureTool().analyze(target),
        "tests": TestsTool().analyze(target)
    }
    return json.dumps(results, indent=2)


@mcp.tool()
def audit_architecture(path: str) -> str:
    """Analyzes project architecture and complexity."""
    target = Path(path).resolve()
    results = {
        "architecture": ArchitectureTool().analyze(target),
        "duplication": DuplicationTool().analyze(target),
        "typing": TypingTool().analyze(target)
    }
    return json.dumps(results, indent=2)


@mcp.tool()
def audit_cleanup(path: str) -> str:
    """Finds cleanup opportunities (cache, temp files, gitignore)."""
    target = Path(path).resolve()
    results = {
        "cleanup": run_cleanup_scan(target),
        "gitignore": GitignoreTool().analyze(target),
    }
    return json.dumps(results, indent=2)


@mcp.tool()
def audit_git(path: str) -> str:
    """Analyzes git status and recent changes."""
    target = Path(path).resolve()
    result = GitTool().analyze(target)
    return json.dumps(result, indent=2)


def get_changed_files(path: Path, base_branch: str = "main") -> list:
    """Helper: Get list of changed Python files compared to base branch."""
    try:
        cmd = ["git", "diff", "--name-only", f"{base_branch}...HEAD"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15, cwd=str(path), stdin=subprocess.DEVNULL
        )
        if result.returncode != 0: return []
        
        changed_files = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and line.endswith('.py'):
                file_path = path / line.strip()
                if file_path.exists():
                    changed_files.append(str(file_path))
        return changed_files
    except Exception: return []


def _audit_pr_changes_logic(path: str, base_branch: str = "main", run_tests: bool = True) -> str:
    """Internal logic for PR audit using PRAuditTool."""
    from app.tools.pr_audit_tool import PRAuditTool

    log(f"[PR-GATE] Starting PR audit for: {path} (base: {base_branch})")
    target = Path(path).resolve()

    changed_files = get_changed_files(target, base_branch)
    if not changed_files:
        msg = "✅ No Python changes detected in this PR."
        return json.dumps({
            "status": "success", "message": msg, "recommendation": "🟢 Ready for Review",
            "score": 100, "report": f"# 🚦 PR Gatekeeper Report\n\n{msg}\n\n**Score:** 100/100"
        }, indent=2)

    log(f"[PR-GATE] Found {len(changed_files)} changed Python files")

    # Run audit using PRAuditTool
    tool = PRAuditTool()
    result = tool.analyze(target, changed_files)

    # Run tests if score is high enough
    tests_passed = True
    test_output = ""
    if run_tests and result.get("score", 0) > 80:
        tests_passed, test_output = _run_safety_net_tests(target)

    # Generate report
    report_text = tool.generate_report(
        base_branch, changed_files, result, tests_passed, test_output, run_tests, target
    )

    # Map recommendation to display format with emojis
    bandit_issues = result.get("bandit", {}).get("total_issues", 0)
    score = result.get("score", 0)

    if bandit_issues > 0 or (run_tests and not tests_passed and score > 80):
        recommendation = "🔴 Request Changes"
    elif score >= 80:
        recommendation = "🟢 Ready for Review"
    else:
        recommendation = "🟡 Needs Improvement"

    return json.dumps({
        "status": "success",
        "recommendation": recommendation,
        "score": score,
        "changed_files_count": len(changed_files),
        "findings": {
            "security_issues": bandit_issues,
            "linting_issues": result.get("ruff", {}).get("total_issues", 0),
            "complexity_issues": result.get("complexity", {}).get("total_high_complexity", 0),
            "tests_passed": tests_passed if run_tests else None
        },
        "report": report_text
    }, indent=2)


@mcp.tool()
def audit_pr_changes(path: str, base_branch: str = "main", run_tests: bool = True) -> str:
    """
    PR Gatekeeper: Fast delta-based audit of ONLY changed files.
    """
    return _audit_pr_changes_logic(path, base_branch, run_tests)


def _run_safety_net_tests(target: Path) -> tuple:
    """Run tests as a safety net."""
    try:
        cmd = [sys.executable, "-m", "pytest", "-x", "--tb=short", "-q"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=str(target), stdin=subprocess.DEVNULL
        )
        return (result.returncode == 0, result.stdout + result.stderr)
    except Exception as e:
        return (False, f"Could not run tests: {e}")


@mcp.tool()
def audit_remote_repo(repo_url: str, branch: str = "main") -> str:
    """
    Audit a remote Git repository without manual cloning.
    """
    return _audit_remote_repo_logic(repo_url, branch)


def _audit_remote_repo_logic(repo_url: str, branch: str = "main") -> str:
    """Internal logic for remote audit using RemoteAuditOrchestrator."""
    from app.core.remote_audit_orchestrator import RemoteAuditOrchestrator

    log(f"[REMOTE-AUDIT] Starting remote audit: {repo_url} (branch: {branch})")

    orchestrator = RemoteAuditOrchestrator(REPORTS_DIR)
    orchestrator.set_log_callback(lambda msg: log(f"[REMOTE-AUDIT] {msg}"))

    # Run async orchestrator
    result = asyncio.run(orchestrator.audit_repository(repo_url, branch))
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_full_report(path: str) -> str:
    """Runs ALL tools and generates a comprehensive Markdown report file using AuditOrchestrator."""
    from app.core.audit_orchestrator import AuditOrchestrator, create_default_tool_runners

    target_path = Path(path).resolve()
    report_id = f"audit__{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Use AuditOrchestrator for consistent execution
    orchestrator = AuditOrchestrator(target_path, REPORTS_DIR)
    orchestrator.set_log_callback(log)

    tool_runners = create_default_tool_runners(target_path)

    # Run synchronously (wrap async)
    result_dict = asyncio.run(orchestrator.run_full_audit(tool_runners, report_id))

    # Generate report
    report_path = orchestrator.generate_report(report_id, result_dict)

    return f"Report generated successfully at: {report_path}"


@mcp.tool()
def get_cache_stats(path: str) -> str:
    """Get statistics about cached audit results."""
    try:
        cache_mgr = CacheManager(path, max_age_hours=1)
        return json.dumps(cache_mgr.get_cache_stats(), indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def clear_audit_cache(path: str, tool_name: str = None) -> str:
    """Clear audit cache for a project."""
    try:
        cache_mgr = CacheManager(path, max_age_hours=1)
        if tool_name:
            cache_mgr.invalidate_tool(tool_name)
            return json.dumps({"status": "success", "message": f"Cleared cache for {tool_name}"})
        else:
            cache_mgr.clear_all()
            return json.dumps({"status": "success", "message": "Cleared all audit caches"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def run_ruff_comprehensive_check(path: str) -> str:
    """Run comprehensive Ruff linting (uses FastAuditTool)."""
    try:
        project_path = Path(path).resolve()
        if not project_path.exists():
            return json.dumps({"status": "error", "error": f"Path does not exist: {path}"})
        result = run_ruff(project_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
async def start_incremental_audit(
    project_path: str,
    force_full: bool = False
) -> str:
    """
    Smart audit that only analyzes changed files.

    First run = full audit. Subsequent runs = incremental (90%+ faster).

    Args:
        project_path: Path to the Python project to audit
        force_full: If True, force a full audit even if cache exists

    Returns:
        JSON string with audit results and performance metrics

    Example:
        First run: Analyzes all 100 files in 60s
        Second run (3 files changed): Analyzes 3 files in 5s (saved 55s!)
    """
    from app.core.audit_orchestrator import create_default_tool_instances

    try:
        target_path = Path(project_path).resolve()

        if not target_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"Path does not exist: {project_path}"
            }, indent=2)

        log(f"[INCREMENTAL] Starting audit for: {target_path} (force_full={force_full})")

        # Initialize incremental engine
        engine = IncrementalEngine(target_path)

        # Use shared tool instances (single source of truth)
        tools = create_default_tool_instances()

        # Run incremental audit
        result = await engine.run_audit(tools, force_full=force_full)

        # Calculate score using ScoringEngine
        score_breakdown = ScoringEngine.calculate_score(result.tool_results)
        score = score_breakdown.final_score

        # Generate report (score recalculated internally)
        report_id = f"audit__{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        generator = ReportGeneratorV2(REPORTS_DIR)
        report_path = generator.generate_report(
            report_id=report_id,
            project_path=str(target_path),
            score=0,  # Deprecated: calculated by ScoringEngine
            tool_results=result.tool_results,
            timestamp=datetime.datetime.now()
        )
        
        # Build response
        response = {
            "status": "success",
            "mode": result.mode,
            "summary": result.get_summary(),
            "score": score,
            "duration_seconds": round(result.duration_seconds, 2),
            "report_path": str(report_path),
            "changes": {
                "new_files": len(result.changes.new_files),
                "modified_files": len(result.changes.modified_files),
                "deleted_files": len(result.changes.deleted_files),
                "cached_files": len(result.changes.unchanged_files)
            },
            "performance": {
                "time_saved_seconds": round(result.time_saved_seconds, 1) if result.time_saved_seconds else None,
                "efficiency_gain": f"{((result.time_saved_seconds / (result.duration_seconds + result.time_saved_seconds)) * 100):.0f}%" if result.time_saved_seconds else "N/A"
            },
            "cache_stats": result.cache_stats
        }
        
        log(f"[INCREMENTAL] {result.get_summary()}")
        return json.dumps(response, indent=2)
        
    except Exception as e:
        log(f"[INCREMENTAL] Error: {e}")
        import traceback
        return json.dumps({
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }, indent=2)


@mcp.tool()
def get_incremental_stats(project_path: str) -> str:
    """
    Get statistics about the incremental audit system.
    
    Shows:
    - File index status
    - Cached tools
    - Cache sizes
    - Last update times
    """
    try:
        target_path = Path(project_path).resolve()
        engine = IncrementalEngine(target_path)
        stats = engine.get_stats()
        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def clear_incremental_cache(project_path: str, tool_name: str = None) -> str:
    """
    Clear incremental audit cache.
    
    Args:
        project_path: Path to the project
        tool_name: Specific tool to clear (None = clear all)
        
    Returns:
        JSON with status and count of cleared caches
    """
    try:
        target_path = Path(project_path).resolve()
        engine = IncrementalEngine(target_path)
        cleared = engine.clear_cache(tool_name)
        
        return json.dumps({
            "status": "success",
            "message": f"Cleared {cleared} cache file(s)",
            "tool": tool_name if tool_name else "all"
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def generate_ci_pipeline(path: str, platform: str = "github", score_threshold: int = 70) -> str:
    """
    Generate CI/CD pipeline configuration for automated code audits.

    Creates platform-specific pipeline files that:
    - Run security scans (Bandit) on every PR
    - Run linting checks (Ruff) with auto-fix
    - Run tests with coverage reporting
    - Calculate audit score and comment on PR
    - Block merge if score is below threshold

    Args:
        path: Path to the project root
        platform: CI platform - 'github', 'gitlab', or 'bitbucket'
        score_threshold: Minimum score to pass CI (default: 70)

    Returns:
        JSON with paths to generated files

    Example:
        generate_ci_pipeline("/my/project", "github", 80)
        -> Creates .github/workflows/audit.yml, .pre-commit-config.yaml, PR template
    """
    from app.core.ci_generator import CIGenerator

    try:
        target_path = Path(path).resolve()

        if not target_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"Path does not exist: {path}"
            }, indent=2)

        generator = CIGenerator(target_path, score_threshold=score_threshold)
        results = generator.generate_all(platform)

        return json.dumps({
            "status": "success",
            "platform": platform,
            "score_threshold": score_threshold,
            "files_created": results,
            "next_steps": [
                f"Commit the generated files to your repository",
                f"For pre-commit: run 'pip install pre-commit && pre-commit install'",
                f"Push to trigger the first audit run"
            ]
        }, indent=2)

    except ValueError as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "supported_platforms": ["github", "gitlab", "bitbucket"]
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2)


@mcp.tool()
def generate_html_report(path: str) -> str:
    """
    Generate a styled HTML audit report for browser viewing.

    Runs all audit tools and produces an HTML report with:
    - Visual score badge
    - Styled tables and code blocks
    - Responsive design for mobile
    - Dark-themed code snippets

    Args:
        path: Path to the Python project to audit

    Returns:
        JSON with status and path to the HTML report file
    """
    from app.core.audit_orchestrator import AuditOrchestrator, create_default_tool_runners

    try:
        target_path = Path(path).resolve()
        report_id = f"audit__{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Use AuditOrchestrator
        orchestrator = AuditOrchestrator(target_path, REPORTS_DIR)
        orchestrator.set_log_callback(log)

        tool_runners = create_default_tool_runners(target_path)
        result_dict = asyncio.run(orchestrator.run_full_audit(tool_runners, report_id))

        # Generate HTML report
        generator = ReportGeneratorV2(REPORTS_DIR)
        html_path = generator.generate_html_report(
            report_id=report_id,
            project_path=str(target_path),
            score=0,
            tool_results=result_dict,
            timestamp=datetime.datetime.now()
        )

        return json.dumps({
            "status": "success",
            "html_path": html_path,
            "message": f"HTML report generated at: {html_path}"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, indent=2)


@mcp.tool()
def get_audit_trends(project_path: str, limit: int = 10) -> str:
    """
    Get historical audit trends for a project.

    Shows score progression, coverage changes, and improvement suggestions
    based on past audits. Useful for tracking code quality over time.

    Args:
        project_path: Path to the project
        limit: Maximum number of historical audits to include

    Returns:
        JSON with trend summary, sparklines, and suggestions
    """
    from app.core.trend_analyzer import TrendAnalyzer

    try:
        target_path = Path(project_path).resolve()
        analyzer = TrendAnalyzer(target_path)

        summary = analyzer.get_trend_summary()
        suggestions = analyzer.get_improvement_suggestions()
        history = analyzer.get_history(limit=limit)

        return json.dumps({
            "status": "success",
            "summary": summary,
            "suggestions": suggestions,
            "history": [h.to_dict() for h in history],
            "report_section": analyzer.generate_trend_report()
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


if __name__ == "__main__":
    # Clear log file on start
    with open(DEBUG_LOG, "w", encoding="utf-8") as f:
        f.write(f"Server Started at {datetime.datetime.now()}\n")
    print("Starting Python Auditor MCP Server...")
    print(f"Reports will be saved to: {REPORTS_DIR}")
    print(f"Debug logs: {DEBUG_LOG}")
    mcp.run()
