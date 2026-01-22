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
    import shutil
    import subprocess
    
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
    """
    Run Ruff with all rule categories to replace multiple tools.
    
    Replaces:
    - Bandit (security) → ruff --select S
    - pycodestyle → ruff --select E,W
    - isort → ruff --select I
    - pyflakes → ruff --select F
    - McCabe complexity → ruff --select C90
    - pydocstyle → ruff --select D
    
    Returns results categorized by type for backward compatibility.
    """
    
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
    import subprocess
    import json
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
    import subprocess
    import json
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
    import subprocess
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
            return {"tool": "ruff", "status": "error", "error": "Timeout (>60s)", "issues": []}
        
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
    import subprocess
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


def run_structure(path: Path) -> dict:
    """Analyze project structure and generate a tree view."""
    try:
        p = Path(path)
        
        # Use os.walk with proper exclusions instead of glob (case-insensitive)
        exclude_dirs_lower = {
            "htmlcov", "reports", "site-packages", "node_modules", 
            ".git", "__pycache__", ".venv", "venv", ".idea", ".vscode", 
            "build", "dist", ".pytest_cache", ".mypy_cache", "env", ".env",
            "fresh-install-test", "eggs", ".eggs", "lib", "lib64"
        }
        
        py_files = []
        for root, dirs, files in os.walk(p):
            # Skip excluded directories (case-insensitive, in-place modification)
            dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs_lower and not d.startswith(".")]
            py_files.extend([Path(root) / f for f in files if f.endswith(".py")])
        
        # Fast line counting (binary mode is faster)
        total_lines = 0
        if len(py_files) < 2000:
            for f in py_files:
                try:
                    with open(f, 'rb') as fp:
                        total_lines += sum(1 for _ in fp)
                except: pass  # nosec B110
        
        # Generate Tree (reuse same exclusions, case-insensitive)
        tree_lines = []
        
        def _generate_tree(directory, prefix="", depth=0):
            if depth > 3: return # Max depth
            
            items = []
            try:
                for x in directory.iterdir():
                    # Case-insensitive exclusion check
                    if x.name.lower() in exclude_dirs_lower: continue
                    if x.name.startswith('.'): continue
                    if x.is_file() and x.suffix in {'.pyc', '.pyo', '.html', '.js', '.css'}: continue # Skip report artifacts
                    items.append(x)
            except PermissionError: return

            items.sort(key=lambda x: (x.is_file(), x.name))
            
            count = len(items)
            for i, item in enumerate(items):
                is_last = i == count - 1
                connector = "└── " if is_last else "├── "
                
                icon = "📁" if item.is_dir() else "🐍" if item.suffix == ".py" else "📄"
                tree_lines.append(f"{prefix}{connector}{icon} {item.name}")
                
                if item.is_dir():
                    extension = "    " if is_last else "│   "
                    _generate_tree(item, prefix + extension, depth + 1)

        _generate_tree(p)
        
        # Cap tree size
        tree_str = "\n".join(tree_lines[:100])
        if len(tree_lines) > 100:
            tree_str += "\n... (truncated for brevity)"

        top_dirs = [d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        return {
            "tool": "structure",
            "status": "analyzed",
            "total_py_files": len(py_files),
            "total_lines": total_lines,
            "top_directories": top_dirs[:20],
            "directory_tree": tree_str
        }
    except Exception as e:
        return {"tool": "structure", "status": "error", "error": str(e)}


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
    import subprocess
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
        
        for pattern in cleanup_targets.keys():
            for d in path.glob(f"**/{pattern}"):
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


def run_tests_coverage(path: Path) -> dict:
    """Run pytest with coverage to analyze test suite."""
    import subprocess
    import re
    
    try:
        target_path = Path(path).resolve()
        
        # Detect virtual environment python executable
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
        
        # Count test files by category (smart detection)
        unit_tests = list(target_path.glob("**/test_*.py")) + list(target_path.glob("**/tests/unit/**/*.py"))
        integration_tests = list(target_path.glob("**/tests/integration/**/*.py")) + list(target_path.glob("**/test_integration_*.py"))
        e2e_tests = list(target_path.glob("**/tests/e2e/**/*.py")) + list(target_path.glob("**/test_e2e_*.py"))
        
        # Remove duplicates and categorize
        all_test_files = set()
        unit_count = 0
        integration_count = 0
        e2e_count = 0
        
        # Categorize by path/name
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
        
        test_breakdown = {
            "unit": unit_count,
            "integration": integration_count,
            "e2e": e2e_count,
            "total_files": len(all_test_files)
        }
        
        return {
            "tool": "pytest",
            "status": "success" if result.returncode in [0, 1] else "error",
            "coverage_percent": coverage_percent,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "test_breakdown": test_breakdown,
            "python_exe": python_exe
        }
        
    except subprocess.TimeoutExpired:
        return {"tool": "pytest", "status": "error", "error": "Timeout (>300s)", "coverage_percent": 0}
    except FileNotFoundError:
        return {"tool": "pytest", "status": "skipped", "error": "pytest not installed", "coverage_percent": 0}
    except Exception as e:
        return {"tool": "pytest", "status": "error", "error": str(e), "coverage_percent": 0}


def run_architecture_visualizer(path: Path) -> dict:
    """
    Generate a Mermaid.js dependency graph by parsing Python imports.
    Pure Python implementation using AST - groups nodes into subgraphs by directory.
    """
    import ast
    from collections import defaultdict
    
    # Standard library modules to filter out
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
    
    try:
        p = Path(path)
        py_files = list(p.glob("**/*.py"))
        
        # Skip common non-source directories
        py_files = [f for f in py_files if not any(
            skip in str(f) for skip in [
                'venv', '.venv', 'node_modules', '__pycache__', 
                '.git', 'site-packages', 'external_libs', 'htmlcov'
            ]
        )]
        
        dependencies = []  # List of (source, target) tuples
        file_nodes = set()
        nodes_by_group = defaultdict(set)  # Group nodes by top-level directory
        
        for py_file in py_files[:50]:  # Limit to avoid huge graphs
            try:
                source_code = py_file.read_text(encoding='utf-8', errors='ignore')
                tree = ast.parse(source_code)
                
                # Get relative path for cleaner names
                try:
                    rel_path = py_file.relative_to(p)
                except ValueError:
                    rel_path = py_file.name
                
                source_name = str(rel_path).replace('\\', '/').replace('.py', '')
                file_nodes.add(source_name)
                
                # Group by top-level directory
                parts = source_name.split('/')
                if len(parts) > 1:
                    group = parts[0]  # e.g., "app", "tests", "data"
                else:
                    group = "root"  # Root-level files
                
                nodes_by_group[group].add(source_name)
                
                for node in ast.walk(tree):
                    target_module = None
                    
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            target_module = alias.name.split('.')[0]
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            target_module = node.module.split('.')[0]
                    
                    # Filter out stdlib and add internal dependencies
                    if target_module and target_module not in STDLIB_MODULES:
                        # Check if it's likely an internal module
                        if target_module in [f.stem for f in py_files] or '.' not in target_module:
                            dependencies.append((source_name, target_module))
            
            except (SyntaxError, UnicodeDecodeError):
                continue
        
        # Generate Mermaid graph with subgraphs
        mermaid_lines = ["graph TD"]
        
        # Create subgraphs for each group
        for group_name, nodes in sorted(nodes_by_group.items()):
            if not nodes:
                continue
                
            # Capitalize group name for display
            display_name = group_name.replace('_', ' ').title()
            mermaid_lines.append(f"    subgraph {display_name}")
            
            for node in sorted(nodes):
                clean_node = node.replace('/', '_').replace('-', '_')
                mermaid_lines.append(f"        {clean_node}[{node}]")
            
            mermaid_lines.append("    end")
        
        # Add edges (dependencies) after all subgraphs
        seen_edges = set()
        for source, target in dependencies[:100]:  # Limit edges
            edge = f"{source}-->{target}"
            if edge not in seen_edges and source != target:
                seen_edges.add(edge)
                # Clean names for Mermaid (replace special chars)
                clean_source = source.replace('/', '_').replace('-', '_')
                clean_target = target.replace('/', '_').replace('-', '_')
                mermaid_lines.append(f"    {clean_source} --> {clean_target}")
        
        mermaid_graph = "\n".join(mermaid_lines) if len(mermaid_lines) > 1 else "graph TD\n    Note[No internal dependencies found]"
        
        return {
            "tool": "architecture",
            "status": "analyzed",
            "total_files": len(py_files),
            "total_dependencies": len(seen_edges),
            "mermaid_graph": mermaid_graph,
            "nodes": list(file_nodes)[:30]
        }
    
    except Exception as e:
        return {"tool": "architecture", "status": "error", "error": str(e)}


def generate_full_markdown_report(job_id: str, duration: str, results: dict, path: str) -> str:
    """Generate a rich, dashboard-style Markdown report."""
    import datetime
    from pathlib import Path
    
    # --- Weighted Scoring Algorithm ---
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
    
    # 5. Ensure floor
    score = max(0, score)
    
    # Updated emoji thresholds (stricter)
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

    # --- Self Healing ---
    md.append("## 🔧 Self-Healing Status")
    md.append("**Status:** Healthy ✅ (No missing tools detected)") 
    md.append("")

    # --- Tool Execution Summary ---
    md.append("## 📊 Tool Execution Summary")
    md.append("")
    md.append("| Tool | Status | Details |")
    md.append("|------|--------|----------|")
    
    # Helper to format status
    def tool_status(result):
        status = result.get("status", "unknown")
        if status == "clean":
            return "✅ Pass"
        elif status == "issues_found":
            return "❌ Fail"
        elif status == "error":
            return "⚠️ Error"
        elif status == "skipped":
            return "⏭️ Skip"
        else:
            return "ℹ️ Info"
    
    # Map each tool
    tools_summary = [
        ("📁 Structure", results.get("structure", {}), lambda r: f"{r.get('total_py_files', 0)} files, {r.get('total_directories', 0)} dirs"),
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
        except:
            details = "N/A"
        md.append(f"| {tool_name} | {status_str} | {details} |")
    
    md.append("")

    # --- Top Priorities ---
    md.append("## 🚨 Top Priorities")
    priorities = []
    if bandit_issues:
        priorities.append("🔴 **Security:** Critical vulnerabilities found.")
    
    if cov < 50:
        priorities.append(f"🟡 **Testing:** Very low coverage ({cov}%)")
    
    if not priorities:
        md.append("✅ No critical priority fixes needed.")
    else:
        for i, p in enumerate(priorities, 1):
            md.append(f"{i}. {p}")
    md.append("")

    # --- Structure ---
    md.append("")
    
    try:
        md.append("## 📂 Project Structure")
        struct = results.get("structure", {})
        md.append(f"**Files:** {struct.get('total_py_files', 0)} Python | **Lines:** {struct.get('total_lines', 0)}")
        
        if struct.get("directory_tree"):
            md.append("### 📁 Tree View")
            md.append("```")
            md.append(struct.get("directory_tree"))
            md.append("```")
        else:
            md.append("### Top Directories")
            for d in struct.get("top_directories", [])[:10]:
                md.append(f"- `/{d}`")
        md.append("")
    except Exception as e:
         log(f"Error in Structure section: {e}")
         md.append(f"Error rendering structure: {e}")

    # --- Architecture ---
    md.append("## 🗺️ Architecture Logic")
    if results.get("architecture", {}).get("mermaid_graph"):
        graph = results["architecture"]["mermaid_graph"]
        md.append("```mermaid")
        md.append(graph)
        md.append("```")
        
        # Mermaid Live Link (Pako Compressed)
        try:
            import json
            import zlib
            import base64
            
            state = {"code": graph, "mermaid": {"theme": "default"}}
            json_str = json.dumps(state)
            compressed = zlib.compress(json_str.encode('utf-8'), level=9)
            encoded = base64.urlsafe_b64encode(compressed).decode('ascii')
            
            live_url = f"https://mermaid.live/edit#pako:{encoded}"
            md.append(f"[🔍 **Open Interactive Graph**]({live_url})")
        except Exception: 
            pass  # nosec B110
    else:
        md.append("_No architecture graph generated._")
    md.append("")

    # --- Findings ---
    md.append("## 📊 Detailed Findings")
    
    # Security
    md.append(f"### 🛡️ Security ({len(bandit_issues)} issues)")
    if not bandit_issues:
        md.append("✅ No security issues found.")
    else:
        md.append("| Severity | Type | File | Description |")
        md.append("|----------|------|------|-------------|")
        for issue in bandit_issues[:10]:
            try:
                fname = Path(issue.get('file', '')).name
            except Exception:
                fname = issue.get('file', 'unknown')
            md.append(f"| {issue.get('severity')} | {issue.get('type')} | `{fname}:{issue.get('line')}` | {issue.get('description','')} |")
    md.append("")

    # Quality
    md.append("### 🧹 Code Quality & Hygiene")
    
    # Dead Code
    dead = results.get("dead_code", {}).get("items", [])
    md.append(f"**💀 Dead Code / Unused ({len(dead)} items)**")
    if dead:
        for item in dead[:10]: # Limit to top 10
            md.append(f"- `{item}`")
        if len(dead) > 10: md.append(f"- ... and {len(dead)-10} more")
    else:
        md.append("✅ Clean.")
    md.append("")

    # Complexity Table
    complex_funcs = results.get("efficiency", {}).get("high_complexity_functions", [])
    md.append("**🤯 Complex Functions (Radon)**")
    if complex_funcs:
        md.append("| File | Function | Rank | Score |")
        md.append("|---|---|---|---|")
        for f in complex_funcs:
            try:
                fname = Path(f.get('file','')).name
            except Exception:
                fname = f.get('file', 'unknown')
            md.append(f"| {fname} | {f.get('function')} | {f.get('rank')} | {f.get('complexity')} |")
    else:
        md.append("✅ No complex functions detected.")
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
    else:
        md.append("✅ No code duplication found.")
    md.append("")

    # Cleanup
    cleanup = results.get("cleanup", {})
    total_mb = cleanup.get("total_size_mb", 0)
    md.append("**🗑️ Junk / Cleanup**")
    md.append(f"- **Total Reclaimable:** {total_mb} MB")
    for target, count in cleanup.get("cleanup_targets", {}).items():
        md.append(f"  - `{target}`: {count} items")
    md.append("")

    # Tests
    tests = results.get("tests", {})
    test_breakdown = tests.get("test_breakdown", {})
    total_test_files = test_breakdown.get("total_files", 0)
    
    md.append("### 🧪 Tests & Coverage")
    md.append("")
    md.append(f"**Files Found:** {total_test_files} test files")
    md.append(f"**Coverage:** {tests.get('coverage_percent', 0)}%")
    md.append("")
    md.append(f"**Test Results:**")
    md.append(f"- Passed: {tests.get('tests_passed', 0)} ✅")
    md.append(f"- Failed: {tests.get('tests_failed', 0)} ❌")
    md.append("")
    
    # Test Type Breakdown
    md.append("**Test Types:**")
    unit_count = test_breakdown.get("unit", 0)
    integration_count = test_breakdown.get("integration", 0)
    e2e_count = test_breakdown.get("e2e", 0)
    
    md.append(f"- Unit: {'✅' if unit_count > 0 else '❌'} ({unit_count} files)")
    md.append(f"- Integration: {'✅' if integration_count > 0 else '❌'} ({integration_count} files)")
    md.append(f"- E2E: {'✅' if e2e_count > 0 else '❌'} ({e2e_count} files)")
    
    # Recommendations
    if total_test_files == 0:
        md.append("")
        md.append("👉 **Fix:** No tests found. Create tests in `tests/` directory or using `test_*.py` naming.")
    elif tests.get('coverage_percent', 0) < 80:
        md.append("")
        md.append(f"👉 **Recommendation:** Increase coverage (current: {tests.get('coverage_percent', 0)}%). Run: `pytest --cov=. --cov-report=term-missing`")
    
    md.append("")

    # --- Git Status / Recent Changes ---
    git_info = results.get("git_info", {})
    md.append("### 📝 Recent Changes")
    md.append("")
    
    if git_info.get("status") in ["analyzed", "clean"]:
        last_commit = git_info.get("last_commit", {})
        branch = git_info.get("branch", git_info.get("current_branch", "unknown"))
        uncommitted = git_info.get("uncommitted_changes", 0)
        
        # Last Commit Info
        if last_commit:
            commit_hash = last_commit.get("hash", "")
            commit_msg = last_commit.get("message", "")
            commit_author = last_commit.get("author", "")
            commit_when = last_commit.get("when", "")
            
            md.append(f"**Last Commit:** `{commit_hash}` - {commit_author}, {commit_when}")
            md.append(f"*\"{commit_msg}\"*")
        else:
            md.append("**Last Commit:** No commits yet")
        
        md.append("")
        
        # Status
        if uncommitted > 0:
            md.append(f"**Status:** ⚠️ {uncommitted} uncommitted change(s)")
        else:
            md.append("**Status:** ✅ Clean working directory")
        
        # Branch
        md.append(f"**Branch:** `{branch}`")
    else:
        md.append("ℹ️ Not a git repository or git not available")
    
    md.append("")
    
    md.append("\n---\n*Generated by Python Auditor MCP v2.1*")
    
    return "\n".join(md)
    



def validate_report_integrity(report_content: str) -> str:
    """Ensures report has all required sections (Security, Quality, Duplication, Tests)."""
    required = [
        "## 📂 Project Structure",
        "## 📊 Detailed Findings",
        "### 🛡️ Security",
        "#### 🎭 DUPLICATES",
        "## 🧪 Test Coverage"
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
            if cached:
                return cached
            result = await asyncio.to_thread(run_bandit, target)
            cache_mgr.save_result("bandit", result, ["**/*.py"])
            return result
        
        async def run_secrets_cached():
            cached = cache_mgr.get_cached_result("secrets", ["**/*"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_secrets, target)
            cache_mgr.save_result("secrets", result, ["**/*"])
            return result
        
        async def run_ruff_cached():
            cached = cache_mgr.get_cached_result("ruff", ["**/*.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_ruff, target)
            cache_mgr.save_result("ruff", result, ["**/*.py"])
            return result
        
        async def run_ruff_comprehensive_cached():
            """Use comprehensive Ruff to replace multiple tools (Bandit, pycodestyle, etc.)."""
            cached = cache_mgr.get_cached_result("ruff_comprehensive", ["**/*.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_ruff_comprehensive, target)
            cache_mgr.save_result("ruff_comprehensive", result, ["**/*.py"])
            return result
        
        async def run_pip_audit_cached():
            cached = cache_mgr.get_cached_result("pip_audit", ["requirements.txt", "pyproject.toml", "setup.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_pip_audit, target)
            cache_mgr.save_result("pip_audit", result, ["requirements.txt", "pyproject.toml", "setup.py"])
            return result
        
        async def run_structure_cached():
            cached = cache_mgr.get_cached_result("structure", ["**/*.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_structure, target)
            cache_mgr.save_result("structure", result, ["**/*.py"])
            return result
        
        async def run_dead_code_cached():
            cached = cache_mgr.get_cached_result("dead_code", ["**/*.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_dead_code, target)
            cache_mgr.save_result("dead_code", result, ["**/*.py"])
            return result
        
        async def run_efficiency_cached():
            cached = cache_mgr.get_cached_result("efficiency", ["**/*.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_efficiency, target)
            cache_mgr.save_result("efficiency", result, ["**/*.py"])
            return result
        
        async def run_duplication_cached():
            cached = cache_mgr.get_cached_result("duplication", ["**/*.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_duplication, target)
            cache_mgr.save_result("duplication", result, ["**/*.py"])
            return result
        
        async def run_git_info_cached():
            # Git info changes frequently, use shorter cache (5 minutes)
            cached = cache_mgr.get_cached_result("git_info", [".git/HEAD", ".git/index"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_git_info, target)
            cache_mgr.save_result("git_info", result, [".git/HEAD", ".git/index"])
            return result
        
        async def run_cleanup_cached():
            # Cleanup scan doesn't need caching (it's fast and checks current state)
            return await asyncio.to_thread(run_cleanup_scan, target)
        
        async def run_architecture_cached():
            cached = cache_mgr.get_cached_result("architecture", ["**/*.py"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_architecture_visualizer, target)
            cache_mgr.save_result("architecture", result, ["**/*.py"])
            return result
        
        async def run_tests_cached():
            cached = cache_mgr.get_cached_result("tests", ["tests/**/*.py", "**/*.py", "pytest.ini", "pyproject.toml"])
            if cached:
                return cached
            result = await asyncio.to_thread(run_tests_coverage, target)
            cache_mgr.save_result("tests", result, ["tests/**/*.py", "**/*.py", "pytest.ini", "pyproject.toml"])
            return result

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
            run_with_log("Tests", run_tests_cached())
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
            log(f"[Job {job_id}] Full error traceback:\n{error_details}")
            # ALSO write to file for easier debugging
            try:
                with open("LAST_JINJA_ERROR.txt", "w") as err_f:
                    err_f.write(error_details)
            except Exception:
                pass  # nosec B110
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
    import shutil
    import subprocess
    
    REQUIRED_TOOLS = ["bandit", "ruff", "vulture", "radon", "pip-audit", "pytest", "detect-secrets"]
    missing = []
    
    for tool in REQUIRED_TOOLS:
        # Check PATH first
        if shutil.which(tool):
            continue
            
        # Check Python Module (more reliable on Windows)
        module_name = tool.replace("-", "_")
        try:
            subprocess.run(
                [sys.executable, "-m", module_name, "--version"],
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
    import subprocess
    
    TOOLS_TO_INSTALL = ["bandit", "detect-secrets", "vulture", "radon", "ruff", "pip-audit"]
    
    try:
        log("Installing audit dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + TOOLS_TO_INSTALL,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max
            stdin=subprocess.DEVNULL
        )
        
        if result.returncode == 0:
            log(f"✅ Successfully installed: {', '.join(TOOLS_TO_INSTALL)}")
            return f"✅ **Installation Successful!**\n\nInstalled tools: {', '.join(TOOLS_TO_INSTALL)}\n\nYou can now run the audit."
        else:
            error_msg = result.stderr or result.stdout
            log(f"❌ Installation failed: {error_msg}")
            return f"❌ **Installation Failed**\n\nError: {error_msg[:500]}"
            
    except subprocess.TimeoutExpired:
        return "❌ **Installation Timeout** - Installation took longer than 5 minutes. Please try manually:\n`pip install bandit detect-secrets vulture radon ruff pip-audit`"
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
    for w in warnings:
        log(f"[SANITY CHECK] {w}")
    
    log(f"=== STARTING FULL AUDIT JOB {job_id} for: {path} ===")
    
    # Fire and forget! We do not await this.
    asyncio.create_task(run_audit_background(job_id, path))
    
    response = {
        "status": "started",
        "job_id": job_id,
        "tools": ["Bandit (Security)", "Secrets", "Ruff (Quality)", "Pip-Audit (Dependencies)"],
        "message": "Full audit started. Use 'check_audit_status' with the job_id. Report auto-saves on completion."
    }
    
    if warnings:
        response["warnings"] = warnings
    
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
    
    # If completed or failed, return the full result
    return json.dumps(job, indent=2)


@mcp.tool()
def run_auto_fix(path: str, confirm: bool = False) -> str:
    """
    SAFE Auto-Fix tool with Dry Run and Backup capabilities.
    
    Args:
        path: Path to the project.
        confirm: Set to True to execute changes. Default is False (Dry Run).
                 Dry Run only lists what would happen.
                 Execution creates a backup, cleans junk, fixes style, and commits changes.
    """
    import subprocess
    import shutil
    import datetime
    
    target = Path(path).resolve()
    
    # STEP 0: Check for dirty git state (BEFORE doing anything)
    if confirm:
        try:
            git_check = subprocess.run(
                ["git", "status", "--porcelain"],  # nosec B607
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=10,
                stdin=subprocess.DEVNULL
            )
            
            if git_check.stdout.strip():
                return json.dumps({
                    "status": "error",
                    "error": "❌ **Action Aborted:** You have uncommitted changes. Please commit or stash ('git stash') your work before running Auto-Fix to keep the PR clean.",
                    "dirty_files": git_check.stdout.strip().split('\n')[:10]
                }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": f"Git check failed: {e}. Cannot verify clean state."
            }, indent=2)
    
    # Identify cleanup targets
    cleanup_targets = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov", "dist", "build"]
    files_to_delete = []
    
    for pattern in cleanup_targets:
        for item in target.rglob(pattern):
            if item.is_dir() and "venv" not in str(item) and ".venv" not in str(item):
                files_to_delete.append(str(item.relative_to(target)))
    
    if not confirm:
        # DRY RUN REPORT
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

    # EXECUTION PHASE
    fixes_applied = []
    errors = []
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_zip = None
    branch_name = f"fix/audit-{timestamp}"
    
    # 1. Backup
    try:
        backup_dir = target / ".backups"
        backup_dir.mkdir(exist_ok=True)
        backup_zip = backup_dir / f"backup_{timestamp}"
        
        # Helper to ignore venv in backup (shutil compatible)
        def ignore_patterns(_, files):
            return [f for f in files if f in ['.venv', 'venv', 'node_modules', '.git']]
            
        # Create zip (base_name, format, root_dir)
        shutil.make_archive(str(backup_zip), 'zip', str(target))
        fixes_applied.append(f"Backup created: {backup_zip}.zip")
    except Exception as e:
        return json.dumps({"status": "error", "error": f"Backup failed: {e}. Aborting for safety."})

    # 2. Cleanup
    deleted_count = 0
    for rel_path in files_to_delete:
        try:
            full_path = target / rel_path
            if full_path.exists():
                shutil.rmtree(full_path)
                deleted_count += 1
        except Exception:
            pass  # nosec B110
    if deleted_count:
        fixes_applied.append(f"Cleanup: Deleted {deleted_count} cache directories")

    # 3. Style Fixes (Ruff)
    try:
        # Check --fix
        subprocess.run([sys.executable, "-m", "ruff", "check", ".", "--fix"], 
                      cwd=str(target), capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
        # Format
        subprocess.run([sys.executable, "-m", "ruff", "format", "."], 
                      cwd=str(target), capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
        fixes_applied.append("Code Style: Ran 'ruff check --fix' and 'ruff format'")
    except Exception as e:
        errors.append(f"Ruff fix failed: {e}")

    # 4. Write Log (BEFORE git commit so it's included)
    try:
        log_file = target / "FIX_LOG.md"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n## Auto-Fix {timestamp}\n")
            for fix in fixes_applied:
                f.write(f"- {fix}\n")
            if errors:
                f.write(f"\n**Errors:**\n")
                for err in errors:
                    f.write(f"- {err}\n")
        fixes_applied.append("Log: Updated FIX_LOG.md")
    except Exception as e:
        errors.append(f"Log write failed: {e}")

    # 5. Git Commit (AFTER log writing)
    try:
        git_kwargs = {"cwd": str(target), "capture_output": True, "timeout": 30, "stdin": subprocess.DEVNULL}
        subprocess.run(["git", "checkout", "-b", branch_name], **git_kwargs)  # nosec B607
        subprocess.run(["git", "add", "."], **git_kwargs)  # nosec B607
        commit_msg = f"Auto-fix: {', '.join(fixes_applied[:3])}"
        subprocess.run(["git", "commit", "-m", commit_msg], **git_kwargs)  # nosec B607
        fixes_applied.append(f"Git: Created branch '{branch_name}' with commit")
    except Exception as e:
        errors.append(f"Git commit failed: {e}")

    return json.dumps({
        "status": "completed",
        "timestamp": timestamp,
        "backup": str(backup_zip) + ".zip" if backup_zip else None,
        "branch": branch_name,
        "fixes": fixes_applied,
        "errors": errors
    }, indent=2)
    
@mcp.tool()
def save_report_to_file(job_id: str) -> str:
    """Generates a Markdown report from a completed background job."""
    job = JOBS.get(job_id)
    if not job:
        return json.dumps({"status": "error", "message": f"Job ID '{job_id}' not found."})
    
    if job["status"] != "completed":
        return json.dumps({"status": "error", "message": f"Job is still {job['status']}. Wait for completion."})
    
    result = job["result"]
    bandit = result.get("bandit", {})
    secrets = result.get("secrets", {})
    
    # Start Markdown
    md = ["# Security Audit Report"]
    md.append(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md.append(f"**Scan Duration:** {job.get('duration', 'N/A')}")
    md.append(f"**Files Scanned:** {bandit.get('files_scanned', bandit.get('code_security', {}).get('files_scanned', 0))}")
    md.append("")
    md.append("---")
    md.append("")
    
    # 1. Bandit Results
    issues = bandit.get("issues", bandit.get("code_security", {}).get("issues", []))
    md.append(f"## Python Security Issues ({len(issues)} found)")
    md.append("")
    
    if issues:
        md.append("| Severity | Type | File | Line | Description |")
        md.append("|----------|------|------|------|-------------|")
        for issue in issues[:20]:  # Limit to 20
            fname = Path(issue.get('file', '')).name
            md.append(f"| **{issue.get('severity', 'N/A')}** | {issue.get('type', 'N/A')} | `{fname}` | {issue.get('line', 0)} | {issue.get('description', '')[:60]}... |")
        if len(issues) > 20:
            md.append(f"\n*...and {len(issues) - 20} more issues*")
    else:
        md.append("No security issues found.")
    
    md.append("")
    
    # 2. Secrets Results
    md.append("## Secrets Detection")
    md.append("")
    secrets_status = secrets.get("status", "unknown")
    secrets_count = secrets.get("total_secrets", 0)
    
    if secrets_status == "clean" or secrets_count == 0:
        md.append("No hardcoded secrets found.")
    else:
        md.append(f"**Warning:** Found {secrets_count} potential secrets!")
        for secret in secrets.get("secrets", [])[:10]:
            md.append(f"- `{secret.get('file', '')}:{secret.get('line', 0)}` - {secret.get('type', 'Unknown')}")
    
    md.append("")
    md.append("---")
    md.append(f"*Generated by Python Auditor MCP Server*")
    
    # Save File
    report_path = REPORTS_DIR / f"SECURITY_REPORT_{job_id}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    
    log(f"Report saved to: {report_path}")
    return json.dumps({
        "status": "success",
        "message": f"Report saved successfully!",
        "path": str(report_path)
    })


@mcp.tool()
def audit_quality(path: str) -> str:
    """Checks code quality (Dead code, Structure, Tests)."""
    log(f"[QUALITY] Running Quality Audit on: {path}")
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
    log(f"[ARCH] Running Architecture Audit on: {path}")
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
    log(f"[CLEANUP] Running Cleanup Audit on: {path}")
    target = Path(path).resolve()
    
    results = {
        "cleanup": run_cleanup_scan(target),
        "gitignore": GitignoreTool().analyze(target),
    }
    return json.dumps(results, indent=2)


@mcp.tool()
def audit_git(path: str) -> str:
    """Analyzes git status and recent changes."""
    log(f"[GIT] Running Git Audit on: {path}")
    target = Path(path).resolve()
    
    git_tool = GitTool()
    result = git_tool.analyze(target)
    return json.dumps(result, indent=2)


def get_changed_files(path: Path, base_branch: str = "main") -> list:
    """
    Helper: Get list of changed Python files compared to base branch.
    
    Args:
        path: Project path
        base_branch: Base branch to compare against (default: "main")
    
    Returns:
        List of existing .py file paths that have changed
    """
    import subprocess
    
    try:
        # Run git diff to get changed files
        cmd = ["git", "diff", "--name-only", f"{base_branch}...HEAD"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(path),
            stdin=subprocess.DEVNULL
        )
        
        if result.returncode != 0:
            log(f"[PR-GATE] Git diff failed: {result.stderr}")
            return []
        
        # Filter for existing .py files only
        changed_files = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and line.endswith('.py'):
                file_path = path / line.strip()
                if file_path.exists():
                    changed_files.append(str(file_path))
        
        return changed_files
        
    except subprocess.TimeoutExpired:
        log("[PR-GATE] Git diff timeout")
        return []
    except Exception as e:
        log(f"[PR-GATE] Error getting changed files: {e}")
        return []


@mcp.tool()
def audit_pr_changes(path: str, base_branch: str = "main", run_tests: bool = True) -> str:
    """
    PR Gatekeeper: Fast delta-based audit of ONLY changed files.
    
    Scans only the files that changed compared to the base branch for speed,
    but allows running tests to ensure no regressions.
    
    Args:
        path: Path to the project
        base_branch: Base branch to compare against (default: "main")
        run_tests: Whether to run tests as a safety net (default: True)
    
    Returns:
        Markdown report with explicit PR review recommendation
    """
    return _audit_pr_changes_logic(path, base_branch, run_tests)


def _run_bandit_scan(target: Path, changed_files: list) -> dict:
    """Run Bandit security scan on changed files."""
    import subprocess
    import json
    
    try:
        cmd = [sys.executable, "-m", "bandit", "-c", "pyproject.toml"] + changed_files + ["-f", "json", "--exit-zero"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(target),
            stdin=subprocess.DEVNULL,
            shell=False
        )
        
        bandit_data = json.loads(result.stdout) if result.stdout else {}
        raw_issues = bandit_data.get("results", [])

        # Normalize bandit issues for report
        normalized_issues = []
        for issue in raw_issues:
            normalized_issues.append({
                "severity": issue.get("issue_severity"),
                "file": issue.get("filename"),
                "line": issue.get("line_number"),
                "description": issue.get("issue_text"),
                "code": issue.get("code")
            })

        return {
            "total_issues": len(normalized_issues),
            "issues": normalized_issues[:10]
        }
    except Exception as e:
        log(f"[PR-GATE] Bandit failed: {e}")
        return {"error": str(e), "total_issues": 0}

def _run_ruff_scan(target: Path, changed_files: list) -> dict:
    """Run Ruff linting on changed files."""
    import subprocess
    import json
    
    try:
        cmd = [sys.executable, "-m", "ruff", "check"] + changed_files + ["--output-format", "json"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(target),
            stdin=subprocess.DEVNULL,
            shell=False
        )
        
        ruff_issues = json.loads(result.stdout) if result.stdout else []
        return {
            "total_issues": len(ruff_issues),
            "issues": ruff_issues[:10]
        }
    except Exception as e:
        log(f"[PR-GATE] Ruff failed: {e}")
        return {"error": str(e), "total_issues": 0}

def _run_radon_scan(target: Path, changed_files: list) -> dict:
    """Run Radon complexity analysis on changed files."""
    import subprocess
    import json
    
    try:
        cmd = [sys.executable, "-m", "radon", "cc"] + changed_files + ["-a", "-j"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(target),
            stdin=subprocess.DEVNULL,
            shell=False
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
        
        return {
            "total_high_complexity": len(high_complexity),
            "high_complexity_functions": high_complexity[:10]
        }
    except Exception as e:
        log(f"[PR-GATE] Radon failed: {e}")
        return {"error": str(e), "total_high_complexity": 0}

def _calculate_pr_score(results: dict) -> int:
    """Calculate score based on audit results."""
    score = 100
    
    # Security penalties
    bandit_issues_count = results.get("bandit", {}).get("total_issues", 0)
    if bandit_issues_count > 0:
        score -= min(bandit_issues_count * 5, 30)  # -5 per issue, max -30
    
    # Quality penalties
    ruff_issues_count = results.get("ruff", {}).get("total_issues", 0)
    if ruff_issues_count > 0:
        score -= min(ruff_issues_count * 2, 20)  # -2 per issue, max -20
    
    # Complexity penalties
    complexity_count = results.get("radon", {}).get("total_high_complexity", 0)
    if complexity_count > 0:
        score -= min(complexity_count * 3, 15)  # -3 per function, max -15
    
    return max(0, score)

def _run_safety_net_tests(target: Path) -> tuple:
    """Run tests as a safety net."""
    import subprocess
    
    log("[PR-GATE] Running tests as safety net...")
    try:
        # Detect venv python
        venv_dirs = [".venv", "venv", "env"]
        python_exe = sys.executable

        for venv_name in venv_dirs:
            venv_path = target / venv_name
            if venv_path.exists():
                if sys.platform == "win32":
                    candidate = venv_path / "Scripts" / "python.exe"
                else:
                    candidate = venv_path / "bin" / "python"
                if candidate.exists():
                    python_exe = str(candidate)
                    break

        # Run pytest in fast mode
        cmd = [python_exe, "-m", "pytest", "-x", "--tb=short", "-q"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(target),
            stdin=subprocess.DEVNULL
        )

        test_output = result.stdout + result.stderr

        # Check if tests passed
        if result.returncode != 0:
            log("[PR-GATE] Tests FAILED")
            return False, test_output
        else:
            log("[PR-GATE] Tests PASSED")
            return True, test_output
            
    except subprocess.TimeoutExpired:
        log("[PR-GATE] Tests timeout")
        return False, "⚠️ Tests timed out (>120s)"
    except Exception as e:
        log(f"[PR-GATE] Tests error: {e}")
        return False, f"⚠️ Could not run tests: {e}"

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
    bandit_issues_count = results.get("bandit", {}).get("total_issues", 0)
    ruff_issues_count = results.get("ruff", {}).get("total_issues", 0)
    complexity_count = results.get("radon", {}).get("total_high_complexity", 0)

    md = []
    md.append("# 🚦 PR Gatekeeper Report")
    md.append("")
    md.append(f"**Base Branch:** `{base_branch}`")
    md.append(f"**Changed Files:** {len(changed_files)} Python files")
    md.append(f"**Score:** {score}/100")
    md.append("")
    
    # Changed files list
    md.append("## 📝 Changed Files")
    for f in changed_files[:20]:
        rel_path = Path(f).relative_to(target) if Path(f).is_absolute() else f
        md.append(f"- `{rel_path}`")
    if len(changed_files) > 20:
        md.append(f"- ...and {len(changed_files) - 20} more")
    md.append("")
    
    # Security findings
    md.append("## 🔒 Security Scan (Bandit)")
    if bandit_issues_count > 0:
        md.append(f"**Status:** ❌ {bandit_issues_count} issue(s) found")
        for issue in results["bandit"].get("issues", [])[:5]:
            md.append(f"- **{issue.get('severity')}** in `{Path(issue.get('file', '')).name}:{issue.get('line')}`: {issue.get('description', '')}")
    else:
        md.append("**Status:** ✅ No security issues detected")
    md.append("")
    
    # Linting findings
    md.append("## 📋 Code Quality (Ruff)")
    if ruff_issues_count > 0:
        md.append(f"**Status:** ⚠️ {ruff_issues_count} issue(s) found")
        for issue in results["ruff"].get("issues", [])[:5]:
            md.append(f"- `{Path(issue.get('filename', '')).name}:{issue.get('location', {}).get('row')}` - {issue.get('code')}: {issue.get('message', '')}")
    else:
        md.append("**Status:** ✅ No linting issues detected")
    md.append("")
    
    # Complexity findings
    md.append("## 🧮 Complexity (Radon)")
    if complexity_count > 0:
        md.append(f"**Status:** ⚠️ {complexity_count} high-complexity function(s)")
        for func in results["radon"].get("high_complexity_functions", [])[:5]:
            md.append(f"- `{func['function']}` in `{func['file']}`: Complexity {func['complexity']} (Rank {func['rank']})")
    else:
        md.append("**Status:** ✅ No high-complexity functions")
    md.append("")
    
    # Test results
    if run_tests:
        md.append("## ✅ Test Safety Net")
        if score > 80:
            if tests_passed:
                md.append("**Status:** ✅ All tests passed")
            else:
                md.append("**Status:** ❌ Tests failed")
                md.append("```")
                md.append(test_output[:500])
                md.append("```")
        else:
            md.append("**Status:** ⏭️ Skipped (score too low, fix issues first)")
        md.append("")
    
    # Bottom Line
    md.append("---")
    md.append("## 🎯 Bottom Line")
    md.append("")
    
    blocking_issues = []
    if bandit_issues_count > 0:
        blocking_issues.append(f"🔴 {bandit_issues_count} security issue(s)")
    if not tests_passed and run_tests and score > 80:
        blocking_issues.append("🔴 Tests failing")
    
    if blocking_issues:
        md.append("### 🔴 Request Changes")
        md.append("")
        md.append("**Blocking Issues:**")
        for issue in blocking_issues:
            md.append(f"- {issue}")
    elif score >= 80:
        md.append("### 🟢 Ready for Review")
        md.append("")
        md.append("✅ Code quality is good, no blocking issues detected.")
        if ruff_issues_count > 0 or complexity_count > 0:
            md.append("")
            md.append("**Minor Issues (Non-blocking):**")
            if ruff_issues_count > 0:
                md.append(f"- {ruff_issues_count} linting issue(s) - consider fixing")
            if complexity_count > 0:
                md.append(f"- {complexity_count} high-complexity function(s) - consider refactoring")
    else:
        md.append("### 🟡 Needs Improvement")
        md.append("")
        md.append(f"Score is {score}/100. Please address the issues above before requesting review.")
    
    md.append("")
    md.append("---")
    md.append("*Generated by Python Auditor MCP - PR Gatekeeper*")
    
    return "\n".join(md)

def _audit_pr_changes_logic(path: str, base_branch: str = "main", run_tests: bool = True) -> str:
    """Internal logic for PR audit."""
    log(f"[PR-GATE] Starting PR audit for: {path} (base: {base_branch})")
    target = Path(path).resolve()

    # Step 1: Get changed files
    changed_files = get_changed_files(target, base_branch)

    if not changed_files:
        msg = "✅ No Python changes detected in this PR."
        return json.dumps({
            "status": "success",
            "message": msg,
            "recommendation": "🟢 Ready for Review",
            "score": 100,
            "report": f"# 🚦 PR Gatekeeper Report\n\n{msg}\n\n**Score:** 100/100"
        }, indent=2)

    log(f"[PR-GATE] Found {len(changed_files)} changed Python files")

    # Step 2: Fast Scan - Run tools ONLY on changed files
    results = {}
    results["bandit"] = _run_bandit_scan(target, changed_files)
    log(f"[PR-GATE] Bandit: {results['bandit'].get('total_issues', 0)} issues")

    results["ruff"] = _run_ruff_scan(target, changed_files)
    log(f"[PR-GATE] Ruff: {results['ruff'].get('total_issues', 0)} issues")

    results["radon"] = _run_radon_scan(target, changed_files)
    log(f"[PR-GATE] Radon: {results['radon'].get('total_high_complexity', 0)} high-complexity functions")

    # Step 3: Calculate Score
    score = _calculate_pr_score(results)

    # Step 4: Safety Net - Run Tests
    tests_passed = True
    test_output = ""

    if run_tests and score > 80:
        tests_passed, test_output = _run_safety_net_tests(target)

    # Step 5: Generate Report
    report_text = _generate_pr_report(
        base_branch=base_branch,
        changed_files=changed_files,
        score=score,
        results=results,
        tests_passed=tests_passed,
        test_output=test_output,
        run_tests=run_tests,
        target=target
    )

    # Recommendation logic (simplified from report generation logic)
    bandit_issues_count = results.get("bandit", {}).get("total_issues", 0)
    blocking_issues = (bandit_issues_count > 0) or (not tests_passed and run_tests and score > 80)

    if blocking_issues:
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
            "security_issues": bandit_issues_count,
            "linting_issues": results.get("ruff", {}).get("total_issues", 0),
            "complexity_issues": results.get("radon", {}).get("total_high_complexity", 0),
            "tests_passed": tests_passed if run_tests else None
        },
        "report": report_text
    }, indent=2)


@mcp.tool()
def audit_remote_repo(repo_url: str, branch: str = "main") -> str:
    """
    Audit a remote Git repository without manual cloning.
    
    Clones the repository to a temporary directory, runs a full audit,
    and automatically cleans up. Perfect for quick security assessments
    of dependencies or open-source projects.
    
    Args:
        repo_url: Git repository URL (e.g., "https://github.com/user/repo.git")
        branch: Branch to audit (default: "main")
    
    Returns:
        JSON with audit results and markdown report
    
    Example:
        audit_remote_repo("https://github.com/psf/requests.git", "main")
    """
    return _audit_remote_repo_logic(repo_url, branch)


def _audit_remote_repo_logic(repo_url: str, branch: str = "main") -> str:
    """Internal logic for remote audit."""
    import subprocess
    import tempfile
    import shutil
    
    log(f"[REMOTE-AUDIT] Starting remote audit: {repo_url} (branch: {branch})")
    
    # Validate URL format
    if not repo_url.startswith(("http://", "https://", "git@")):
        return json.dumps({
            "status": "error",
            "error": "Invalid repository URL. Must start with http://, https://, or git@"
        }, indent=2)
    
    # Use temporary directory with automatic cleanup
    try:
        with tempfile.TemporaryDirectory(prefix="audit_remote_") as temp_dir:
            temp_path = Path(temp_dir)
            log(f"[REMOTE-AUDIT] Created temporary directory: {temp_path}")
            
            # Step 1: Clone repository (shallow clone for speed)
            clone_cmd = [
                "git", "clone",
                "--depth", "1",  # Shallow clone (faster)
                "-b", branch,    # Specific branch
                repo_url,
                str(temp_path)
            ]
            
            log(f"[REMOTE-AUDIT] Cloning repository...")
            try:
                result = subprocess.run(
                    clone_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes max for clone
                    stdin=subprocess.DEVNULL
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    log(f"[REMOTE-AUDIT] Clone failed: {error_msg}")
                    
                    # Provide helpful error messages
                    if "not found" in error_msg.lower():
                        return json.dumps({
                            "status": "error",
                            "error": f"Repository not found: {repo_url}",
                            "suggestion": "Check the URL and ensure the repository exists"
                        }, indent=2)
                    elif "authentication" in error_msg.lower() or "permission denied" in error_msg.lower():
                        return json.dumps({
                            "status": "error",
                            "error": "Authentication failed - repository may be private",
                            "suggestion": "This tool currently supports public repositories only. For private repos, clone manually and use start_full_audit()"
                        }, indent=2)
                    elif f"branch '{branch}'" in error_msg.lower():
                        return json.dumps({
                            "status": "error",
                            "error": f"Branch '{branch}' not found",
                            "suggestion": "Check the branch name. Common branches: main, master, develop"
                        }, indent=2)
                    else:
                        return json.dumps({
                            "status": "error",
                            "error": f"Git clone failed: {error_msg}"
                        }, indent=2)
                
                log(f"[REMOTE-AUDIT] Clone successful")
                
            except subprocess.TimeoutExpired:
                log("[REMOTE-AUDIT] Clone timeout")
                return json.dumps({
                    "status": "error",
                    "error": "Clone operation timed out (>5 minutes)",
                    "suggestion": "Repository may be too large. Try cloning manually."
                }, indent=2)
            except FileNotFoundError:
                log("[REMOTE-AUDIT] Git not found")
                return json.dumps({
                    "status": "error",
                    "error": "Git is not installed or not in PATH",
                    "suggestion": "Install Git: https://git-scm.com/downloads"
                }, indent=2)
            
            # Step 2: Verify Python files exist
            py_files = list(temp_path.glob("**/*.py"))
            if not py_files:
                log("[REMOTE-AUDIT] No Python files found")
                return json.dumps({
                    "status": "warning",
                    "message": "Repository cloned successfully but contains no Python files",
                    "repo_url": repo_url,
                    "branch": branch
                }, indent=2)
            
            log(f"[REMOTE-AUDIT] Found {len(py_files)} Python files")
            
            # Step 3: Run full audit using existing infrastructure
            log("[REMOTE-AUDIT] Starting full audit...")
            
            # Create job ID for this audit
            job_id = f"remote_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Run audit synchronously (we're already in temp context)
            try:
                # Import the audit function
                start_time = time.time()
                
                # Run all tools
                tools = {
                    "structure": StructureTool(),
                    "architecture": ArchitectureTool(),
                    "typing": TypingTool(),
                    "duplication": DuplicationTool(),
                    "deadcode": DeadcodeTool(),
                    # "ruff": FastAuditTool(),  <-- REMOVED to avoid confusion. We run security/quality separately below.
                    "secrets": SecretsTool(),
                    "tests": TestsTool(),
                    "git_info": GitTool(),
                }

                
                results = {}
                for key, tool in tools.items():
                    try:
                        log(f"[REMOTE-AUDIT] Running {key}...")
                        results[key] = tool.analyze(temp_path)
                    except Exception as e:
                        log(f"[REMOTE-AUDIT] {key} failed: {e}")
                        results[key] = {"error": str(e), "status": "error"}
                
                # Manual run for real Bandit (Security)
                try:
                    log("[REMOTE-AUDIT] Running bandit (real security)...")
                    results["bandit"] = run_bandit(temp_path)
                except Exception as e:
                    log(f"[REMOTE-AUDIT] bandit failed: {e}")
                    results["bandit"] = {"error": str(e)}

                # Manual run for Quality (Ruff)
                try:
                    log("[REMOTE-AUDIT] Running ruff (quality)...")
                    # We can use FastAuditTool but purely for quality mapping if needed, 
                    # or just rely on its 'quality' output key.
                    # For now let's map it to 'quality' key so it doesn't conflict with bandit
                    results["quality"] = FastAuditTool().analyze(temp_path)
                except Exception as e:
                    log(f"[REMOTE-AUDIT] ruff failed: {e}")
                    results["quality"] = {"error": str(e)}
                try:
                    log("[REMOTE-AUDIT] Running bandit (real security)...")
                    results["bandit"] = run_bandit(temp_path)
                except Exception as e:
                    log(f"[REMOTE-AUDIT] bandit failed: {e}")
                    results["bandit"] = {"error": str(e)}
                
                duration = f"{time.time() - start_time:.1f}s"
                
                # Generate report using existing function
                report_md = generate_full_markdown_report(
                    job_id=job_id,
                    duration=duration,
                    results=results,
                    path=str(temp_path)
                )
                
                # Calculate score (reuse existing logic)
                score = 100
                
                # Security penalties
                if results.get("security", {}).get("total_issues", 0) > 0:
                    score -= 20
                if results.get("secrets", {}).get("total_findings", 0) > 0:
                    score -= 10
                
                # Testing penalties
                cov = results.get("tests", {}).get("coverage_percent", 100)
                if cov < 20:
                    score -= 40
                elif cov < 50:
                    score -= 25
                elif cov < 80:
                    score -= 10
                
                # Quality penalties
                duplicates = results.get("duplication", {}).get("total_duplicates", 0)
                score -= min(duplicates, 15)
                
                dead_code_items = len(results.get("deadcode", {}).get("unused_items", []))
                score -= min(dead_code_items, 5)
                
                # Complexity penalties
                complex_funcs = len(results.get("complexity", {}).get("high_complexity_functions", []))
                score -= min(complex_funcs * 2, 10)
                
                score = max(0, score)
                
                log(f"[REMOTE-AUDIT] Audit complete. Score: {score}/100")
                
                # IMPORTANT: Capture report BEFORE temp directory is deleted
                return json.dumps({
                    "status": "success",
                    "repo_url": repo_url,
                    "branch": branch,
                    "score": score,
                    "duration": duration,
                    "files_analyzed": len(py_files),
                    "report": report_md,
                    "summary": {
                        "security_issues": results.get("security", {}).get("total_issues", 0),
                        "secrets_found": results.get("secrets", {}).get("total_findings", 0),
                        "test_coverage": results.get("tests", {}).get("coverage_percent", 0),
                        "duplicates": duplicates,
                        "dead_code": dead_code_items,
                        "high_complexity": complex_funcs
                    }
                }, indent=2)
                
            except Exception as e:
                log(f"[REMOTE-AUDIT] Audit failed: {e}")
                import traceback
                return json.dumps({
                    "status": "error",
                    "error": f"Audit execution failed: {str(e)}",
                    "traceback": traceback.format_exc()
                }, indent=2)
            
            # Temp directory automatically deleted here by context manager
            
    except Exception as e:
        log(f"[REMOTE-AUDIT] Unexpected error: {e}")
        import traceback
        return json.dumps({
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "traceback": traceback.format_exc()
        }, indent=2)


@mcp.tool()
def generate_full_report(path: str) -> str:
    """Runs ALL 13 tools and generates a comprehensive Markdown report file."""
    log(f"[REPORT] Generating Full Report for: {path}")
    target_path = Path(path).resolve()
    
    # All available tools
    tools = {
        "structure": StructureTool(),
        "architecture": ArchitectureTool(),
        "typing": TypingTool(),
        "complexity": ComplexityTool(),
        "duplication": DuplicationTool(),
        "deadcode": DeadcodeTool(),
        "efficiency": EfficiencyTool(),
        "cleanup": CleanupTool(),
        "secrets": SecretsTool(),
        "security": SecurityTool(),
        "tests": TestsTool(),
        "gitignore": GitignoreTool(),
        "git": GitTool(),
    }
    
    # Run all tools explicitly to catch errors
    # Run all tools explicitly to catch errors
    results = {}
    for key, tool in tools.items():
        try:
            log(f"   [RUNNING] {key}...")
            start = time.time()
            results[key] = tool.analyze(target_path)
            log(f"   [OK] {key} complete in {time.time() - start:.2f}s")
        except Exception as e:
            log(f"   [FAIL] {key} failed: {e}")
            results[key] = {"error": str(e)}

    # Manual run for real Bandit
    try:
        log("   [RUNNING] bandit (real security)...")
        results["bandit"] = run_bandit(target_path)
    except Exception as e:
        log(f"   [FAIL] bandit failed: {e}")
        results["bandit"] = {"error": str(e)}

    # Manual run for Quality (Ruff)
    try:
        log("   [RUNNING] ruff (quality)...")
        results["quality"] = FastAuditTool().analyze(target_path)
    except Exception as e:
        log(f"   [FAIL] ruff failed: {e}")
        results["quality"] = {"error": str(e)}

    # Calculate a simple score (can be enhanced)
    score = 100
    if results.get("security", {}).get("total_issues", 0) > 0:
        score -= 15
    if results.get("secrets", {}).get("total_secrets", 0) > 0:
        score -= 20
    if len(results.get("deadcode", {}).get("dead_functions", [])) > 10:
        score -= 10
    
    # Generate Report
    report_id = f"audit__{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    generator = ReportGenerator(REPORTS_DIR)
    report_path = generator.generate_report(
        report_id=report_id,
        project_path=str(target_path),
        score=max(0, score),
        tool_results=results,
        timestamp=datetime.datetime.now()
    )
    
    log(f"Report generated at: {report_path}")
    return f"Report generated successfully at: {report_path}"



def _audit_remote_repo_logic(repo_url: str, branch: str = "main") -> str:
    """
    Logic for auditing a remote git repository.
    Clones the repo to a temp dir, runs audit tools, and returns a JSON report.
    """
    import tempfile
    import shutil
    import subprocess
    import json
    from pathlib import Path
    
    # 1. Validation
    if not repo_url.startswith(("http", "git@")):
         return json.dumps({"status": "error", "error": "Invalid repository URL", "suggestion": "Use http/https/git URL"})

    try:
        # 2. Clone
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Simple git check
            try:
                subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)  # nosec B607
            except (FileNotFoundError, subprocess.CalledProcessError):
                 return json.dumps({"status": "error", "error": "Git not installed", "suggestion": "Install git"})

            cmd = ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(temp_path)]
            try:
                # Use check=False and text=True to be compatible with tests mocking returncode
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300, stdin=subprocess.DEVNULL)
                
                if proc.returncode != 0:
                     err = proc.stderr if proc.stderr else ""
                     if "not found" in err.lower():
                         return json.dumps({"status": "error", "error": f"Repository not found: {err}", "suggestion": "Check URL"})
                     if "authentication" in err.lower() or "private" in err.lower():
                          return json.dumps({"status": "error", "error": "Authentication failed", "suggestion": "Check credentials"})
                     if "branch" in err.lower() or "did not match any" in err.lower():
                          return json.dumps({"status": "error", "error": f"Branch '{branch}' not found", "suggestion": "Check branch name"})
                     return json.dumps({"status": "error", "error": f"Clone failed: {err}", "suggestion": "Check network"})

            except subprocess.TimeoutExpired:
                 return json.dumps({"status": "error", "error": "Clone timeout (>300s)", "suggestion": "Repo might be too large"})
            except Exception as e:
                 return json.dumps({"status": "error", "error": f"Clone exception: {e}", "suggestion": "Check system"})

            # Check for Python files
            structure_res = run_structure(temp_path)
            if structure_res.get("total_py_files", 0) == 0:
                 return json.dumps({"status": "warning", "message": "No Python files found", "files_analyzed": 0})

            # 3. Run Tools
            # Reuse existing run_* functions
            bandit_res = run_bandit(temp_path)
            secrets_res = run_secrets(temp_path)
            tests_res = run_tests_coverage(temp_path)
            deadcode_res = run_dead_code(temp_path)
            duplication_res = run_duplication(temp_path)
            efficiency_res = run_efficiency(temp_path)
            
            # 4. Calculate Score (Simplified logic matching generate_full_markdown_report)
            score = 100
            
            # Security
            if bandit_res.get("issues"): score -= 20
            if secrets_res.get("total_secrets", 0) > 0: score -= 10
            
            # Coverage
            cov = tests_res.get("coverage_percent", 0)
            if cov < 20: score -= 40
            elif cov < 50: score -= 25
            elif cov < 80: score -= 10
            
            # Quality
            score -= min(duplication_res.get("total_duplicates", 0), 15)
            # (Deadcode score logic in main report is: min(dead_code_items, 5))
            score -= min(deadcode_res.get("total_dead_code", 0), 5) 
            
            score = max(0, score)
            
            # 5. Build Result
            result = {
                "status": "success",
                "repo_url": repo_url,
                "branch": branch,
                "score": score,
                "visual_score": "🟢" if score > 80 else "🔴",
                "files_analyzed": structure_res.get("total_py_files", 0),
                "duration": "N/A", 
                "summary": {
                    "security_issues": bandit_res.get("total_issues", 0),
                    "secrets_found": secrets_res.get("total_secrets", secrets_res.get("total_secrets", 0)),
                    "test_coverage": tests_res.get("coverage_percent", 0),
                    "duplicates": duplication_res.get("total_duplicates", 0),
                    "dead_code": deadcode_res.get("total_dead_code", 0),
                    "high_complexity": efficiency_res.get("total_high_complexity", 0)
                },
                "report": "Full report generation skipped for quick remote audit" 
            }
            return json.dumps(result)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "suggestion": "Unexpected error"})

@mcp.tool()
def audit_remote_repo(repo_url: str, branch: str = "main") -> str:
    """Audit a remote git repository."""
    return _audit_remote_repo_logic(repo_url, branch)


@mcp.tool()
def get_cache_stats(path: str) -> str:
    """
    Get statistics about cached audit results.
    
    Args:
        path: Path to the project
        
    Returns:
        JSON with cache statistics including age, validity, and files tracked
    """
    try:
        from app.core.cache_manager import CacheManager
        
        cache_mgr = CacheManager(path, max_age_hours=1)
        stats = cache_mgr.get_cache_stats()
        
        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def clear_audit_cache(path: str, tool_name: str = None) -> str:
    """
    Clear audit cache for a project.
    
    Args:
        path: Path to the project
        tool_name: Optional specific tool to clear (e.g., "bandit", "ruff").
                   If not provided, clears all caches.
    
    Returns:
        Confirmation message
    """
    try:
        from app.core.cache_manager import CacheManager
        
        cache_mgr = CacheManager(path, max_age_hours=1)
        
        if tool_name:
            cache_mgr.invalidate_tool(tool_name)
            return json.dumps({
                "status": "success",
                "message": f"Cleared cache for {tool_name}",
                "tool": tool_name
            })
        else:
            cache_mgr.clear_all()
            return json.dumps({
                "status": "success",
                "message": "Cleared all audit caches",
                "cache_dir": str(cache_mgr.cache_dir)
            })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


@mcp.tool()
def run_ruff_comprehensive_check(path: str) -> str:
    """
    Run comprehensive Ruff linting (replaces Bandit, pycodestyle, isort, etc.).
    
    This single command replaces 6+ separate tools:
    - Bandit (security) → Ruff --select S
    - pycodestyle → Ruff --select E,W
    - isort → Ruff --select I
    - pyflakes → Ruff --select F
    - McCabe → Ruff --select C90
    - pydocstyle → Ruff --select D
    
    Args:
        path: Path to the project
        
    Returns:
        JSON with categorized issues (security, quality, imports, complexity, etc.)
    """
    try:
        from pathlib import Path
        
        project_path = Path(path).resolve()
        
        if not project_path.exists():
            return json.dumps({"status": "error", "error": f"Path does not exist: {path}"})
        
        result = run_ruff_comprehensive(project_path)
        
        return json.dumps(result, indent=2)
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
