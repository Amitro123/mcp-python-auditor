#!/usr/bin/env python3
"""Python Auditor CLI - Fast parallel code analysis with batch execution.

Usage:
    python audit.py           # Interactive mode with AI insights
    python audit.py <path>    # Direct audit of path
    python audit.py . --fast  # Fast audit (skip slow tools)
"""

import ast
import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

# Setup logging with Rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(show_path=False, rich_tracebacks=True)],
)
logger = logging.getLogger("audit")

console = Console()
warn_console = Console(stderr=True)
TOOLS = {
    "security": ["bandit", "secrets", "pip-audit"],
    "quality": ["ruff", "duplication", "deadcode", "cleanup"],
    "analysis": ["coverage", "complexity", "typing"],
}
ALL_TOOLS = [t for tools in TOOLS.values() for t in tools]
CACHE_FILE = Path(".audit_cache.json")
CACHE_TTL = 3600
SLOW_TOOLS = {"coverage", "pip-audit", "bandit", "deadcode", "secrets"}
VERY_SLOW_TOOLS = {"secrets", "coverage"}  # Skip with --skip-slow for <60s audits
BATCH_SIZE = 4  # Run tools in batches of 4
TOOL_TIMEOUT = 120  # Per-tool timeout in seconds (must exceed internal timeouts)
SECRETS_TIMEOUT = 15  # Secrets with proper excludes should finish in 3-8s


# Dynamic timeout: base 120s + 30s per tool, max 600s
def calc_timeout(num_tools: int) -> int:
    return min(120 + num_tools * 30, 600)


class Cache:
    def __init__(self):
        try:
            self.data = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
        except Exception:
            self.data = {}

    def get(self, tool: str, file: str, fh: str):
        key = f"{tool}:{file}:{fh}"
        if key in self.data and time.time() - self.data[key]["time"] < CACHE_TTL:
            return self.data[key]["result"]
        return None

    def set(self, tool: str, file: str, fh: str, result):
        self.data[f"{tool}:{file}:{fh}"] = {"time": time.time(), "result": result}

    def save(self):
        now = time.time()
        self.data = {k: v for k, v in self.data.items() if now - v["time"] < CACHE_TTL}
        CACHE_FILE.write_text(json.dumps(self.data), encoding="utf-8")


def file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except Exception:
        return ""


class Results:
    def __init__(self, comprehensive=False, show_samples=False):
        self.data, self.score, self.penalties, self.timings = {}, 100, [], {}
        self.completed, self.failed = 0, 0
        self.failed_tools = []  # List of (tool_name, reason) tuples
        self.comprehensive = comprehensive  # Full Ruff reporting mode
        self.show_samples = show_samples  # Include sample issues in output

    def penalty(self, amount: int, reason: str):
        self.score = max(0, self.score - amount)
        self.penalties.append(f"-{amount} {reason}")

    def add_failure(self, tool: str, reason: str):
        self.failed += 1
        self.failed_tools.append((tool, reason))


def run_sync(cmd, timeout=120, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace", cwd=cwd)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -1


def get_pr_files(base: str = "origin/main") -> list:
    out, err, code = run_sync(["git", "diff", "--name-only", base], timeout=30)
    if code != 0:
        return []
    return [f for f in out.strip().split("\n") if f.endswith(".py") and Path(f).exists()]


# Directories to always exclude
EXCLUDE_DIRS = ".venv,venv,node_modules,__pycache__,.git,build,dist,htmlcov,.tox,.eggs,archive"
EXCLUDE_SET = {".venv", "venv", "node_modules", "__pycache__", ".git", "build", "dist", "htmlcov", ".tox", ".eggs", "archive"}

# Scoring weights (total: 100pts)
# Security: 40pts (bandit: 15, secrets: 15, pip-audit: 10)
# Quality: 35pts (ruff: 20, deadcode: 10, cleanup: 5)
# Analysis: 25pts (coverage: 12, complexity: 8, typing: 5)


def get_project_py_files(path: Path) -> list[str]:
    """Get Python files in the project, excluding venv/node_modules/etc."""
    py_files = []
    for py_file in path.rglob("*.py"):
        # Check if any parent directory is in the exclude set
        parts = py_file.relative_to(path).parts
        if not any(part in EXCLUDE_SET for part in parts):
            py_files.append(str(py_file))
    return py_files


# Tool functions - each returns (success: bool, result_key: str, issues_count: int|str)
def run_bandit(path, res, files=None, cache=None):
    logger.info("[bandit] Starting...")
    # Use explicit file list to avoid scanning .venv/node_modules (excludes don't work reliably)
    py_files = files if files else get_project_py_files(path)
    if not py_files:
        res.data["bandit"] = {"total": 0, "status": "no_files"}
        return True
    # Pass files directly, not -r (recursive) which scans everything
    cmd = [sys.executable, "-m", "bandit", "-f", "json", "--exit-zero", "-ll", "--skip", "B101"] + py_files[:200]
    out, err, code = run_sync(cmd, timeout=60)
    if code == -1:
        res.data["bandit"] = {"total": 0, "error": "timeout" if "timeout" in err else "failed"}
        logger.error(f"[bandit] Failed: {'timeout' if 'timeout' in err else err[:50]}")
        return False
    try:
        issues = json.loads(out).get("results", []) if out else []
    except Exception:
        issues = []
    result = {"total": len(issues)}
    # Add samples if enabled
    if res.show_samples and issues:
        result["samples"] = [
            {"file": i.get("filename", ""), "line": i.get("line_number", 0), "code": i.get("test_id", ""), "msg": i.get("issue_text", "")[:80]}
            for i in issues[:5]
        ]
    res.data["bandit"] = result
    if issues:
        res.penalty(min(len(issues) * 3, 15), f"Bandit: {len(issues)} issues")  # max 15pts
    return True


def run_secrets(path, res, files=None, cache=None):
    logger.info("[secrets] Starting...")
    # Find Python files explicitly to avoid scanning entire system (excludes don't work on Windows)
    py_files = []
    for pattern in ["*.py", "app/**/*.py", "tests/**/*.py"]:
        py_files.extend(str(f) for f in Path(path).glob(pattern) if ".venv" not in str(f) and "venv" not in str(f))

    if not py_files:
        res.data["secrets"] = {"total": 0, "status": "no_files"}
        return True

    # Scan explicit file list (much faster than directory scan)
    cmd = ["detect-secrets", "scan", "--no-verify"] + py_files[:100]  # Limit to 100 files
    out, err, code = run_sync(cmd, timeout=SECRETS_TIMEOUT)

    if code == -1:
        err_msg = "timeout" if "timeout" in str(err) else (err[:50] if err else "unknown")
        res.data["secrets"] = {"total": 0, "error": err_msg}
        logger.error(f"[secrets] Failed: {err_msg}")
        return False

    try:
        raw_results = json.loads(out).get("results", {}) if out else {}
        secrets_count = sum(len(v) for v in raw_results.values())
        # Extract samples
        samples = []
        for file_path, findings in list(raw_results.items())[:5]:
            for f in findings[:1]:  # One per file
                samples.append({"file": file_path, "line": f.get("line_number", 0), "type": f.get("type", "unknown")})
    except Exception as e:
        logger.error(f"[secrets] Parse error: {e}")
        secrets_count, samples = 0, []
    result = {"total": secrets_count}
    if res.show_samples and samples:
        result["samples"] = samples[:5]
    res.data["secrets"] = result
    if secrets_count:
        res.penalty(min(secrets_count * 5, 15), f"Secrets: {secrets_count} found")  # max 15pts
    return True


def run_pip_audit(path, res, files=None, cache=None):
    logger.info("[pip-audit] Starting...")
    # --local: only scan local env, --timeout 10: per-package timeout
    out, err, code = run_sync(["pip-audit", "-f", "json", "--local", "--timeout", "10", "--progress-spinner=off"], timeout=90)
    if code == -1:
        res.data["pip-audit"] = {"total": 0, "error": "failed"}
        logger.error(f"[pip-audit] Failed: {'timeout' if 'timeout' in err else err[:50]}")
        return False

    vulns = []
    try:
        parsed = json.loads(out) if out else []
        # pip-audit returns a list of dicts, but handle unexpected formats
        if isinstance(parsed, list):
            vulns = parsed
        elif isinstance(parsed, dict):
            # Some versions return {"dependencies": [...]}
            vulns = parsed.get("dependencies", [])
            if not isinstance(vulns, list):
                vulns = []
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning(f"[pip-audit] Parse error: {e}")
        vulns = []

    result = {"total": len(vulns)}
    try:
        if res.show_samples and vulns and isinstance(vulns, list):
            samples = []
            for v in vulns[:5]:
                if isinstance(v, dict):
                    vuln_list = v.get("vulns", [])
                    vuln_id = ""
                    if isinstance(vuln_list, list) and vuln_list:
                        first_vuln = vuln_list[0]
                        if isinstance(first_vuln, dict):
                            vuln_id = first_vuln.get("id", "")
                    samples.append({
                        "package": v.get("name", ""),
                        "version": v.get("version", ""),
                        "vuln_id": vuln_id,
                    })
            result["samples"] = samples
    except Exception as e:
        logger.warning(f"[pip-audit] Sample extraction error: {e}")

    res.data["pip-audit"] = result
    if vulns:
        res.penalty(min(len(vulns) * 5, 10), f"Vulnerabilities: {len(vulns)}")  # max 10pts
    return True


def run_ruff(path, res, files=None, cache=None):
    logger.info("[ruff] Starting...")
    # Use explicit file list to avoid scanning .venv/node_modules
    py_files = files if files else get_project_py_files(path)
    if not py_files:
        res.data["ruff"] = {"total": 0, "all": 0, "status": "no_files"}
        return True

    # Critical issues (E=errors, F=pyflakes) - always run
    out, err, code = run_sync(
        [sys.executable, "-m", "ruff", "check"] + py_files + ["--select=E,F", "--output-format", "json", "--exit-zero"],
        timeout=60,
    )
    if code == -1:
        res.data["ruff"] = {"total": 0, "error": "failed"}
        logger.error(f"[ruff] Failed: {err[:50] if err else 'unknown'}")
        return False
    try:
        critical = json.loads(out) if out else []
    except Exception:
        critical = []

    # In comprehensive mode, also get total count
    total_count = len(critical)
    if res.comprehensive:
        out2, _, code2 = run_sync(
            [sys.executable, "-m", "ruff", "check"] + py_files + ["--output-format", "json", "--exit-zero"],
            timeout=60,
        )
        if code2 != -1 and out2:
            try:
                total_count = len(json.loads(out2))
            except Exception:
                pass

    # Store both counts
    result = {"total": len(critical), "all": total_count}
    if res.show_samples and critical:
        result["samples"] = [
            {"file": i.get("filename", ""), "line": i.get("location", {}).get("row", 0), "code": i.get("code", ""), "msg": i.get("message", "")[:60]}
            for i in critical[:5]
        ]
    res.data["ruff"] = result
    if len(critical) > 20:
        res.penalty(min((len(critical) - 20) // 10, 20), f"Ruff: {len(critical)} critical")  # max 20pts
    return True


def run_duplication(path, res, files=None, cache=None):
    logger.info("[duplication] Starting...")
    hashes = defaultdict(list)
    # Use explicit file list to avoid scanning .venv/node_modules
    py_files = [Path(f) for f in files] if files else [Path(f) for f in get_project_py_files(path)]
    for py in py_files:
        fh = file_hash(py)
        cached = cache.get("dup", str(py), fh) if cache else None
        if cached:
            for h in cached:
                hashes[h].append(1)
            continue
        try:
            file_hashes = []
            for n in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
                if isinstance(n, ast.FunctionDef) and hasattr(n, "end_lineno") and n.end_lineno - n.lineno >= 5:
                    h = hashlib.md5(ast.dump(n).encode()).hexdigest()
                    hashes[h].append(1)
                    file_hashes.append(h)
            if cache:
                cache.set("dup", str(py), fh, file_hashes)
        except Exception:
            pass
    dups = sum(1 for v in hashes.values() if len(v) > 1)
    res.data["duplication"] = {"total": dups}
    if dups > 5:
        res.penalty(min(dups - 5, 10), f"Duplicates: {dups}")
    return True


def run_deadcode(path, res, files=None, cache=None):
    logger.info("[deadcode] Starting...")
    # Use explicit file list to avoid scanning .venv/node_modules
    py_files = files if files else get_project_py_files(path)
    if not py_files:
        res.data["deadcode"] = {"total": 0, "status": "no_files"}
        return True
    out, err, code = run_sync(
        [sys.executable, "-m", "vulture"] + py_files + ["--min-confidence", "60"],
        timeout=120,
    )
    if code == -1:
        res.data["deadcode"] = {"total": 0, "error": "timeout" if "timeout" in err else "failed"}
        logger.error(f"[deadcode] Failed: {'timeout' if 'timeout' in err else err[:50]}")
        return False
    raw_lines = [line for line in (out or "").splitlines() if line.strip()]
    result = {"total": len(raw_lines)}
    # Parse vulture output: "file.py:123: unused function 'foo'"
    if res.show_samples and raw_lines:
        samples = []
        for line in raw_lines[:5]:
            parts = line.split(":", 2)
            if len(parts) >= 3:
                samples.append({"file": parts[0], "line": int(parts[1]) if parts[1].isdigit() else 0, "msg": parts[2].strip()[:60]})
        result["samples"] = samples
    res.data["deadcode"] = result
    if len(raw_lines) > 150:
        res.penalty(10, f"Dead code: {len(raw_lines)} items")  # max 10pts, only if > 150
    return True


def run_cleanup(path, res, files=None, cache=None):
    logger.info("[cleanup] Starting...")
    # Exclude .venv and venv directories
    found = 0
    for t in ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]:
        for p in path.rglob(t):
            if ".venv" not in str(p) and "venv" not in str(p) and "node_modules" not in str(p):
                found += 1
    res.data["cleanup"] = {"total": found}
    if found > 50:
        res.penalty(5, f"Cleanup: {found} cache dirs")  # max 5pts
    return True


def run_coverage(path, res, files=None, cache=None):
    logger.info("[coverage] Starting...")
    tests_dir = path / "tests"
    if not tests_dir.exists():
        res.data["coverage"] = {"percent": 0, "error": "no tests dir"}
        return True
    out, err, code = run_sync(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir),
            "--cov=.",
            "--cov-report=term",
            "-q",
            "--color=no",
            "--tb=no",
        ],
        timeout=180,
        cwd=str(path),
    )
    combined = (out or "") + (err or "")
    cov = 0
    for line in combined.splitlines():
        if line.strip().startswith("TOTAL"):
            match = re.search(r"(\d+)%", line)
            if match:
                cov = int(match.group(1))
                break
    res.data["coverage"] = {"percent": cov}
    if code != 0 and cov == 0:
        res.data["coverage"]["error"] = "pytest failed"
    # Coverage penalty: max 12pts, scaled by coverage/80
    if cov < 80:
        penalty = int((1 - cov / 80) * 12)  # 0% -> 12pts, 40% -> 6pts, 80% -> 0pts
        if penalty > 0:
            res.penalty(penalty, f"Coverage: {cov}%")
    return True


def run_complexity(path, res, files=None, cache=None):
    logger.info("[complexity] Starting...")
    target = files if files else [str(path)]
    out, err, code = run_sync(
        [sys.executable, "-m", "radon", "cc"] + target + ["-a", "-s", "-e", "tests/*,*_test.py"],
        timeout=60,
    )
    if code == -1:
        res.data["complexity"] = {"grade": "?", "error": "failed"}
        logger.error(f"[complexity] Failed: {err[:50] if err else 'unknown'}")
        return False
    match = re.search(r"Average complexity: ([A-F]) \((\d+\.?\d*)\)", out or "")
    grade = match.group(1) if match else "?"
    res.data["complexity"] = {"grade": grade}
    if grade == "C":
        res.penalty(4, f"Complexity: grade {grade}")  # max 8pts
    elif grade in ["D", "E", "F"]:
        res.penalty(8, f"Complexity: grade {grade}")
    return True


def run_typing(path, res, files=None, cache=None):
    logger.info("[typing] Starting...")
    total = typed = 0
    py_files = [Path(f) for f in files] if files else path.rglob("*.py")
    for py in py_files:
        if any(x in str(py) for x in ["venv", "node_modules", "__pycache__", "test"]):
            continue
        fh = file_hash(py)
        cached = cache.get("typing", str(py), fh) if cache else None
        if cached:
            total += cached[0]
            typed += cached[1]
            continue
        try:
            ft, tt = 0, 0
            for n in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
                if isinstance(n, ast.FunctionDef) and not n.name.startswith("_"):
                    ft += 1
                    if n.returns:
                        tt += 1
            total += ft
            typed += tt
            if cache:
                cache.set("typing", str(py), fh, [ft, tt])
        except Exception:
            pass
    pct = int(typed / total * 100) if total else 0
    res.data["typing"] = {"percent": pct}
    if pct < 50:
        res.penalty(5, f"Typing: {pct}%")  # max 5pts
    return True


FUNCS = {
    "bandit": run_bandit,
    "secrets": run_secrets,
    "pip-audit": run_pip_audit,
    "ruff": run_ruff,
    "duplication": run_duplication,
    "deadcode": run_deadcode,
    "cleanup": run_cleanup,
    "coverage": run_coverage,
    "complexity": run_complexity,
    "typing": run_typing,
}


def grade(score):
    """Letter grade with +/- modifiers."""
    if score >= 97:
        return "A+"
    if score >= 93:
        return "A"
    if score >= 90:
        return "A-"
    if score >= 87:
        return "B+"
    if score >= 83:
        return "B"
    if score >= 80:
        return "B-"
    if score >= 77:
        return "C+"
    if score >= 73:
        return "C"
    if score >= 70:
        return "C-"
    if score >= 67:
        return "D+"
    if score >= 63:
        return "D"
    if score >= 60:
        return "D-"
    return "F"


def report(path, res, ai_analysis=None, old_score=None, changed_files=None):
    """Generate enhanced markdown report with optional AI analysis and fix results."""
    # Determine emoji based on score
    score_emoji = "🎉" if res.score >= 90 else "✅" if res.score >= 70 else "⚠️"

    # Count completed tools (fix bug - count non-skipped, non-error tools)
    completed = sum(1 for d in res.data.values() if not d.get("skipped") and not d.get("error"))
    total = len(res.data)

    lines = [
        f"# {score_emoji} Audit Report: {path.name}",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Score:** {res.score}/100 ({grade(res.score)})",
        f"**Tools:** {completed}/{total} completed",
    ]

    # Before/after scores if fixes were applied
    if old_score is not None and old_score != res.score:
        diff = res.score - old_score
        sign = "+" if diff > 0 else ""
        lines.append(f"**Improvement:** {old_score} → {res.score} ({sign}{diff} points)")

    # Changed files summary
    if changed_files:
        lines.append(f"**Files Fixed:** {len(changed_files)}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Results")
    lines.append("")

    for cat, tools in TOOLS.items():
        cat_emoji = {"security": "🔒", "quality": "🧹", "analysis": "📊"}.get(cat, "📋")
        lines.append(f"### {cat_emoji} {cat.title()}")
        lines.append("")

        for t in tools:
            d = res.data.get(t, {})
            v = d.get("total", d.get("percent", d.get("grade", "-")))
            dur = res.timings.get(t, 0) if hasattr(res, "timings") else 0

            # Status indicator
            if d.get("skipped"):
                status = "⏭️ skipped"
            elif d.get("error"):
                status = f"❌ {d.get('error')}"
            elif v == 0 or v == "-" or v in ["A", "B"]:
                status = "✅"
            else:
                status = "⚠️"

            lines.append(f"- **{t}**: {v} ({dur:.1f}s) {status}")

            # Add sample issues if available
            samples = d.get("samples", [])
            if samples:
                for s in samples[:3]:
                    if "code" in s:
                        # Ruff/bandit format
                        lines.append(f"  - `{s.get('file', '')}:{s.get('line', '')}` [{s.get('code', '')}] {s.get('msg', '')[:50]}")
                    elif "type" in s:
                        # Secrets format
                        lines.append(f"  - `{s.get('file', '')}:{s.get('line', '')}` [{s.get('type', '')}]")
                    elif "package" in s:
                        # pip-audit format
                        lines.append(f"  - `{s.get('package', '')}` {s.get('version', '')} - {s.get('vuln_id', '')}")

        lines.append("")

    # AI Analysis section
    if ai_analysis:
        lines.append("---")
        lines.append("")
        lines.append("## 🤖 AI Analysis")
        lines.append("")
        lines.append(ai_analysis)
        lines.append("")

    # Changed files detail
    if changed_files and len(changed_files) > 0:
        lines.append("---")
        lines.append("")
        lines.append("## 🔧 Files Modified")
        lines.append("")
        for f in changed_files[:10]:
            lines.append(f"- `{f}`")
        if len(changed_files) > 10:
            lines.append(f"- ... and {len(changed_files) - 10} more")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Python Audit CLI*")

    return "\n".join(lines)


async def run_tool_with_timeout(name, func, path, res, files, cache, progress, task_id):
    """Run a single tool with per-tool timeout, error handling, and logging."""
    # Prevent duplicate runs - check if already has results
    if name in res.data and not res.data[name].get("skipped"):
        progress.update(task_id, completed=1)
        return name, True

    start = time.time()
    try:
        # Wrap tool execution with per-tool timeout
        success = await asyncio.wait_for(asyncio.to_thread(func, path, res, files, cache), timeout=TOOL_TIMEOUT)
        duration = time.time() - start
        res.timings[name] = duration

        if success:
            res.completed += 1
            d = res.data.get(name, {})
            result_val = d.get("total", d.get("percent", d.get("grade", "ok")))
            logger.info(
                f"[green][{name}] Done in {duration:.1f}s: {result_val}[/green]",
                extra={"markup": True},
            )
        else:
            err_msg = res.data.get(name, {}).get("error", "unknown")
            res.add_failure(name, err_msg)
            logger.warning(
                f"[yellow][{name}] Failed in {duration:.1f}s: {err_msg}[/yellow]",
                extra={"markup": True},
            )

        progress.update(task_id, completed=1)
        return name, success

    except TimeoutError:
        duration = time.time() - start
        res.timings[name] = duration
        res.data[name] = {"total": 0, "error": "timeout"}
        res.add_failure(name, "timeout")
        logger.error(
            f"[red][{name}] Timeout after {duration:.1f}s (limit: {TOOL_TIMEOUT}s)[/red]",
            extra={"markup": True},
        )
        progress.update(task_id, completed=1)
        return name, False

    except Exception as e:
        duration = time.time() - start
        res.timings[name] = duration
        err_msg = str(e)[:50]
        res.data[name] = {"total": 0, "error": err_msg}
        res.add_failure(name, err_msg)
        logger.error(f"[red][{name}] Exception after {duration:.1f}s: {e}[/red]", extra={"markup": True})
        progress.update(task_id, completed=1)
        return name, False


async def run_batch(batch, path, res, files, cache, progress, task_ids, processed):
    """Run a batch of tools in parallel with return_exceptions=True and proper cleanup."""
    # Filter out already processed tools AND tools already in results (belt-and-suspenders)
    batch = [t for t in batch if t not in processed and t not in res.data]
    if not batch:
        return

    # Mark as processed BEFORE creating tasks to prevent race conditions
    processed.update(batch)

    tasks = [
        asyncio.create_task(
            run_tool_with_timeout(name, FUNCS[name], path, res, files, cache, progress, task_ids[name]),
            name=f"tool-{name}",
        )
        for name in batch
    ]

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any unexpected exceptions from gather (shouldn't happen with try/except in run_tool_with_timeout)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                name = batch[i]
                if name not in res.data:  # Only if not already handled
                    err_msg = str(result)[:50]
                    res.data[name] = {"total": 0, "error": err_msg}
                    res.add_failure(name, err_msg)
                logger.error(f"[red][{name}] Gather exception: {result}[/red]", extra={"markup": True})
    finally:
        # Cancel any pending tasks to prevent "executor did not finish joining threads" warning
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


async def run_all_tools_batched(path, res, files, cache, skip, progress):
    """Run all tools in batches of BATCH_SIZE with proper cleanup."""
    # Deduplicate tools list (safety check)
    tools_to_run = list(dict.fromkeys(t for t in ALL_TOOLS if t not in skip))

    # Mark skipped tools
    for tool in skip:
        res.data[tool] = {"total": 0, "skipped": True}
        res.timings[tool] = 0

    # Track processed tools to prevent duplicates
    processed = set()

    # Create ALL progress tasks upfront (one per tool) - with duplicate check
    task_ids = {}
    for tool in tools_to_run:
        if tool not in task_ids:  # Prevent duplicate progress tasks
            task_ids[tool] = progress.add_task(f"[cyan]{tool}[/]", total=1)

    # Suppress logging during progress to avoid visual conflicts
    old_level = logger.level
    logger.setLevel(logging.WARNING)

    try:
        # Run in batches
        for i in range(0, len(tools_to_run), BATCH_SIZE):
            batch = tools_to_run[i : i + BATCH_SIZE]
            await run_batch(batch, path, res, files, cache, progress, task_ids, processed)
    finally:
        # Restore logging
        logger.setLevel(old_level)

        # Cancel any remaining pending tasks to prevent executor shutdown warnings
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task() and not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.5)
                except (asyncio.CancelledError, TimeoutError):
                    pass


def _print_summary_table(res, comprehensive=False):
    """Print summary table immediately - call right after tools complete."""
    table = Table(title="Audit Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Tool")
    table.add_column("Result", justify="right")
    table.add_column("Duration", justify="right", style="dim")
    table.add_column("Status", justify="center")

    for cat, tools in TOOLS.items():
        for t in tools:
            d = res.data.get(t, {})
            v = d.get("total", d.get("percent", d.get("grade", "-")))
            if d.get("skipped"):
                v = "-"
            elif t == "ruff" and comprehensive and d.get("all", 0) > d.get("total", 0):
                v = f"{d.get('total', 0)} ({d.get('all', 0)} total)"
            dur = res.timings.get(t, 0)
            dur_str = f"{dur:.1f}s" if dur > 0 else "-"
            status = "[red]ERR[/]" if d.get("error") else "[dim]skip[/]" if d.get("skipped") else "[green]OK[/]"
            table.add_row(cat, t, str(v), dur_str, status)

    console.print(table)

    # Print score
    total_tools = res.completed + res.failed
    color = "green" if res.score >= 80 else "yellow" if res.score >= 60 else "red"
    console.print(f"\n[bold {color}]Score: {res.score}/100 ({grade(res.score)})[/] [dim](completed: {res.completed}/{total_tools})[/]")

    if res.failed_tools:
        failed_summary = ", ".join(f"{t} ({r})" for t, r in res.failed_tools)
        console.print(f"[red]Failed: {failed_summary}[/]")


def run_audit_sync(path, res, files, cache, skip, silent=False):
    """Synchronous wrapper for async audit with batched execution."""
    num_tools = len([t for t in ALL_TOOLS if t not in skip])
    timeout = calc_timeout(num_tools)

    if silent:

        async def run_silent():
            processed = set()
            for tool in ALL_TOOLS:
                if tool in processed:
                    continue  # Skip duplicates
                processed.add(tool)
                if tool in skip:
                    res.data[tool] = {"total": 0, "skipped": True}
                    res.timings[tool] = 0
                    continue
                start = time.time()
                try:
                    success = await asyncio.wait_for(
                        asyncio.to_thread(FUNCS[tool], path, res, files, cache),
                        timeout=TOOL_TIMEOUT,
                    )
                    res.timings[tool] = time.time() - start
                    if success:
                        res.completed += 1
                    else:
                        err_msg = res.data.get(tool, {}).get("error", "unknown")
                        res.add_failure(tool, err_msg)
                except TimeoutError:
                    res.timings[tool] = time.time() - start
                    res.data[tool] = {"total": 0, "error": "timeout"}
                    res.add_failure(tool, "timeout")
                except Exception as e:
                    res.timings[tool] = time.time() - start
                    err_msg = str(e)[:50]
                    res.data[tool] = {"total": 0, "error": err_msg}
                    res.add_failure(tool, err_msg)

        asyncio.run(run_silent())
    else:
        console.print(f"\n[bold blue]Auditing:[/] {path}")
        console.print(f"[dim]Tools: {num_tools}, Timeout: {timeout}s, Batch size: {BATCH_SIZE}[/]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True,  # Clean up progress bars after completion
        ) as progress:
            asyncio.run(run_all_tools_batched(path, res, files, cache, skip, progress))

        # Print penalties
        for p in res.penalties:
            console.print(f"  [yellow]{p}[/]")

        # Print summary table IMMEDIATELY after tools complete (before any post-processing)
        print("", flush=True)  # Ensure output is flushed
        _print_summary_table(res)
        print("", flush=True)


def explain_results(data: dict) -> None:
    """Print human-readable explanation of audit results."""
    print(f"\n{'=' * 50}")
    print(f"  Audit Results: {data.get('path', 'unknown')}")
    print(f"  Score: {data.get('score', 0)}/100 ({data.get('grade', '?')})")
    print(f"{'=' * 50}\n")

    tools = data.get("tools", {})

    for tool, result in tools.items():
        total = result.get("total", result.get("percent", result.get("grade", "-")))
        if tool in ("coverage", "typing"):
            status = "OK" if (isinstance(total, int) and total >= 50) else "!"
        elif tool == "complexity":
            status = "OK" if total in ["A", "B", "?", "-"] else "!"
        else:
            status = "OK" if total in [0, "-"] or (isinstance(total, int) and total <= 10) else "!"
        print(f"  [{status}] {tool:12} : {total}")


def call_llm(prompt_text: str, provider: str = "1") -> str:
    """Call LLM (Groq or Ollama) for AI insights."""
    if provider == "1":
        key = os.getenv("GROQ_API_KEY")
        if not key:
            key = input("Groq API key: ").strip()
        import groq

        return (
            groq.Groq(api_key=key)
            .chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt_text}])
            .choices[0]
            .message.content
        )
    import requests

    return requests.post(
        "http://localhost:11434/api/generate", json={"model": "llama3.2", "prompt": prompt_text, "stream": False}, timeout=60
    ).json()["response"]


def run_audit_internal(path: Path, fast: bool = False, pr: bool = False, skip_secrets: bool = False) -> dict:
    """Run audit and return results dict (for interactive mode)."""
    res = Results(comprehensive=False, show_samples=True)
    cache = Cache()
    files = get_pr_files() if pr else None

    if pr and not files:
        return {"path": str(path), "score": 100, "grade": "A+", "tools": {}, "pr_files": 0}

    if fast:
        skip = SLOW_TOOLS
    else:
        skip = {"secrets"} if skip_secrets else set()

    run_audit_sync(path, res, files, cache, skip, silent=False)
    cache.save()

    return {
        "path": str(path),
        "score": res.score,
        "grade": grade(res.score),
        "tools": res.data,
        "timings": res.timings,
        "completed": f"{res.completed}/{res.completed + res.failed}",
    }


def interactive_mode() -> None:
    """Interactive question-based audit with AI insights."""
    print("\n" + "=" * 50)
    print("  Python Audit - Interactive Mode")
    print("=" * 50 + "\n")

    # Ask for path
    path_input = input("Enter project path [.]: ").strip() or "."
    target = Path(path_input).resolve()
    if not target.exists():
        print(f"Error: Path '{path_input}' does not exist.")
        return

    # Ask for mode
    print("\nAudit mode:")
    print("  1. Full audit (includes coverage, pip-audit, secrets)")
    print("  2. Fast audit (skip slow tools) [recommended]")
    print("  3. PR mode (only changed files vs origin/main)")
    mode = input("Select [2]: ").strip() or "2"
    fast = mode == "2"
    pr = mode == "3"

    print()
    data = run_audit_internal(target, fast, pr)

    if "error" in data:
        print(f"\nError: {data['error']}")
        return

    explain_results(data)

    # Track data for report
    ai_analysis = None
    old_score = None
    changed_files = None

    # Optional AI analysis and fixes
    if input("\nAI analysis? [y/N]: ").strip().lower() == "y":
        issues = {k: v.get("total", 0) for k, v in data["tools"].items() if v.get("total", 0) > 0}
        issues_str = ", ".join(f"{k}: {v}" for k, v in issues.items())

        provider = input("[1] Groq [2] Ollama: ").strip() or "1"

        try:
            # Stage 1: Analysis
            print("\n[Stage 1] Analyzing issues...")
            analysis_prompt = f"""Score: {data["score"]}/100. Issues found: {issues_str}.

Analyze these code quality issues. For each problem area, explain:
- What the issue is
- Why it matters
- Specific examples if possible

Keep response under 200 words. Use bullet points."""

            ai_analysis = call_llm(analysis_prompt, provider)
            print(f"\n{ai_analysis}")

            # Stage 2: Get specific fixes
            if input("\nGet fix commands? [y/N]: ").strip().lower() == "y":
                print("\n[Stage 2] Generating fixes...")
                fix_prompt = f"""You MUST return ONLY a JSON array. No markdown, no explanation, no text.

ONLY USE THESE EXACT COMMANDS:
- Remove unused imports: ["ruff","check","--fix","--select","F401","."]
- Format code: ["ruff","format","."]
- Fix all auto-fixable: ["ruff","check","--fix","."]

NEVER use: "ruff fix" (doesn't exist)
NEVER use: "ruff --fix" (wrong syntax)

Issues found: {issues_str}

Return JSON array with 1-3 commands:
[{{"desc":"Remove unused imports","cmd":["ruff","check","--fix","--select","F401","."]}}]"""

                ai_fixes = []
                try:
                    fix_response = call_llm(fix_prompt, provider)

                    # Strip everything before [ and after ]
                    start = fix_response.find("[")
                    end = fix_response.rfind("]")

                    if start != -1 and end != -1 and end > start:
                        json_str = fix_response[start : end + 1]
                        json_str = json_str.strip()
                        if json_str.startswith("[") and json_str.endswith("]"):
                            parsed = json.loads(json_str)
                            # Validate each item and fix common LLM mistakes
                            valid_fixes = []
                            for f in parsed[:3]:
                                if not isinstance(f, dict) or "desc" not in f or "cmd" not in f:
                                    continue
                                cmd = f["cmd"]
                                if not isinstance(cmd, list) or len(cmd) < 2:
                                    continue
                                # Fix common LLM mistakes: "ruff fix" -> "ruff check --fix"
                                if cmd[0] == "ruff" and len(cmd) >= 2:
                                    if cmd[1] == "fix":
                                        cmd = ["ruff", "check", "--fix", "."]
                                    elif cmd[1] == "--fix":
                                        cmd = ["ruff", "check", "--fix", "."]
                                f["cmd"] = cmd
                                valid_fixes.append(f)
                            ai_fixes = valid_fixes
                    if not ai_fixes:
                        print("  (AI response not in expected format, skipping fixes)")
                except json.JSONDecodeError:
                    print("  (Could not parse AI response as JSON, skipping fixes)")
                except Exception as e:
                    print(f"  (AI fix generation failed: {e})")

                if ai_fixes:
                    print("\nSuggested fixes:")
                    for i, f in enumerate(ai_fixes, 1):
                        print(f"  {i}. {f['desc']}")

                    # Stage 3: Apply and show results
                    if input("\nApply fixes? [y/N]: ").strip().lower() == "y":
                        print("\n[Stage 3] Applying fixes...")
                        old_score = data["score"]

                        for f in ai_fixes:
                            print(f"\n  Running: {f['desc']}")
                            try:
                                # Add excludes to prevent fixing archive/.venv files
                                cmd = f["cmd"].copy()
                                if "ruff" in cmd:
                                    # Insert excludes before the path argument
                                    cmd = [c for c in cmd if c != "."]  # Remove bare "."
                                    cmd.extend(["--exclude", "archive,.venv,venv,node_modules", "app", "tests"])
                                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace", cwd=str(target))
                                # Show what was fixed
                                if result.stdout:
                                    lines = result.stdout.strip().split("\n")[:5]
                                    for line in lines:
                                        print(f"    {line}")
                                    if len(result.stdout.strip().split("\n")) > 5:
                                        print(f"    ... and more")
                                if result.returncode != 0 and result.stderr:
                                    print(f"    Warning: {result.stderr[:100]}")
                            except Exception as fix_err:
                                print(f"    Error: {fix_err}")

                        # Get all changed files at once
                        diff_result = subprocess.run(
                            ["git", "diff", "--name-only"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(target)
                        )
                        changed_files = [f for f in diff_result.stdout.strip().split("\n") if f]

                        if changed_files:
                            print(f"\n  Changed {len(changed_files)} files:")
                            for f in changed_files[:5]:
                                print(f"    - {f}")
                            if len(changed_files) > 5:
                                print(f"    ... and {len(changed_files) - 5} more")

                            # Re-run audit
                            print("\n  Re-running audit...")
                            data = run_audit_internal(target, fast, pr)
                            if "error" not in data:
                                new_score = data["score"]
                                diff_score = new_score - old_score

                                print(f"\n{'=' * 50}")
                                print("  Results:")
                                print(f"{'=' * 50}")
                                print(f"  Files changed: {len(changed_files)}")
                                print(f"  Score: {old_score} → {new_score}", end="")
                                if diff_score > 0:
                                    console.print(f" [bold green](+{diff_score} points!)[/]")
                                elif diff_score < 0:
                                    console.print(f" [yellow]({diff_score} points)[/]")
                                else:
                                    print(" (no change)")

                                explain_results(data)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Parse error: {e}")
        except Exception as e:
            print(f"AI error: {e}")

    # Auto-save markdown report
    report_name = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    res = Results()
    res.data = data["tools"]
    res.score = data["score"]
    res.timings = data.get("timings", {})
    Path(report_name).write_text(report(target, res, ai_analysis=ai_analysis, old_score=old_score, changed_files=changed_files), encoding="utf-8")
    console.print(f"\n[green]Report saved to {report_name}[/]")

    print("\nDone!")


@click.command()
@click.argument("path", type=click.Path(exists=True), default=".", required=False)
@click.option("--output", "-o", type=click.Path(), help="Output report path")
@click.option("--fast", is_flag=True, help="Skip slow tools (coverage, pip-audit, bandit, deadcode, secrets)")
@click.option("--skip-slow", is_flag=True, help="Skip very slow tools (secrets, coverage) for <60s audits")
@click.option("--skip-secrets", is_flag=True, help="Skip secrets scan (runs by default with optimized excludes)")
@click.option("--comprehensive", is_flag=True, help="Full Ruff report: show all issues, not just critical")
@click.option("--json-out", is_flag=True, help="Output JSON only")
@click.option("--json-file", type=click.Path(), help="Write JSON to file (with progress)")
@click.option("--pr", is_flag=True, help="Only changed files")
@click.option("--show-samples", is_flag=True, help="Include top 3-5 sample issues from each tool")
@click.option("-q", "--quiet", is_flag=True, help="Suppress logging output")
def main(
    path: str,
    output: str,
    fast: bool,
    skip_slow: bool,
    skip_secrets: bool,
    comprehensive: bool,
    json_out: bool,
    json_file: str,
    pr: bool,
    show_samples: bool,
    quiet: bool,
):
    """Run parallel Python code audit with batched execution."""
    if quiet or json_out:
        logging.getLogger("audit").setLevel(logging.WARNING)

    start_time = time.time()
    target = Path(path).resolve()
    res = Results(comprehensive=comprehensive, show_samples=show_samples)
    cache = Cache()
    files = get_pr_files() if pr else None

    if pr and not files:
        if json_out:
            print(
                json.dumps(
                    {
                        "path": str(target),
                        "score": 100,
                        "grade": "A+",
                        "tools": {},
                        "pr_files": 0,
                        "completed": "0/0",
                    }
                )
            )
        else:
            console.print("[green]No changed Python files.[/]")
        return

    if pr and not json_out:
        console.print(f"[dim]PR mode: {len(files)} files[/]")

    # Determine which tools to skip
    if fast:
        skip = SLOW_TOOLS
    elif skip_slow:
        skip = VERY_SLOW_TOOLS
    else:
        skip = {"secrets"} if skip_secrets else set()

    run_audit_sync(target, res, files, cache, skip, silent=json_out)

    cache.save()
    total_time = time.time() - start_time
    total_tools = res.completed + res.failed

    if json_out:
        out = {
            "path": str(target),
            "score": res.score,
            "grade": grade(res.score),
            "tools": res.data,
            "timings": res.timings,
            "total_time": total_time,
            "completed": f"{res.completed}/{total_tools}",
            "failed": [{"tool": t, "reason": r} for t, r in res.failed_tools] if res.failed_tools else [],
        }
        if pr:
            out["pr_files"] = len(files)
        print(json.dumps(out))
        return

    # Table already printed in run_audit_sync, just show total time
    console.print(f"[dim]Total time: {total_time:.1f}s[/]")

    # Show samples if enabled
    if show_samples:
        console.print("[bold]Sample Issues:[/]")
        for tool_name, tool_data in res.data.items():
            samples = tool_data.get("samples", [])
            if samples:
                console.print(f"\n  [cyan]{tool_name}[/]:")
                for s in samples[:3]:
                    if "msg" in s:
                        console.print(f"    {s.get('file', '')}:{s.get('line', '')} [{s.get('code', '')}] {s.get('msg', '')}")
                    elif "type" in s:
                        console.print(f"    {s.get('file', '')}:{s.get('line', '')} [{s.get('type', '')}]")
                    elif "package" in s:
                        console.print(f"    {s.get('package', '')} {s.get('version', '')} - {s.get('vuln_id', '')}")
                    else:
                        console.print(f"    {s}")
        console.print()

    if json_file:
        out = {
            "path": str(target),
            "score": res.score,
            "grade": grade(res.score),
            "tools": res.data,
            "timings": res.timings,
            "completed": f"{res.completed}/{total_tools}",
        }
        if pr:
            out["pr_files"] = len(files) if files else 0
        Path(json_file).write_text(json.dumps(out), encoding="utf-8")

    if output:
        Path(output).write_text(report(target, res), encoding="utf-8")
        console.print(f"[dim]Report saved to {output}[/]")


def _log_error(error: Exception, context: str = ""):
    """Log error to audit_error.log with timestamp."""
    import traceback
    error_file = Path("audit_error.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(error_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{timestamp}] {context}\n")
        f.write(f"Error: {type(error).__name__}: {error}\n")
        f.write(traceback.format_exc())
    return error_file


if __name__ == "__main__":
    # Check if running in interactive mode (no path argument provided)
    # Interactive if: no args, or all args are flags (start with -)
    args = sys.argv[1:]
    has_path_arg = any(not arg.startswith("-") for arg in args)

    exit_code = 0
    try:
        if not has_path_arg:
            interactive_mode()
        else:
            main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/]")
        exit_code = 130
    except Exception as e:
        error_file = _log_error(e, f"Command: {' '.join(sys.argv)}")
        console.print(f"\n[red]Fatal error: {e}[/]")
        console.print(f"[dim]Details logged to {error_file}[/]")
        exit_code = 1

    sys.exit(exit_code)
