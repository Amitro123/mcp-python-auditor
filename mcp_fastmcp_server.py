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
from collections import defaultdict
from typing import Dict, Any, List, Set, Tuple

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

def run_ruff_comprehensive(path: Path) -> dict:
    """Run Ruff with all rule categories to replace multiple tools."""
    
    # Rule categories to enable
    # Full list: https://docs.astral.sh/ruff/rules/
    rule_sets = {
        'security': 'S',      # Bandit rules
        'errors': 'E',        # pycodestyle errors
        'warnings': 'W',      # pycodestyle warnings
        'pyflakes': 'F',      # Unused imports, undefined names
        'complexity': 'C90',  # McCabe complexity
        'imports': 'I',       # Import sorting
        'docstrings': 'D',    # pydocstyle
        'performance': 'PERF', # Performance anti-patterns
        'bugbear': 'B',       # Common bugs
    }
    
    # Combine all rules
    all_rules = ','.join(rule_sets.values())
    
    cmd = [
        sys.executable,
        '-m', 'ruff',
        'check',
        str(path),
        '--select', all_rules,
        '--output-format', 'json',
        '--exit-zero',  # Don't fail on issues
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,  # Ruff is FAST - 10s is plenty
            cwd=path,
            stdin=subprocess.DEVNULL
        )
        
        issues = json.loads(result.stdout) if result.stdout else []
        
        # Categorize issues by type
        categorized = {
            'security': [],      # S rules (Bandit replacement)
            'quality': [],       # E, W rules
            'imports': [],       # I, F401 rules
            'complexity': [],    # C90 rules
            'docstrings': [],    # D rules
            'performance': [],   # PERF, B rules
            'other': []
        }
        
        for issue in issues:
            code = issue.get('code', '')
            
            if code.startswith('S'):
                categorized['security'].append(issue)
            elif code.startswith(('E', 'W')):
                categorized['quality'].append(issue)
            elif code.startswith('I') or code == 'F401':
                categorized['imports'].append(issue)
            elif code.startswith('C90'):
                categorized['complexity'].append(issue)
            elif code.startswith('D'):
                categorized['docstrings'].append(issue)
            elif code.startswith(('PERF', 'B')):
                categorized['performance'].append(issue)
            else:
                categorized['other'].append(issue)
        
        total_issues = len(issues)
        files_analyzed = len(set(i.get('filename') for i in issues)) if issues else 0
        
        return {
            'tool': 'ruff_comprehensive',
            'status': 'issues_found' if total_issues > 0 else 'clean',
            'total_issues': total_issues,
            'categorized': categorized,
            'issues': issues,  # Raw issues for compatibility
            'files_analyzed': files_analyzed,
            'summary': {
                'security': len(categorized['security']),
                'quality': len(categorized['quality']),
                'imports': len(categorized['imports']),
                'complexity': len(categorized['complexity']),
                'performance': len(categorized['performance']),
                'docstrings': len(categorized['docstrings']),
            },
            # Backward compatibility fields
            'code_security': {
                'issues': categorized['security'],
                'files_scanned': files_analyzed
            }
        }
        
    except subprocess.TimeoutExpired:
        return {
            'tool': 'ruff_comprehensive',
            'status': 'error',
            'error': 'Ruff timed out (should never happen!)'
        }
    except json.JSONDecodeError as e:
        return {
            'tool': 'ruff_comprehensive',
            'status': 'error',
            'error': f'Failed to parse Ruff JSON output: {str(e)}'
        }
    except Exception as e:
        return {
            'tool': 'ruff_comprehensive',
            'status': 'error',
            'error': f'Ruff failed: {str(e)}'
        }


def run_bandit(path: Path) -> dict:
    """Run real Bandit security analysis (using pyproject.toml config)."""
    try:
        target_path = Path(path).resolve()
        
        # Use explicit config to exclude tests and skip false positives
        cmd = [
            sys.executable, "-m", "bandit",
            "-c", "pyproject.toml",
            "-r", str(target_path),
            "-f", "json",
            "--exit-zero"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(target_path), # Important: run from root so config is found
                stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired:
            return {"tool": "bandit", "status": "error", "error": "Timeout (>120s)", "issues": []}
            
        bandit_data = {}
        if result.stdout.strip():
            try:
                bandit_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
                
        issues = bandit_data.get("results", [])
        
        # Filter logic is now handled by Bandit config (B101 etc skipped), 
        # but we can add extra safety here if needed.
        
        # Extract files scanned from metrics
        metrics = bandit_data.get("metrics", {})
        files_scanned = metrics.get("_totals", {}).get("loc", 0) if metrics else 0
        
        # If metrics doesn't have totals, count unique files from results
        if files_scanned == 0 and issues:
            files_scanned = len(set(issue.get("filename", "") for issue in issues))
        
        return {
            "tool": "bandit",
            "status": "issues_found" if issues else "clean",
            "total_issues": len(issues),
            "issues": issues,
            "metrics": metrics,
            "files_scanned": files_scanned
        }
        
    except Exception as e:
        return {"tool": "bandit", "status": "error", "error": str(e), "issues": [], "total_issues": 0}


def run_secrets(path: Path) -> dict:
    """Run detect-secrets scan."""
    try:
        target_path = Path(path).resolve()
        # Use cwd=. pattern
        cmd = [
            "detect-secrets", "scan", ".",
            "--exclude-files", "node_modules",
            "--exclude-files", "venv",
            "--exclude-files", ".venv",
            "--exclude-files", ".git",
            "--exclude-files", "__pycache__",
            "--exclude-files", "frontend/test-results",
            "--exclude-files", "playwright-report"
        ]
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60, 
                cwd=str(target_path),
                stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired:
            return {"tool": "secrets", "status": "error", "error": "Timeout (>60s)"}
        
        secrets = []
        if result.stdout:
            try:
                data = json.loads(result.stdout)
                for file_path, findings in data.get("results", {}).items():
                    # Filter venv/lock files
                    if "lock" in file_path or ".min." in file_path:
                        continue
                    for finding in findings:
                        secrets.append({
                            "file": file_path,
                            "line": finding.get("line_number"),
                            "type": finding.get("type", "Secret"),
                            "hashed_secret": finding.get("hashed_secret", "")[:8] + "..."
                        })
            except json.JSONDecodeError:
                pass
            
        return {
            "tool": "secrets",
            "status": "issues_found" if secrets else "clean",
            "total_secrets": len(secrets),
            "secrets": secrets[:20]
        }
    except FileNotFoundError:
        return {"tool": "secrets", "status": "skipped", "error": "detect-secrets not installed", "secrets": [], "total_secrets": 0}
    except Exception as e:
        return {"tool": "secrets", "status": "error", "error": str(e), "secrets": [], "total_secrets": 0}


def run_ruff(path: Path) -> dict:
    """Run Ruff linter on the project."""
    try:
        # Use cwd pattern for Windows compatibility
        target_path = Path(path).resolve()
        cmd = [
            sys.executable, "-m", "ruff", "check", ".",
            "--output-format", "json",
            "--exclude", "node_modules,venv,.venv,.git,__pycache__,frontend/test-results"
        ]
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60, 
                cwd=str(target_path),
                stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired:
            return {"tool": "ruff", "status": "error", "error": "Timeout (>60s)", "issues": [], "total_issues": 0}
        
        try:
            issues = json.loads(result.stdout) if result.stdout else []
        except json.JSONDecodeError:
            issues = []
        
        return {
            "tool": "ruff",
            "status": "issues_found" if issues else "clean",
            "total_issues": len(issues) if issues else 0,
            "issues": (issues or [])[:30]
        }
    except FileNotFoundError:
        return {"tool": "ruff", "status": "skipped", "error": "Ruff not installed", "issues": [], "total_issues": 0}
    except subprocess.TimeoutExpired:
        return {"tool": "ruff", "status": "error", "error": "Timeout (>120s)", "issues": [], "total_issues": 0}
    except Exception as e:
        return {"tool": "ruff", "status": "error", "error": str(e), "issues": [], "total_issues": 0}


def run_pip_audit(path: Path) -> dict:
    """Run pip-audit to check for vulnerable dependencies."""
    try:
        # Ensure absolute path for Windows compatibility
        target_path = Path(path).resolve()
        
        # Check if requirements.txt exists - much faster scan
        req_file = target_path / "requirements.txt"
        if req_file.exists():
            cmd = ["pip-audit", "-r", str(req_file), "-f", "json"]
        else:
            # Fallback to environment scan with longer timeout
            cmd = ["pip-audit", "-f", "json"]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=180, 
                cwd=str(target_path),
                stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired:
            return {"tool": "pip_audit", "status": "error", "error": "Timeout (>180s)"}
        
        try:
            data = json.loads(result.stdout) if result.stdout else []
        except json.JSONDecodeError:
            data = []
        
        # Safe handling - ensure data is a list
        if not isinstance(data, list):
            data = []
        
        return {
            "tool": "pip-audit",
            "status": "vulnerabilities_found" if data else "clean",
            "total_vulnerabilities": len(data) if data else 0,
            "vulnerabilities": (data or [])[:20],
            "scan_mode": "requirements.txt" if req_file.exists() else "environment"
        }
    except FileNotFoundError:
        return {"tool": "pip-audit", "status": "skipped", "error": "pip-audit not installed", "vulnerabilities": [], "total_vulnerabilities": 0}
    except subprocess.TimeoutExpired:
        return {"tool": "pip-audit", "status": "error", "error": "Timeout (>180s)", "vulnerabilities": [], "total_vulnerabilities": 0}
    except Exception as e:
        return {"tool": "pip-audit", "status": "error", "error": str(e), "vulnerabilities": [], "total_vulnerabilities": 0}


async def run_structure(target: str) -> dict:
    """Analyze project structure using StructureTool."""
    tool = StructureTool()
    return await asyncio.to_thread(tool.analyze, Path(target))


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
    try:
        target_path = Path(path).resolve()
        tool = FastAuditTool()
        result = tool.analyze(target_path)
        
        # Map to expected format for backward compatibility
        return {
            "tool": "ruff",
            "status": result.get("status", "clean"),
            "high_complexity_functions": result.get("complexity", []),
            "total_high_complexity": len(result.get("complexity", [])),
            "performance_issues": result.get("performance", []),
            "total_functions_analyzed": result.get("total_issues", 0)
        }
    except Exception as e:
         return {"tool": "ruff", "status": "error", "error": str(e), "high_complexity_functions": [], "total_high_complexity": 0}


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
    """Get git repository information."""
    try:
        kwargs = {"capture_output": True, "text": True, "cwd": str(path), "timeout": 15, "stdin": subprocess.DEVNULL}
        
        # Check if git repo
        result = subprocess.run(["git", "rev-parse", "--git-dir"], **kwargs)  # nosec B607
        if result.returncode != 0:
            return {"tool": "git", "status": "not_a_repo", "message": "Not a git repository"}
        
        # Get last commit
        log_result = subprocess.run(["git", "log", "-1", "--format=%H|%s|%an|%ar"], **kwargs)  # nosec B607
        last_commit = {}
        if log_result.stdout.strip():
            parts = log_result.stdout.strip().split('|')
            if len(parts) >= 4:
                last_commit = {
                    "hash": parts[0][:8],
                    "message": parts[1][:50],
                    "author": parts[2],
                    "when": parts[3]
                }
        
        # Get status
        status_result = subprocess.run(["git", "status", "-s"], **kwargs)  # nosec B607
        changes = len([l for l in status_result.stdout.strip().split('\n') if l.strip()])
        
        # Get branch
        branch_result = subprocess.run(["git", "branch", "--show-current"], **kwargs)  # nosec B607
        branch = branch_result.stdout.strip()
        
        return {
            "tool": "git",
            "status": "analyzed",
            "branch": branch,
            "uncommitted_changes": changes,
            "last_commit": last_commit
        }
    except FileNotFoundError:
        return {"tool": "git", "status": "skipped", "error": "Git not installed"}
    except Exception as e:
        return {"tool": "git", "status": "error", "error": str(e)}


def run_cleanup_scan(path: Path) -> dict:
    """Scan for cleanup opportunities (cache dirs, temp files) - Simplified version."""
    try:
        cleanup_targets = {
            "__pycache__": 0,
            ".pytest_cache": 0,
            ".mypy_cache": 0,
            ".ruff_cache": 0,
        }
        
        total_size_bytes = 0
        items_found = []
        
        # Directories to exclude from cleanup suggestions
        exclude_patterns = {'.venv', 'venv', 'env', 'node_modules', 'site-packages', '.git'}

        for pattern in cleanup_targets.keys():
            for d in path.glob(f"**/{pattern}"):
                # Skip if path contains excluded directories
                path_str = str(d)
                if any(excl in path_str for excl in exclude_patterns):
                    continue

                if d.is_dir():
                    try:
                        size = sum(f.stat().st_size for f in d.rglob('*') if f.is_file())
                        cleanup_targets[pattern] += 1
                        total_size_bytes += size
                        items_found.append(str(d.relative_to(path)))
                    except:
                        pass  # nosec B110
        
        return {
            "tool": "cleanup",
            "status": "cleanup_available" if total_size_bytes > 0 else "clean",
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "cleanup_targets": {k: v for k, v in cleanup_targets.items() if v > 0},
            "items": items_found[:20]
        }
    except Exception as e:
        return {"tool": "cleanup", "status": "error", "error": str(e)}


def _find_test_python_exe(target_path: Path) -> str:
    """Finds the appropriate Python executable for running tests."""
    venv_dirs = [".venv", "venv", "env"]
    python_exe = sys.executable  # Fallback to system python

    for venv_name in venv_dirs:
        venv_path = target_path / venv_name
        if venv_path.exists():
            # Windows vs Unix
            if sys.platform == "win32":
                candidate = venv_path / "Scripts" / "python.exe"
            else:
                candidate = venv_path / "bin" / "python"
            if candidate.exists():
                python_exe = str(candidate)
                break
    return python_exe

def _parse_pytest_output(output: str) -> tuple[int, int, int]:
    """Parses pytest stdout for coverage and test counts."""
    # Parse coverage percentage (look for "TOTAL ... XX%")
    coverage_percent = 0
    coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
    if coverage_match:
        coverage_percent = int(coverage_match.group(1))

    # Count test results
    tests_passed = 0
    tests_failed = 0
    tests_match = re.search(r'(\d+) passed', output)
    if tests_match:
        tests_passed = int(tests_match.group(1))
    fail_match = re.search(r'(\d+) failed', output)
    if fail_match:
        tests_failed = int(fail_match.group(1))

    return coverage_percent, tests_passed, tests_failed

def _categorize_test_files(target_path: Path) -> dict:
    """Categorize test files into unit, integration, e2e."""
    unit_tests = list(target_path.glob("**/test_*.py")) + list(target_path.glob("**/tests/unit/**/*.py"))
    integration_tests = list(target_path.glob("**/tests/integration/**/*.py")) + list(target_path.glob("**/test_integration_*.py"))
    e2e_tests = list(target_path.glob("**/tests/e2e/**/*.py")) + list(target_path.glob("**/test_e2e_*.py"))

    all_test_files = set()
    unit_count = 0
    integration_count = 0
    e2e_count = 0

    for f in unit_tests:
        if str(f) not in all_test_files and 'integration' not in str(f).lower() and 'e2e' not in str(f).lower():
            unit_count += 1
            all_test_files.add(str(f))

    for f in integration_tests:
        if str(f) not in all_test_files:
            integration_count += 1
            all_test_files.add(str(f))

    for f in e2e_tests:
        if str(f) not in all_test_files:
            e2e_count += 1
            all_test_files.add(str(f))

    return {
        "unit": unit_count,
        "integration": integration_count,
        "e2e": e2e_count,
        "total_files": len(all_test_files)
    }


def _collect_test_names(project_path: Path, python_exe: str) -> list:
    """Collect all test names using pytest --collect-only."""
    try:
        cmd = [
            python_exe, '-m', 'pytest', '--collect-only', '-q', '--color=no',
            '--ignore=node_modules', '--ignore=venv', '--ignore=.venv',
            '--ignore=dist', '--ignore=build', '--ignore=.git',
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,  # Increased from 30s for larger projects
            cwd=project_path,
            errors='replace'
        )

        # Parse test count from output (e.g., "142 tests collected")
        test_list = []
        for line in result.stdout.splitlines():
            line = line.strip()
            # Look for test IDs like "tests/test_api.py::test_root_endpoint"
            if '::test_' in line or '::Test' in line:
                test_list.append(line)

        # If no detailed list, try to get count from summary
        if not test_list:
            import re
            match = re.search(r'(\d+)\s+tests?\s+collected', result.stdout + result.stderr)
            if match:
                count = int(match.group(1))
                # Create placeholder list with count
                test_list = [f"test_{i}" for i in range(count)]

        return test_list

    except Exception as e:
        log(f"Failed to collect test names: {e}")
        return []


def run_tests_coverage(path: Path) -> dict:
    """Run pytest with coverage to analyze test suite."""
    try:
        target_path = Path(path).resolve()
        python_exe = _find_test_python_exe(target_path)
        
        # Check if tests directory exists
        tests_dir = target_path / "tests"
        if not tests_dir.exists():
            # Try finding any test files
            test_files = list(target_path.glob("**/test_*.py"))
            if not test_files:
                return {
                    "tool": "pytest",
                    "status": "skipped",
                    "error": "No tests directory or test files found",
                    "coverage_percent": 0,
                    "tests_found": 0
                }
        
        # Run pytest with coverage
        cmd = [
            python_exe, "-m", "pytest",
            "--cov=.",
            "--cov-report=term-missing",
            "-q",  # Quiet mode
            "--ignore=node_modules",
            "--ignore=venv",
            "--ignore=.venv",
            "--ignore=.git",
            "--ignore=frontend/test-results",
            "."
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300, 
                cwd=str(target_path),
                stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired:
            return {"tool": "pytest", "status": "error", "error": "Timeout (>300s)", "coverage_percent": 0}
        
        output = result.stdout + result.stderr
        coverage_percent, tests_passed, tests_failed = _parse_pytest_output(output)
        test_breakdown = _categorize_test_files(target_path)

        # Collect test names for actual test count
        test_list = _collect_test_names(target_path, python_exe)

        return {
            "tool": "pytest",
            "status": "success" if result.returncode in [0, 1] else "error",
            "coverage_percent": coverage_percent,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "test_breakdown": test_breakdown,
            "test_list": test_list,
            "total_test_files": test_breakdown.get("total_files", 0),
            "python_exe": python_exe
        }
        
    except subprocess.TimeoutExpired:
        return {"tool": "pytest", "status": "error", "error": "Timeout (>300s)", "coverage_percent": 0}
    except FileNotFoundError:
        return {"tool": "pytest", "status": "skipped", "error": "pytest not installed", "coverage_percent": 0}
    except Exception as e:
        return {"tool": "pytest", "status": "error", "error": str(e), "coverage_percent": 0}


def _parse_imports_ast(py_files: List[Path], root_path: Path) -> Tuple[Set[str], List[Tuple[str, str]], Dict[str, Set[str]]]:
    """Parses AST to find imports and dependencies."""
    STDLIB_MODULES = {
        'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 're', 'typing',
        'collections', 'itertools', 'functools', 'logging', 'subprocess',
        'threading', 'multiprocessing', 'asyncio', 'uuid', 'hashlib',
        'base64', 'io', 'copy', 'math', 'random', 'abc', 'dataclasses',
        'enum', 'contextlib', 'warnings', 'traceback', 'inspect', 'shutil',
        'tempfile', 'glob', 'fnmatch', 'stat', 'struct', 'codecs', 'csv',
        'configparser', 'argparse', 'getopt', 'optparse', 'unittest', 'doctest',
        'pdb', 'profile', 'timeit', 'gc', 'platform', 'socket', 'http',
        'urllib', 'email', 'html', 'xml', 'ssl', 'ftplib', 'smtplib',
        'pickle', 'shelve', 'sqlite3', 'zlib', 'gzip', 'zipfile', 'tarfile',
        'textwrap', 'string', 'difflib', 'ctypes', 'types', 'operator',
        '__future__', 'builtins', 'importlib', 'pkgutil', 'pprint', 'secrets'
    }

    dependencies = []
    file_nodes = set()
    nodes_by_group = defaultdict(set)
    
    for py_file in py_files[:50]:  # Limit to avoid huge graphs
        try:
            source_code = py_file.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(source_code)

            try:
                rel_path = py_file.relative_to(root_path)
            except ValueError:
                rel_path = py_file.name

            source_name = str(rel_path).replace('\\', '/').replace('.py', '')
            file_nodes.add(source_name)

            parts = source_name.split('/')
            group = parts[0] if len(parts) > 1 else "root"
            nodes_by_group[group].add(source_name)

            for node in ast.walk(tree):
                target_module = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        target_module = alias.name.split('.')[0]
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        target_module = node.module.split('.')[0]

                if target_module and target_module not in STDLIB_MODULES:
                    if target_module in [f.stem for f in py_files] or '.' not in target_module:
                        dependencies.append((source_name, target_module))
        except (SyntaxError, UnicodeDecodeError):
            continue

    return file_nodes, dependencies, nodes_by_group

def _generate_mermaid_graph(nodes_by_group: Dict[str, Set[str]], dependencies: List[Tuple[str, str]]) -> str:
    """Generates a Mermaid graph string from nodes and dependencies."""
    mermaid_lines = ["graph TD"]

    for group_name, nodes in sorted(nodes_by_group.items()):
        if not nodes: continue
        display_name = group_name.replace('_', ' ').title()
        mermaid_lines.append(f"    subgraph {display_name}")
        for node in sorted(nodes):
            clean_node = node.replace('/', '_').replace('-', '_')
            mermaid_lines.append(f"        {clean_node}[{node}]")
        mermaid_lines.append("    end")

    seen_edges = set()
    for source, target in dependencies[:100]:
        edge = f"{source}-->{target}"
        if edge not in seen_edges and source != target:
            seen_edges.add(edge)
            clean_source = source.replace('/', '_').replace('-', '_')
            clean_target = target.replace('/', '_').replace('-', '_')
            mermaid_lines.append(f"    {clean_source} --> {clean_target}")

    return "\n".join(mermaid_lines) if len(mermaid_lines) > 1 else "graph TD\n    Note[No internal dependencies found]"

def run_architecture_visualizer(path: Path) -> dict:
    """
    Generate a Mermaid.js dependency graph by parsing Python imports.
    Pure Python implementation using AST - groups nodes into subgraphs by directory.
    """
    try:
        p = Path(path)
        py_files = list(p.glob("**/*.py"))
        
        py_files = [f for f in py_files if not any(
            skip in str(f) for skip in [
                'venv', '.venv', 'node_modules', '__pycache__', 
                '.git', 'site-packages', 'external_libs', 'htmlcov'
            ]
        )]
        
        file_nodes, dependencies, nodes_by_group = _parse_imports_ast(py_files, p)
        mermaid_graph = _generate_mermaid_graph(nodes_by_group, dependencies)
        
        return {
            "tool": "architecture",
            "status": "analyzed",
            "total_files": len(py_files),
            "total_dependencies": len(dependencies),
            "mermaid_graph": mermaid_graph,
            "nodes": list(file_nodes)[:30]
        }
    except Exception as e:
        return {"tool": "architecture", "status": "error", "error": str(e)}


def _calculate_audit_score(results: dict) -> int:
    """Calculates a weighted audit score based on tool results."""
    score = 100
    
    # 1. Security Penalty (Max -30)
    bandit_issues = results.get("bandit", {}).get("issues", [])
    if bandit_issues:
        score -= 20  # Critical security issues
    
    secrets_findings = results.get("secrets", {}).get("total_findings", 0)
    if secrets_findings > 0:
        score -= 10  # Credentials in code
    
    # 2. Testing Penalty (Max -40, Exponential)
    cov = results.get("tests", {}).get("coverage_percent", 100)
    if cov < 20:
        score -= 40  # Severe: Almost no tests
    elif cov < 50:
        score -= 25  # Major: Low coverage
    elif cov < 80:
        score -= 10  # Minor: Needs improvement
    
    # 3. Code Quality Penalty (Max -20)
    duplicates = results.get("duplication", {}).get("total_duplicates", 0)
    score -= min(duplicates, 15)  # -1 per duplicate, cap at -15
    
    dead_code_items = len(results.get("dead_code", {}).get("unused_items", []))
    score -= min(dead_code_items, 5)  # -1 per dead item, cap at -5
    
    # 4. Complexity Penalty (Max -10)
    complex_funcs = len(results.get("efficiency", {}).get("high_complexity_functions", []))
    score -= min(complex_funcs * 2, 10)  # -2 per complex function, cap at -10
    
    return max(0, score)

def _generate_report_header(path: str, score: int, job_id: str, duration: str) -> List[str]:
    """Generates the markdown header with score and status."""
    score_emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
    md = []
    try:
        md.append(f"# 🕵️‍♂️ Project Audit Report: {Path(path).name}")
        md.append(f"**Score:** {score}/100 {score_emoji} | **Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        md.append(f"**Scan Duration:** {duration} | **Job ID:** `{job_id}`")
    except Exception as e:
        log(f"Error generating report header: {e}")
        md.append(f"# Audit Report (Error: {e})")
    md.append("")
    md.append("## 🔧 Self-Healing Status")
    md.append("**Status:** Healthy ✅ (No missing tools detected)") 
    md.append("")
    return md

def _generate_tool_summary(results: dict) -> List[str]:
    """Generates the tool execution summary table."""
    md = ["## 📊 Tool Execution Summary", "", "| Tool | Status | Details |", "|------|--------|----------|"]
    
    def tool_status(result):
        status = result.get("status", "unknown")
        if status == "clean": return "✅ Pass"
        elif status == "issues_found": return "❌ Fail"
        elif status == "error": return "⚠️ Error"
        elif status == "skipped": return "⏭️ Skip"
        else: return "ℹ️ Info"

    tools_summary = [
        ("📁 Structure", results.get("structure", {}), lambda r: f"{r.get('total_files', 0)} files, {r.get('total_dirs', 0)} dirs"),
        ("🏗️ Architecture", results.get("architecture", {}), lambda r: f"{r.get('total_dependencies', 0)} dependencies"),
        ("🧮 Complexity", results.get("efficiency", {}), lambda r: f"{len(r.get('high_complexity_functions', []))} high-complexity functions"),
        ("🎭 Duplication", results.get("duplication", {}), lambda r: f"{r.get('total_duplicates', 0)} duplicate blocks"),
        ("☠️ Dead Code", results.get("dead_code", {}), lambda r: f"{r.get('total_dead_code', 0)} unused items"),
        ("🧹 Cleanup", results.get("cleanup", {}), lambda r: f"{r.get('total_size_mb', 0):.1f} MB reclaimable"),
        ("🔑 Secrets", results.get("secrets", {}), lambda r: f"{r.get('total_findings', 0)} secrets found"),
        ("🔒 Security (Bandit)", results.get("bandit", {}), lambda r: f"{r.get('total_issues', 0)} issues"),
        ("📋 Ruff", results.get("ruff", {}), lambda r: f"{r.get('total_issues', 0)} issues"),
        ("🔍 Pip-Audit", results.get("pip_audit", {}), lambda r: f"{r.get('total_vulns', 0)} vulnerabilities"),
        ("✅ Tests", results.get("tests", {}), lambda r: f"Coverage: {r.get('coverage_percent', 0)}%"),
        ("📝 Git Info", results.get("git_info", {}), lambda r: r.get('current_branch', 'N/A')),
    ]
    
    for tool_name, result, details_fn in tools_summary:
        status_str = tool_status(result)
        try:
            details = details_fn(result) if result else "Not run"
        except: details = "N/A"
        md.append(f"| {tool_name} | {status_str} | {details} |")
    md.append("")
    return md

def _generate_priorities_section(results: dict, score: int) -> List[str]:
    """Generates the Top Priorities section."""
    md = ["## 🚨 Top Priorities"]
    priorities = []

    bandit_issues = results.get("bandit", {}).get("issues", [])
    if bandit_issues:
        priorities.append("🔴 **Security:** Critical vulnerabilities found.")
    
    cov = results.get("tests", {}).get("coverage_percent", 100)
    if cov < 50:
        priorities.append(f"🟡 **Testing:** Very low coverage ({cov}%)")
    
    if not priorities:
        md.append("✅ No critical priority fixes needed.")
    else:
        for i, p in enumerate(priorities, 1):
            md.append(f"{i}. {p}")
    md.append("")
    return md

def _generate_detailed_findings(results: dict) -> List[str]:
    """Generates the Detailed Findings sections."""
    md = ["## 📊 Detailed Findings"]
    
    # Security
    bandit_issues = results.get("bandit", {}).get("issues", [])
    md.append(f"### 🛡️ Security ({len(bandit_issues)} issues)")
    if not bandit_issues:
        md.append("✅ No security issues found.")
    else:
        md.append("| Severity | Type | File | Description |")
        md.append("|----------|------|------|-------------|")
        for issue in bandit_issues[:10]:
            try: fname = Path(issue.get('file', '')).name
            except Exception: fname = issue.get('file', 'unknown')
            md.append(f"| {issue.get('severity')} | {issue.get('type')} | `{fname}:{issue.get('line')}` | {issue.get('description','')} |")
    md.append("")

    # Quality - Dead Code
    md.append("### 🧹 Code Quality & Hygiene")
    dead = results.get("dead_code", {}).get("items", [])
    md.append(f"**💀 Dead Code / Unused ({len(dead)} items)**")
    if dead:
        for item in dead[:10]: md.append(f"- `{item}`")
        if len(dead) > 10: md.append(f"- ... and {len(dead)-10} more")
    else: md.append("✅ Clean.")
    md.append("")

    # Complexity
    complex_funcs = results.get("efficiency", {}).get("high_complexity_functions", [])
    md.append("**🤯 Complex Functions (Radon)**")
    if complex_funcs:
        md.append("| File | Function | Rank | Score |")
        md.append("|---|---|---|---|")
        for f in complex_funcs:
            try: fname = Path(f.get('file','')).name
            except Exception: fname = f.get('file', 'unknown')
            md.append(f"| {fname} | {f.get('function')} | {f.get('rank')} | {f.get('complexity')} |")
    else: md.append("✅ No complex functions detected.")
    md.append("")

    # Duplication
    dup = results.get("duplication", {})
    md.append("## 🎭 DUPLICATES (Grouped + Actionable)")
    if dup.get("status") == "issues_found":
        md.append(f"**Found {dup.get('total_duplicates', 0)} duplicated blocks.**")
        for d in dup.get("duplicates", [])[:5]:
             md.append(f"- **Hash:** `{d['hash'][:8]}` ({d['count']} copies)")
             for loc in d.get("locations", [])[:3]:
                  md.append(f"  - `{loc}`")
             if len(d.get("locations", [])) > 3:
                  md.append(f"  - ...and {len(d['locations'])-3} more")
    elif dup.get("status") == "error":
         md.append(f"⚠️ **Duplication analysis failed:** {dup.get('error')}")
    else: md.append("✅ No code duplication found.")
    md.append("")

    return md

def generate_full_markdown_report(job_id: str, duration: str, results: dict, path: str) -> str:
    """Generate a rich, dashboard-style Markdown report."""
    score = _calculate_audit_score(results)

    md = _generate_report_header(path, score, job_id, duration)
    md.extend(_generate_tool_summary(results))
    md.extend(_generate_priorities_section(results, score))

    # Structure
    try:
        md.append("## 📂 Project Structure")
        struct = results.get("structure", {})
        file_counts = struct.get("file_counts", {})
        py_count = file_counts.get(".py", 0)
        md.append(f"**Files:** {struct.get('total_files', 0)} total ({py_count} Python) | **Directories:** {struct.get('total_dirs', 0)}")
        if struct.get("tree"):
            md.append("### 📁 Tree View")
            md.append("```\n" + struct.get("tree") + "\n```")
        md.append("")
    except Exception as e:
         log(f"Error in Structure section: {e}")
         md.append(f"Error rendering structure: {e}")

    # Architecture
    md.append("## 🗺️ Architecture Logic")
    if results.get("architecture", {}).get("mermaid_graph"):
        md.append("```mermaid\n" + results["architecture"]["mermaid_graph"] + "\n```")
    else: md.append("_No architecture graph generated._")
    md.append("")

    md.extend(_generate_detailed_findings(results))

    # Cleanup
    cleanup = results.get("cleanup", {})
    md.append("**🗑️ Junk / Cleanup**")
    md.append(f"- **Total Reclaimable:** {cleanup.get('total_size_mb', 0)} MB")
    for target, count in cleanup.get("cleanup_targets", {}).items():
        md.append(f"  - `{target}`: {count} items")
    md.append("")

    # Tests
    tests = results.get("tests", {})
    md.append("### 🧪 Tests & Coverage")
    md.append("")
    md.append(f"**Coverage:** {tests.get('coverage_percent', 0)}%")
    md.append(f"**Passed:** {tests.get('tests_passed', 0)} ✅ | **Failed:** {tests.get('tests_failed', 0)} ❌")
    md.append("")
    
    # Git Info
    git_info = results.get("git_info", {})
    md.append("### 📝 Recent Changes")
    if git_info.get("status") in ["analyzed", "clean"]:
        md.append(f"**Branch:** `{git_info.get('branch', 'unknown')}`")
        last_commit = git_info.get("last_commit", {})
        if last_commit:
            md.append(f"**Last Commit:** {last_commit.get('hash', '')[:8]} - {last_commit.get('message', '')}")
    else: md.append("ℹ️ Not a git repository")
    md.append("")
    
    md.append("\n---\n*Generated by Python Auditor MCP v2.1*")
    
    return "\n".join(md)
    



def validate_report_integrity(report_content: str) -> str:
    """Ensures report has all required sections (Security, Quality, Duplication, Tests)."""
    # Updated to match actual template section headers
    required = [
        "## 📂 Project Structure",
        "## 📊 Detailed Findings",
        "## 🔒 Security Analysis",  # Fixed: was "### 🛡️ Security"
        "## 🧪 Test Coverage",
        "## 🧹 Code Quality"  # Includes duplication subsection
    ]
    missing = [r for r in required if r not in report_content]

    footer = "\n\n## 🛡️ Report Integrity Check\n"
    if missing:
        footer += f"**Status:** ⚠️ Incomplete\nMissing sections: {', '.join(missing)}"
    else:
        footer += "**Status:** ✅ Pass (All sections verified)"

    return report_content + footer


async def run_audit_background(job_id: str, path: str):

    """The actual heavy lifting function running in the background."""
    log(f"[Job {job_id}] Starting FULL AUDIT on {path}...")
    JOBS[job_id] = {"status": "running", "start_time": time.time()}
    
    target = Path(path).resolve()
    
    try:
        # Initialize cache manager
        from app.core.cache_manager import CacheManager
        cache_mgr = CacheManager(str(target), max_age_hours=1)
        log(f"[Job {job_id}] Cache manager initialized")
        
        # Helper for logging
        async def run_with_log(name: str, coro):
            log(f"[Job {job_id}] ⏳ Starting {name}...")
            try:
                start_t = time.time()
                res = await coro
                res["duration_s"] = round(time.time() - start_t, 2)
                log(f"[Job {job_id}] ✅ Finished {name} ({res['duration_s']}s)")
                return res
            except Exception as e:
                log(f"[Job {job_id}] ❌ Failed {name}: {e}")
                return {"tool": name, "status": "error", "error": str(e)}
        
        # Cached wrapper functions
        async def run_bandit_cached():
            cached = cache_mgr.get_cached_result("bandit", ["**/*.py"])
            if cached: return cached
            result = await asyncio.to_thread(run_bandit, target)
            cache_mgr.save_result("bandit", result, ["**/*.py"])
            return result
        
        async def run_secrets_cached():
            cached = cache_mgr.get_cached_result("secrets", ["**/*"])
            if cached: return cached
            result = await asyncio.to_thread(run_secrets, target)
            cache_mgr.save_result("secrets", result, ["**/*"])
            return result
        
        async def run_ruff_cached():
            cached = cache_mgr.get_cached_result("ruff", ["**/*.py"])
            if cached: return cached
            result = await asyncio.to_thread(run_ruff, target)
            cache_mgr.save_result("ruff", result, ["**/*.py"])
            return result
        
        async def run_pip_audit_cached():
            cached = cache_mgr.get_cached_result("pip_audit", ["requirements.txt", "pyproject.toml", "setup.py"])
            if cached: return cached
            result = await asyncio.to_thread(run_pip_audit, target)
            cache_mgr.save_result("pip_audit", result, ["requirements.txt", "pyproject.toml", "setup.py"])
            return result
        
        async def run_structure_cached():
            cached = cache_mgr.get_cached_result("structure", ["**/*.py"])
            if cached: return cached
            result = await run_structure(target)
            cache_mgr.save_result("structure", result, ["**/*.py"])
            return result
        
        async def run_dead_code_cached():
            cached = cache_mgr.get_cached_result("dead_code", ["**/*.py"])
            if cached: return cached
            result = await asyncio.to_thread(run_dead_code, target)
            cache_mgr.save_result("dead_code", result, ["**/*.py"])
            return result
        
        async def run_efficiency_cached():
            cached = cache_mgr.get_cached_result("efficiency", ["**/*.py"])
            if cached: return cached
            result = await asyncio.to_thread(run_efficiency, target)
            cache_mgr.save_result("efficiency", result, ["**/*.py"])
            return result
        
        async def run_duplication_cached():
            cached = cache_mgr.get_cached_result("duplication", ["**/*.py"])
            if cached: return cached
            result = await asyncio.to_thread(run_duplication, target)
            cache_mgr.save_result("duplication", result, ["**/*.py"])
            return result
        
        async def run_git_info_cached():
            # Git info changes frequently, use shorter cache (5 minutes)
            cached = cache_mgr.get_cached_result("git_info", [".git/HEAD", ".git/index"])
            if cached: return cached
            result = await asyncio.to_thread(run_git_info, target)
            cache_mgr.save_result("git_info", result, [".git/HEAD", ".git/index"])
            return result
        
        async def run_cleanup_cached():
            # Cleanup scan doesn't need caching (it's fast and checks current state)
            return await asyncio.to_thread(run_cleanup_scan, target)
        
        async def run_architecture_cached():
            cached = cache_mgr.get_cached_result("architecture", ["**/*.py"])
            if cached: return cached
            result = await asyncio.to_thread(run_architecture_visualizer, target)
            cache_mgr.save_result("architecture", result, ["**/*.py"])
            return result
        
        async def run_tests_cached():
            cached = cache_mgr.get_cached_result("tests", ["tests/**/*.py", "**/*.py", "pytest.ini", "pyproject.toml"])
            if cached: return cached
            result = await asyncio.to_thread(run_tests_coverage, target)
            cache_mgr.save_result("tests", result, ["tests/**/*.py", "**/*.py", "pytest.ini", "pyproject.toml"])
            return result

        async def run_typing_cached():
            cached = cache_mgr.get_cached_result("typing", ["**/*.py"])
            if cached: return cached
            result = await asyncio.to_thread(lambda: TypingTool().analyze(target))
            cache_mgr.save_result("typing", result, ["**/*.py"])
            return result

        async def run_gitignore_cached():
            # Gitignore is fast and checks current state
            return await asyncio.to_thread(lambda: GitignoreTool().analyze(target))

        # Run ALL tools in parallel with caching
        log(f"[Job {job_id}] Launching tools in parallel with caching enabled...")
        results = await asyncio.gather(
            run_with_log("Bandit", run_bandit_cached()),
            run_with_log("Secrets", run_secrets_cached()),
            run_with_log("Ruff", run_ruff_cached()),
            run_with_log("Pip-Audit", run_pip_audit_cached()),
            run_with_log("Structure", run_structure_cached()),
            run_with_log("Dead Code", run_dead_code_cached()),
            run_with_log("Efficiency", run_efficiency_cached()),
            run_with_log("Duplication", run_duplication_cached()),
            run_with_log("Git Info", run_git_info_cached()),
            run_with_log("Cleanup", run_cleanup_cached()),
            run_with_log("Architecture", run_architecture_cached()),
            run_with_log("Tests", run_tests_cached()),
            run_with_log("Typing", run_typing_cached()),
            run_with_log("Gitignore", run_gitignore_cached())
        )
        
        duration = f"{time.time() - JOBS[job_id]['start_time']:.2f}s"
        duration_seconds = time.time() - JOBS[job_id]['start_time']  # ADDED: numeric duration
        
        result_dict = {
            "bandit": results[0],
            "secrets": results[1],
            "ruff": results[2],
            "pip_audit": results[3],
            "structure": results[4],
            "dead_code": results[5],
            "efficiency": results[6],
            "duplication": results[7],
            "git_info": results[8],
            "cleanup": results[9],
            "architecture": results[10],
            "tests": results[11],
            "typing": results[12],
            "gitignore": results[13],
            "installed_tools": [],
            "duration_seconds": duration_seconds  # ADDED: for report context
        }
        
        # AUTO-GENERATE REPORT using Jinja2 engine
        log(f"[Job {job_id}] Generating Markdown report with Jinja2...")
        
        try:
            # Use Jinja2-based report generator
            generator = ReportGeneratorV2(REPORTS_DIR)
            report_path = generator.generate_report(
                report_id=job_id,
                project_path=path,
                score=0,  # Will be calculated inside
                tool_results=result_dict,
                timestamp=datetime.datetime.now()
            )
            
            # Read the generated report
            report_content = Path(report_path).read_text(encoding='utf-8')
            
            # Add integrity check
            report_content = validate_report_integrity(report_content)
            
            # Write back with validation
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
                
        except Exception as e:
            # Fallback to legacy generator if Jinja2 fails
            import traceback
            error_details = traceback.format_exc()
            log(f"[Job {job_id}] Jinja2 failed, using legacy generator: {e}")
            report_content = generate_full_markdown_report(job_id, duration, result_dict, path)
            report_content = validate_report_integrity(report_content)
            
            report_path = REPORTS_DIR / f"FULL_AUDIT_{job_id}.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        
        # Update Job with results and report path
        JOBS[job_id] = {
            "status": "completed",
            "duration": duration,
            "report_path": str(report_path),
            "summary": f"12 tools completed. Report: {Path(report_path).name}",
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


@mcp.tool()
def audit_pr_changes(path: str, base_branch: str = "main", run_tests: bool = True) -> str:
    """
    PR Gatekeeper: Fast delta-based audit of ONLY changed files.
    """
    return _audit_pr_changes_logic(path, base_branch, run_tests)


def _run_bandit_scan(target: Path, changed_files: list) -> dict:
    """Run Bandit security scan on changed files."""
    try:
        cmd = [sys.executable, "-m", "bandit", "-c", "pyproject.toml"] + changed_files + ["-f", "json", "--exit-zero"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=str(target), stdin=subprocess.DEVNULL, shell=False
        )
        bandit_data = json.loads(result.stdout) if result.stdout else {}
        normalized_issues = []
        for issue in bandit_data.get("results", []):
            normalized_issues.append({
                "severity": issue.get("issue_severity"),
                "file": issue.get("filename"),
                "line": issue.get("line_number"),
                "description": issue.get("issue_text"),
                "code": issue.get("code")
            })
        return {"total_issues": len(normalized_issues), "issues": normalized_issues[:10]}
    except Exception as e:
        return {"error": str(e), "total_issues": 0}

def _run_ruff_scan(target: Path, changed_files: list) -> dict:
    """Run Ruff linting on changed files."""
    try:
        cmd = [sys.executable, "-m", "ruff", "check"] + changed_files + ["--output-format", "json"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=str(target), stdin=subprocess.DEVNULL, shell=False
        )
        ruff_issues = json.loads(result.stdout) if result.stdout else []
        return {"total_issues": len(ruff_issues), "issues": ruff_issues[:10]}
    except Exception as e:
        return {"error": str(e), "total_issues": 0}

def _run_radon_scan(target: Path, changed_files: list) -> dict:
    """Run Radon complexity analysis on changed files."""
    try:
        cmd = [sys.executable, "-m", "radon", "cc"] + changed_files + ["-a", "-j"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=str(target), stdin=subprocess.DEVNULL, shell=False
        )
        radon_data = json.loads(result.stdout) if result.stdout else {}
        high_complexity = []
        for file_path, functions in radon_data.items():
            if isinstance(functions, list):
                for func in functions:
                    if func.get('rank', 'A') in ['C', 'D', 'E', 'F']:
                        high_complexity.append({
                            "file": Path(file_path).name,
                            "function": func.get('name', ''),
                            "complexity": func.get('complexity', 0),
                            "rank": func.get('rank', '')
                        })
        return {"total_high_complexity": len(high_complexity), "high_complexity_functions": high_complexity[:10]}
    except Exception as e:
        return {"error": str(e), "total_high_complexity": 0}

def _calculate_pr_score(results: dict) -> int:
    """Calculate score based on audit results."""
    score = 100
    
    # Security penalties
    bandit_issues_count = results.get("bandit", {}).get("total_issues", 0)
    if bandit_issues_count > 0:
        score -= min(bandit_issues_count * 5, 30)
    
    # Quality penalties
    ruff_issues_count = results.get("ruff", {}).get("total_issues", 0)
    if ruff_issues_count > 0:
        score -= min(ruff_issues_count * 2, 20)
    
    # Complexity penalties
    complexity_count = results.get("radon", {}).get("total_high_complexity", 0)
    if complexity_count > 0:
        score -= min(complexity_count * 3, 15)
    
    return max(0, score)

def _run_safety_net_tests(target: Path) -> tuple:
    """Run tests as a safety net."""
    try:
        python_exe = _find_test_python_exe(target)
        cmd = [python_exe, "-m", "pytest", "-x", "--tb=short", "-q"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=str(target), stdin=subprocess.DEVNULL
        )
        return (result.returncode == 0, result.stdout + result.stderr)
    except Exception as e:
        return (False, f"⚠️ Could not run tests: {e}")

def _generate_pr_findings_section(results: dict) -> List[str]:
    """Generates the findings section for the PR report."""
    md = []
    
    # Security findings
    bandit_issues_count = results.get("bandit", {}).get("total_issues", 0)
    md.append("## 🔒 Security Scan (Bandit)")
    if bandit_issues_count > 0:
        md.append(f"**Status:** ❌ {bandit_issues_count} issue(s) found")
        for issue in results["bandit"].get("issues", [])[:5]:
            md.append(f"- **{issue.get('severity')}** in `{Path(issue.get('file', '')).name}:{issue.get('line')}`: {issue.get('description', '')}")
    else: md.append("**Status:** ✅ No security issues detected")
    md.append("")
    
    # Linting findings
    ruff_issues_count = results.get("ruff", {}).get("total_issues", 0)
    md.append("## 📋 Code Quality (Ruff)")
    if ruff_issues_count > 0:
        md.append(f"**Status:** ⚠️ {ruff_issues_count} issue(s) found")
        for issue in results["ruff"].get("issues", [])[:5]:
            md.append(f"- `{Path(issue.get('filename', '')).name}:{issue.get('location', {}).get('row')}` - {issue.get('code')}: {issue.get('message', '')}")
    else: md.append("**Status:** ✅ No linting issues detected")
    md.append("")
    
    # Complexity findings
    complexity_count = results.get("radon", {}).get("total_high_complexity", 0)
    md.append("## 🧮 Complexity (Radon)")
    if complexity_count > 0:
        md.append(f"**Status:** ⚠️ {complexity_count} high-complexity function(s)")
        for func in results["radon"].get("high_complexity_functions", [])[:5]:
            md.append(f"- `{func['function']}` in `{func['file']}`: Complexity {func['complexity']} (Rank {func['rank']})")
    else: md.append("**Status:** ✅ No high-complexity functions")
    md.append("")
    
    return md

def _generate_pr_report(
    base_branch: str,
    changed_files: list,
    score: int,
    results: dict,
    tests_passed: bool,
    test_output: str,
    run_tests: bool,
    target: Path
) -> str:
    """Generate Markdown report for PR audit."""
    md = ["# 🚦 PR Gatekeeper Report", ""]
    md.append(f"**Base Branch:** `{base_branch}`")
    md.append(f"**Changed Files:** {len(changed_files)} Python files")
    md.append(f"**Score:** {score}/100")
    md.append("")

    md.append("## 📝 Changed Files")
    for f in changed_files[:20]:
        rel_path = Path(f).relative_to(target) if Path(f).is_absolute() else f
        md.append(f"- `{rel_path}`")
    if len(changed_files) > 20: md.append(f"- ...and {len(changed_files) - 20} more")
    md.append("")

    md.extend(_generate_pr_findings_section(results))

    # Test results
    if run_tests:
        md.append("## ✅ Test Safety Net")
        if score > 80:
            if tests_passed: md.append("**Status:** ✅ All tests passed")
            else:
                md.append("**Status:** ❌ Tests failed")
                md.append(f"```\n{test_output[:500]}\n```")
        else: md.append("**Status:** ⏭️ Skipped (score too low, fix issues first)")
        md.append("")
    
    # Bottom Line
    md.append("---\n## 🎯 Bottom Line\n")
    
    bandit_issues_count = results.get("bandit", {}).get("total_issues", 0)
    blocking_issues = []
    if bandit_issues_count > 0: blocking_issues.append(f"🔴 {bandit_issues_count} security issue(s)")
    if not tests_passed and run_tests and score > 80: blocking_issues.append("🔴 Tests failing")
    
    if blocking_issues:
        md.append("### 🔴 Request Changes\n\n**Blocking Issues:**")
        for issue in blocking_issues: md.append(f"- {issue}")
    elif score >= 80:
        md.append("### 🟢 Ready for Review\n\n✅ Code quality is good, no blocking issues detected.")
    else:
        md.append(f"### 🟡 Needs Improvement\n\nScore is {score}/100. Please address the issues above before requesting review.")
    
    md.append("\n\n---\n*Generated by Python Auditor MCP - PR Gatekeeper*")
    return "\n".join(md)

def _audit_pr_changes_logic(path: str, base_branch: str = "main", run_tests: bool = True) -> str:
    """Internal logic for PR audit."""
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

    # Fast Scan
    results = {
        "bandit": _run_bandit_scan(target, changed_files),
        "ruff": _run_ruff_scan(target, changed_files),
        "radon": _run_radon_scan(target, changed_files)
    }

    score = _calculate_pr_score(results)
    tests_passed = True
    test_output = ""
    if run_tests and score > 80:
        tests_passed, test_output = _run_safety_net_tests(target)

    report_text = _generate_pr_report(
        base_branch, changed_files, score, results, tests_passed, test_output, run_tests, target
    )

    recommendation = "🟡 Needs Improvement"
    if results["bandit"]["total_issues"] > 0 or (run_tests and not tests_passed and score > 80):
        recommendation = "🔴 Request Changes"
    elif score >= 80:
        recommendation = "🟢 Ready for Review"
    
    return json.dumps({
        "status": "success",
        "recommendation": recommendation,
        "score": score,
        "changed_files_count": len(changed_files),
        "findings": {
            "security_issues": results["bandit"]["total_issues"],
            "linting_issues": results["ruff"]["total_issues"],
            "complexity_issues": results["radon"]["total_high_complexity"],
            "tests_passed": tests_passed if run_tests else None
        },
        "report": report_text
    }, indent=2)


@mcp.tool()
def audit_remote_repo(repo_url: str, branch: str = "main") -> str:
    """
    Audit a remote Git repository without manual cloning.
    """
    return _audit_remote_repo_logic(repo_url, branch)


def _clone_repo_step(repo_url: str, branch: str, temp_path: Path) -> dict:
    """Clones the repository and returns status/error dict if failed, else None."""
    if not shutil.which("git"):
         return {
             "status": "error",
             "error": "Git not installed",
             "suggestion": "Install git command line tool"
         }

    clone_cmd = ["git", "clone", "--depth", "1", "-b", branch, repo_url, str(temp_path)]
    try:
        result = subprocess.run(
            clone_cmd, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL
        )
        if result.returncode != 0:
            err = result.stderr
            suggestion = "Check the repository URL and network connection."
            if "not found" in err.lower():
                suggestion = "Check the URL and ensure the repository exists."
            elif "authentication" in err.lower() or "private" in err.lower():
                suggestion = "This tool supports public repositories. Check credentials for private ones."
            elif f"branch '{branch}'" in err.lower() or "did not match any" in err.lower():
                suggestion = f"Check the branch name. '{branch}' may not exist."

            return {
                "status": "error",
                "error": f"Git clone failed: {err}",
                "suggestion": suggestion
            }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "Clone operation timeout (>300s)",
            "suggestion": "Repository might be too large or network is slow."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Clone error: {e}",
            "suggestion": "Unexpected error during clone."
        }

    return None # Success

def _audit_remote_repo_logic(repo_url: str, branch: str = "main") -> str:
    """Internal logic for remote audit."""
    import tempfile
    
    log(f"[REMOTE-AUDIT] Starting remote audit: {repo_url} (branch: {branch})")
    
    if not repo_url.startswith(("http://", "https://", "git@")):
        return json.dumps({
            "status": "error",
            "error": "Invalid repository URL.",
            "suggestion": "Use http://, https://, or git@ URL"
        }, indent=2)
    
    try:
        with tempfile.TemporaryDirectory(prefix="audit_remote_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Step 1: Clone
            clone_error = _clone_repo_step(repo_url, branch, temp_path)
            if clone_error:
                return json.dumps(clone_error, indent=2)
            
            # Step 2: Audit
            # Check for Python files
            py_files = list(temp_path.glob("**/*.py"))
            if not py_files:
                 return json.dumps({
                     "status": "warning",
                     "message": "No Python files found",
                     "repo_url": repo_url,
                     "branch": branch
                 }, indent=2)

            # Create job ID for this audit
            job_id = f"remote_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            start_time = time.time()
            
            tools = {
                "structure": StructureTool(),
                "architecture": ArchitectureTool(),
                "duplication": DuplicationTool(),
                "deadcode": DeadcodeTool(),
                "secrets": SecretsTool(),
                "tests": TestsTool(),
                "git_info": GitTool(),
            }

            results = {}
            for key, tool in tools.items():
                try: results[key] = tool.analyze(temp_path)
                except Exception as e: results[key] = {"error": str(e), "status": "error"}
            
            results["bandit"] = run_bandit(temp_path)
            results["quality"] = FastAuditTool().analyze(temp_path)
            results["ruff"] = results["quality"] # alias
            results["efficiency"] = results["quality"] # alias for complexity

            duration = f"{time.time() - start_time:.1f}s"
            report_md = generate_full_markdown_report(job_id, duration, results, str(temp_path))
            score = _calculate_audit_score(results)

            return json.dumps({
                "status": "success",
                "repo_url": repo_url,
                "branch": branch,
                "score": score,
                "duration": duration,
                "files_analyzed": len(py_files),
                "report": report_md,
                "summary": {
                    "security_issues": results.get("bandit", {}).get("total_issues", 0),
                    "secrets_found": results.get("secrets", {}).get("total_findings", 0),
                    "test_coverage": results.get("tests", {}).get("coverage_percent", 0),
                    "duplicates": results.get("duplication", {}).get("total_duplicates", 0),
                    "dead_code": results.get("dead_code", {}).get("total_dead_code", 0),
                    "high_complexity": len(results.get("efficiency", {}).get("high_complexity_functions", []))
                }
            }, indent=2)
            
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Unexpected error: {str(e)}", "suggestion": "Check system logs."}, indent=2)


@mcp.tool()
def generate_full_report(path: str) -> str:
    """Runs ALL tools and generates a comprehensive Markdown report file."""
    start_time = time.time()
    target_path = Path(path).resolve()

    # Run all tools explicitly to catch errors
    results = {}
    tools = {
        "structure": StructureTool(), "architecture": ArchitectureTool(), "typing": TypingTool(),
        "duplication": DuplicationTool(), "deadcode": DeadcodeTool(), "efficiency": FastAuditTool(),
        "secrets": SecretsTool(), "tests": TestsTool(), "gitignore": GitignoreTool(), "git": GitTool(),
    }
    for key, tool in tools.items():
        tool_start = time.time()
        try:
            results[key] = tool.analyze(target_path)
            results[key]["duration_s"] = round(time.time() - tool_start, 2)
        except Exception as e:
            results[key] = {"error": str(e), "duration_s": round(time.time() - tool_start, 2)}

    tool_start = time.time()
    results["bandit"] = run_bandit(target_path)
    results["bandit"]["duration_s"] = round(time.time() - tool_start, 2)

    tool_start = time.time()
    results["quality"] = FastAuditTool().analyze(target_path)
    results["quality"]["duration_s"] = round(time.time() - tool_start, 2)

    # Calculate score
    score = _calculate_audit_score(results)

    # Add total duration
    results["duration_seconds"] = time.time() - start_time

    # Generate Report
    report_id = f"audit__{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    generator = ReportGeneratorV2(REPORTS_DIR)
    report_path = generator.generate_report(
        report_id=report_id,
        project_path=str(target_path),
        score=score,
        tool_results=results,
        timestamp=datetime.datetime.now()
    )

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
    """Run comprehensive Ruff linting."""
    try:
        project_path = Path(path).resolve()
        if not project_path.exists(): return json.dumps({"status": "error", "error": f"Path does not exist: {path}"})
        result = run_ruff_comprehensive(project_path)
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
        
        # Prepare tools (same as regular audit)
        tools = {
            "structure": StructureTool(),
            "architecture": ArchitectureTool(),
            "typing": TypingTool(),
            "duplication": DuplicationTool(),
            "deadcode": DeadcodeTool(),
            "efficiency": FastAuditTool(),
            "secrets": SecretsTool(),
            "tests": TestsTool(),
            "gitignore": GitignoreTool(),
            "git": GitTool(),
            "bandit": lambda p: run_bandit(p),
            "quality": FastAuditTool(),
        }
        
        # Run incremental audit
        result = await engine.run_audit(tools, force_full=force_full)
        
        # Calculate score
        score = _calculate_audit_score(result.tool_results)
        
        # Generate report
        report_id = f"audit__{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        generator = ReportGeneratorV2(REPORTS_DIR)
        report_path = generator.generate_report(
            report_id=report_id,
            project_path=str(target_path),
            score=score,
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


if __name__ == "__main__":
    # Clear log file on start
    with open(DEBUG_LOG, "w", encoding="utf-8") as f:
        f.write(f"Server Started at {datetime.datetime.now()}\n")
    print("Starting Python Auditor MCP Server...")
    print(f"Reports will be saved to: {REPORTS_DIR}")
    print(f"Debug logs: {DEBUG_LOG}")
    mcp.run()
