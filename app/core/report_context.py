"""Data normalization layer for audit report context.

This module transforms raw audit results into a clean, normalized context for
Jinja2 template rendering. It handles missing keys, inconsistent formats, and
provides safe defaults to prevent "N/A" bugs.
"""
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Constants for scoring and grading
SCORE_A = 90
SCORE_B = 80
SCORE_C = 70
SCORE_D = 60

# Penalty Constants
MAX_SECURITY_PENALTY = 50
SECURITY_ISSUE_PENALTY = 5
SECRET_FOUND_PENALTY = 10

MAX_QUALITY_PENALTY = 20
DEAD_CODE_DIVISOR = 2

# Testing Penalty Constants
PENALTY_TESTING_VERY_LOW = 30
PENALTY_TESTING_LOW = 20
PENALTY_TESTING_MODERATE = 10
COVERAGE_THRESHOLD_LOW = 50
COVERAGE_THRESHOLD_MODERATE = 70
COVERAGE_THRESHOLD_GOOD = 80


def _format_duration(seconds: float) -> str:
    """Format duration as human-readable string (e.g., '4m 2s' instead of '242.31s')."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def _extract_tool_data(raw_results: dict[str, Any], key: str) -> dict[str, Any]:
    """
    Extract tool data handling both flat and nested structures.

    Handles:
    1. Flat: raw_results[key] = {actual data}
    2. Nested: raw_results[key] = {tool_name, status, data: {actual data}}
    """
    data = raw_results.get(key, {})

    # If data has 'data' key with a dict value, extract the nested data
    if isinstance(data, dict) and 'data' in data and isinstance(data.get('data'), dict):
        return data['data']

    return data if isinstance(data, dict) else {}


def build_report_context(
    raw_results: dict[str, Any],
    project_path: str,
    score: int,
    report_id: str,
    timestamp: datetime,
    duration: float | None = None  # ADDED: duration parameter
) -> dict[str, Any]:
    """
    Build normalized context for Jinja2 template rendering.

    This function:
    1. Flattens inconsistent keys (git vs git_info)
    2. Calculates totals and aggregates
    3. Provides safe defaults for missing data
    4. Formats data for easy template iteration

    Args:
        raw_results: Raw tool execution results
        project_path: Path to the project being audited
        score: Overall audit score
        report_id: Unique report identifier
        timestamp: Report generation timestamp
        duration: Total audit duration in seconds (optional)

    Returns:
        Normalized context dictionary ready for template rendering
    """
    # Calculate grade from score
    grade = _calculate_grade(score)

    # Calculate penalties
    penalties = _calculate_penalties(raw_results)

    # Calculate severity labels
    security_severity = _get_security_severity(raw_results)
    coverage_severity = _get_coverage_severity(raw_results)

    return {
        # === METADATA ===
        "project_name": Path(project_path).name,
        "repo_name": Path(project_path).name,  # ADDED: for template compatibility
        "score": score,
        "grade": grade,  # ADDED: A/B/C/D/F
        "report_id": report_id,
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "date": timestamp.strftime("%Y-%m-%d"),
        "time": timestamp.strftime("%H:%M:%S"),
        "duration": _format_duration(duration) if duration else "N/A",  # Human-readable duration

        # === PENALTIES (for score breakdown table) ===
        "security_penalty": penalties["security"],
        "testing_penalty": penalties["testing"],
        "quality_penalty": penalties["quality"],

        # === SEVERITY LABELS ===
        "security_severity": security_severity,
        "coverage_severity": coverage_severity,

        # === NORMALIZED SECTIONS ===
        "git": _normalize_git_info(raw_results),
        "structure": _normalize_structure(raw_results),
        "architecture": _normalize_architecture(raw_results),
        "security": _normalize_security(raw_results),
        "secrets": _normalize_secrets(raw_results),
        "tests": _normalize_tests(raw_results),
        "complexity": _normalize_complexity(raw_results),
        "efficiency": _normalize_efficiency(raw_results),
        "duplication": _normalize_duplication(raw_results),
        "quality": _normalize_quality(raw_results),
        "deadcode": _normalize_deadcode(raw_results),
        "cleanup": _normalize_cleanup(raw_results),
        "typing": _normalize_typing(raw_results),
        "gitignore": _normalize_gitignore(raw_results),

        # === TOOL EXECUTION SUMMARY ===
        "tools_summary": _build_tools_summary(raw_results),

        # === TOP PRIORITIES ===
        "top_priorities": _calculate_top_priorities(raw_results),

        # === REPORT INTEGRITY ===
        "all_sections_present": True,  # Will be validated later
        "missing_sections": [],  # Will be populated if needed
    }


def _calculate_grade(score: int) -> str:
    """Calculate letter grade from numeric score."""
    if score >= SCORE_A:
        return "A"
    if score >= SCORE_B:
        return "B"
    if score >= SCORE_C:
        return "C"
    if score >= SCORE_D:
        return "D"
    return "F"


def _calculate_penalties(raw_results: dict[str, Any]) -> dict[str, int]:
    """Calculate penalty points for each category."""
    penalties = {
        "security": 0,
        "testing": 0,
        "quality": 0
    }

    # Security penalty
    security = raw_results.get("bandit") or raw_results.get("security", {})
    secrets = raw_results.get("secrets", {})

    if "code_security" in security:
        security_issues = len(security["code_security"].get("issues", []))
    else:
        security_issues = len(security.get("issues", []))

    secrets_found = len(secrets.get("secrets", []))

    penalties["security"] = min(
        MAX_SECURITY_PENALTY,
        (security_issues * SECURITY_ISSUE_PENALTY) + (secrets_found * SECRET_FOUND_PENALTY)
    )

    # Testing penalty
    tests = raw_results.get("tests", {})
    coverage = tests.get("coverage_percent", 0)

    if coverage < COVERAGE_THRESHOLD_LOW:
        penalties["testing"] = PENALTY_TESTING_VERY_LOW
    elif coverage < COVERAGE_THRESHOLD_MODERATE:
        penalties["testing"] = PENALTY_TESTING_LOW
    elif coverage < COVERAGE_THRESHOLD_GOOD:
        penalties["testing"] = PENALTY_TESTING_MODERATE
    else:
        penalties["testing"] = 0

    # Quality penalty
    deadcode = raw_results.get("deadcode") or raw_results.get("dead_code", {})
    dead_functions = len(deadcode.get("dead_functions", []))
    unused_imports = len(deadcode.get("unused_imports", []))
    unused_vars = len(deadcode.get("unused_variables", []))
    total_dead = dead_functions + unused_imports + unused_vars

    penalties["quality"] = min(MAX_QUALITY_PENALTY, total_dead // DEAD_CODE_DIVISOR)

    return penalties


def _get_security_severity(raw_results: dict[str, Any]) -> dict[str, str]:
    """Get security severity label and description."""
    security = raw_results.get("bandit") or raw_results.get("security", {})

    if "code_security" in security:
        issues = len(security["code_security"].get("issues", []))
    else:
        issues = len(security.get("issues", []))

    if issues == 0:
        return {
            "label": "✅ Clean",
            "description": "No security issues detected"
        }
    if issues < 5:
        return {
            "label": "🟡 Low",
            "description": "Minor security issues found"
        }
    if issues < 15:
        return {
            "label": "🟠 Medium",
            "description": "Moderate security concerns"
        }
    return {
        "label": "🔴 High",
        "description": "Significant security issues require attention"
    }


def _get_coverage_severity(raw_results: dict[str, Any]) -> dict[str, str]:
    """Get coverage severity label, description, and recommendation."""
    tests = raw_results.get("tests", {})
    coverage = tests.get("coverage_percent", 0)

    if coverage >= COVERAGE_THRESHOLD_GOOD:
        return {
            "label": "🟢 Excellent",
            "description": f"Excellent coverage ({coverage}%)",
            "recommendation": "Maintain current test coverage"
        }
    if coverage >= COVERAGE_THRESHOLD_MODERATE:
        return {
            "label": "🟡 Good",
            "description": f"Good coverage ({coverage}%)",
            "recommendation": "Continue improving to 80%+"
        }
    if coverage >= COVERAGE_THRESHOLD_LOW:
        return {
            "label": "🟠 Moderate",
            "description": f"Acceptable coverage ({coverage}%)",
            "recommendation": "Continue improving to 80%+"
        }
    if coverage > 0:
        return {
            "label": "🔴 Low",
            "description": f"Low coverage ({coverage}%)",
            "recommendation": "CRITICAL: Increase test coverage to at least 70%"
        }
    return {
        "label": "❌ None",
        "description": "No coverage data available",
        "recommendation": "CRITICAL: Add tests to achieve at least 70% coverage"
    }


def _normalize_git_info(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize git information - handles both 'git' and 'git_info' keys."""
    # Try git_info first (new format), then git (legacy)
    git_data = _extract_tool_data(raw_results, "git_info") or _extract_tool_data(raw_results, "git")
    if not git_data:
        return {
            "available": False,
            "branch": "N/A",
            "uncommitted_changes": 0,
            "last_commit": {},
            "status": "Not a git repository"
        }

    # Extract last commit info
    last_commit = git_data.get("last_commit", {})
    if isinstance(last_commit, str):
        # Legacy format: "hash : message"
        parts = last_commit.split(" : ", 1)
        last_commit = {
            "hash": parts[0] if parts else "N/A",
            "message": parts[1] if len(parts) > 1 else "",
            "author": git_data.get("commit_author", "Unknown"),
            "when": git_data.get("commit_date", "Unknown")
        }

    return {
        "available": True,
        "branch": git_data.get("branch", "unknown"),
        "uncommitted_changes": git_data.get("uncommitted_changes", 0),
        "last_commit": last_commit,
        "status": git_data.get("status", "Unknown"),
        "days_since_commit": git_data.get("days_since_commit", 0)
    }


def _normalize_structure(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize project structure data."""
    data = _extract_tool_data(raw_results, "structure")

    # Handle both 'directory_tree' and 'tree' field names
    tree = data.get("directory_tree") or data.get("tree", "N/A")

    return {
        "available": bool(data),
        "total_py_files": data.get("total_py_files") or data.get("total_files", 0),
        "total_files": data.get("total_py_files") or data.get("total_files", 0),
        "total_lines": data.get("total_lines", 0),
        "total_directories": len(data.get("top_directories", [])) or data.get("total_dirs", 0),
        "directory_tree": tree,
        "tree": tree,
        "top_directories": data.get("top_directories", [])
    }


def _normalize_architecture(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize architecture analysis data."""
    data = _extract_tool_data(raw_results, "architecture")

    return {
        "available": bool(data),
        "total_dependencies": data.get("total_dependencies", 0),
        "total_files": data.get("total_files", 0),
        "mermaid_graph": data.get("mermaid_graph", ""),
        "has_graph": bool(data.get("mermaid_graph")),
        "nodes": data.get("nodes", []),
        "issues": data.get("issues", []),
        "has_issues": len(data.get("issues", [])) > 0
    }


def _normalize_security(raw_results: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize security (Bandit) data.

    Handles BOTH:
    1. Bandit field names (issue_severity, filename, issue_text, line_number)
    2. Standard field names (severity, file, message, line) - from FastAuditTool or pre-normalized
    """
    # Extract tool data handling nested structure
    bandit_data = _extract_tool_data(raw_results, 'bandit') or _extract_tool_data(raw_results, 'security')

    # Also handle 'code_security' wrapper if present
    if 'code_security' in bandit_data:
        bandit_data = bandit_data['code_security']

    raw_issues = bandit_data.get('issues', [])

    # Map fields to template-expected format
    # Check BOTH Bandit field names AND standard field names
    issues = []
    for issue in raw_issues:
        issues.append({
            # Prefer standard names, fall back to Bandit names, then defaults
            'severity': issue.get('severity') or issue.get('issue_severity', 'MEDIUM'),
            'file': issue.get('file') or issue.get('filename', ''),
            'line': issue.get('line') or issue.get('line_number', 0),
            'message': issue.get('message') or issue.get('issue_text', ''),
            'code': issue.get('code') or issue.get('test_id', ''),
            'confidence': issue.get('confidence') or issue.get('issue_confidence', 'MEDIUM'),
            'more_info': issue.get('more_info', ''),
            'cwe': issue.get('cwe') or issue.get('issue_cwe', {})
        })

    return {
        'available': bool(bandit_data) and 'error' not in bandit_data,
        'files_scanned': bandit_data.get('files_scanned', 0),
        'total_issues': len(issues),
        'issues': issues[:20],  # Limit to top 20 for display
        'has_issues': len(issues) > 0,
        'severity_counts': _count_by_severity(issues)
    }


def _normalize_secrets(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize secrets detection data."""
    data = _extract_tool_data(raw_results, "secrets")
    secrets = data.get("secrets", [])

    return {
        "available": bool(data),
        "total_secrets": len(secrets),
        "secrets": secrets,
        "has_secrets": len(secrets) > 0,
        "status": data.get("status", "unknown")
    }


def _generate_test_warning(data: dict[str, Any], total_files: int, total_executed: int) -> str:
    """Generate warning message for test execution anomalies."""
    warning = data.get("warning", "")

    # Validation: Test files found but no results
    if total_files > 0 and total_executed == 0:
        msg = "⚠️ Test files found but no tests executed."
        warning = f"{warning} {msg}" if warning else msg

    # Validation: Coverage reported but no test files
    coverage_percent = data.get("coverage_percent", 0)
    if coverage_percent > 0 and total_files == 0:
        msg = "⚠️ Coverage reported but no test files detected."
        warning = f"{warning} {msg}" if warning else msg

    return warning


def _normalize_tests(raw_results: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize test execution data.

    Handles BOTH flat and nested data structures.
    """
    data = _extract_tool_data(raw_results, 'tests')

    total_files = data.get('total_test_files', 0)
    tests_passed = data.get('tests_passed', 0)
    tests_failed = data.get('tests_failed', 0)
    tests_skipped = data.get('tests_skipped', 0)
    total_executed = tests_passed + tests_failed

    # Detect premature stop
    premature_stop = (
        total_files > 0 and
        total_executed > 0 and
        total_executed < total_files
    )

    warning = data.get('warning', '')
    coverage_percent = data.get('coverage_percent', 0)

    # Validation: Test files found but no results
    # FIXED: Only show warning if BOTH no tests reported AND coverage is 0
    # If coverage > 0, tests definitely ran even if passed/failed counters are 0
    if total_files > 0 and total_executed == 0 and coverage_percent == 0:
        msg = "⚠️ Test files found but no tests executed."
        warning = f"{warning} {msg}" if warning else msg

    # Get raw_breakdown from JSON (may be None from TestsTool)
    raw_breakdown = data.get('test_breakdown') or {}

    # Check raw_breakdown for files if total_files (from total_test_files) is 0
    if total_files == 0:
        total_files = raw_breakdown.get('total_files', 0)

    # Validation: Coverage reported but no test files
    if coverage_percent > 0 and total_files == 0:
        msg = "⚠️ Coverage reported but no test files detected."
        warning = f"{warning} {msg}" if warning else msg

    # Get test_list to count actual test functions
    test_list = data.get('test_list', [])
    total_tests = len(test_list)

    # Count actual tests by category (based on path in test_list)
    # Handle various path formats: tests/e2e/..., e2e/..., /e2e/...
    unit_tests_count = 0
    integration_tests_count = 0
    e2e_tests_count = 0

    for test_id in test_list:
        test_path = test_id.lower().replace('\\', '/')
        # Check for integration tests (path contains /integration/ or starts with integration/)
        if '/integration/' in test_path or test_path.startswith('integration/'):
            integration_tests_count += 1
        # Check for e2e tests (path contains /e2e/ or starts with e2e/)
        elif '/e2e/' in test_path or test_path.startswith('e2e/'):
            e2e_tests_count += 1
        else:
            unit_tests_count += 1

    # Build test_breakdown with ACTUAL TEST COUNTS
    test_breakdown = {
        'unit': unit_tests_count if total_tests > 0 else raw_breakdown.get('unit', 0),
        'integration': integration_tests_count if total_tests > 0 else raw_breakdown.get('integration', 0),
        'e2e': e2e_tests_count if total_tests > 0 else raw_breakdown.get('e2e', 0),
        'total_files': raw_breakdown.get('total_files', total_files)
    }

    # Also keep file counts for reference
    file_breakdown = {
        'unit': raw_breakdown.get('unit', 0),
        'integration': raw_breakdown.get('integration', 0),
        'e2e': raw_breakdown.get('e2e', 0),
        'total_files': raw_breakdown.get('total_files', total_files)
    }

    # Determine has_* flags - use TestsTool booleans as fallback
    has_unit = (test_breakdown['unit'] > 0 or file_breakdown['unit'] > 0
                or data.get('has_unit_tests', False))
    has_integration = (test_breakdown['integration'] > 0 or file_breakdown['integration'] > 0
                       or data.get('has_integration_tests', False))
    has_e2e = (test_breakdown['e2e'] > 0 or file_breakdown['e2e'] > 0
               or data.get('has_e2e_tests', False))

    return {
        'available': bool(data),
        'coverage_percent': coverage_percent,
        'coverage_report': data.get('coverage_report', ''),
        'total_test_files': total_files,
        'total_tests': total_tests,
        'tests_passed': tests_passed,
        'tests_failed': tests_failed,
        'tests_skipped': tests_skipped,
        'total_executed': total_executed,
        'premature_stop': premature_stop,
        'has_unit': has_unit,
        'has_integration': has_integration,
        'has_e2e': has_e2e,
        'test_breakdown': test_breakdown,
        'file_breakdown': file_breakdown,
        'test_list': test_list,
        'warning': warning
    }


def _normalize_complexity(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize complexity analysis data."""
    data = _extract_tool_data(raw_results, "complexity")

    # Fallback 1: Check efficiency data (FastAuditTool includes complexity)
    if not data:
        efficiency_data = _extract_tool_data(raw_results, "efficiency")
        if efficiency_data:
            complexity_issues = efficiency_data.get("complexity", [])
            high_complexity = efficiency_data.get("high_complexity_functions", [])

            if complexity_issues or high_complexity:
                return {
                    "available": True,
                    "total_functions": efficiency_data.get("total_functions_analyzed", "N/A"),
                    "average_complexity": efficiency_data.get("average_complexity", "N/A"),
                    "high_complexity": complexity_issues or high_complexity,
                    "very_high_complexity": [],
                    "has_complex_functions": len(complexity_issues or high_complexity) > 0
                }

    # Fallback 2: Check Ruff (quality) complexity findings
    if not data and ("quality" in raw_results or "ruff" in raw_results):
        ruff_data = _extract_tool_data(raw_results, "quality") or _extract_tool_data(raw_results, "ruff")
        complexity_issues = ruff_data.get("complexity", [])

        if complexity_issues:
            return {
                "available": True,
                "total_functions": "N/A",
                "average_complexity": "N/A",
                "high_complexity": complexity_issues,
                "very_high_complexity": [],
                "has_complex_functions": len(complexity_issues) > 0
            }

    return {
        "available": bool(data),
        "total_functions": data.get("total_functions_analyzed", 0),
        "average_complexity": data.get("average_complexity", 0),
        "high_complexity": data.get("high_complexity_functions", []),
        "very_high_complexity": data.get("very_high_complexity_functions", []),
        "has_complex_functions": len(data.get("high_complexity_functions", [])) > 0
    }


def _normalize_efficiency(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize efficiency analysis data."""
    data = _extract_tool_data(raw_results, "efficiency")

    # Handle FastAuditTool format (complexity list from ruff C901)
    complexity_items = data.get("complexity", [])
    high_complexity_functions = data.get("high_complexity_functions", [])

    # Convert FastAuditTool complexity items to high_complexity_functions format
    if complexity_items and not high_complexity_functions:
        import re
        for item in complexity_items:
            # Parse message like "`analyze_project` is too complex (14 > 10)"
            message = item.get("message", "")
            func_match = re.search(r"`(\w+)`", message)
            complexity_match = re.search(r"\((\d+)\s*>", message)

            func_name = func_match.group(1) if func_match else "unknown"
            complexity_val = int(complexity_match.group(1)) if complexity_match else 0

            high_complexity_functions.append({
                "file": item.get("file", "").replace("\\", "/").split("/")[-1],
                "name": func_name,
                "function": func_name,
                "complexity": complexity_val,
                "line": item.get("line", 0),
            })

    # Map high_complexity_functions to issues
    issues = data.get("issues", [])
    if not issues and high_complexity_functions:
        for func in high_complexity_functions:
            issues.append({
                "type": "High Complexity",
                "file": func.get("file", ""),
                "line": func.get("line", ""),
                "description": f"Complexity: {func.get('complexity', 0)} (Function: {func.get('name', func.get('function', ''))})"
            })

    return {
        "available": bool(data) or bool(high_complexity_functions),
        "total_functions": data.get("total_functions_analyzed", 0),
        "total_functions_analyzed": data.get("total_functions_analyzed", 0),
        "total_high_complexity": len(high_complexity_functions),
        "high_complexity_functions": high_complexity_functions,
        "average_complexity": data.get("average_complexity", 0),
        "average_maintainability": data.get("average_maintainability", 0),
        "maintainability_grade": data.get("maintainability_grade", "N/A"),
        "files_analyzed": data.get("files_analyzed", 0),
        "performance_issues": data.get("performance_issues", []),
        "issues": issues,
        "has_issues": len(issues) > 0 or len(high_complexity_functions) > 0
    }


def _normalize_duplication(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize code duplication data."""
    data = _extract_tool_data(raw_results, "duplication")
    duplicates = data.get("duplicates", [])

    # Group by file for better display
    file_groups = defaultdict(list)

    for dup in duplicates:
        locations = dup.get("locations", [])
        if locations:
            primary_file = locations[0].split(":")[0]
            file_groups[primary_file].append(dup)

    sorted_files = sorted(file_groups.items(), key=lambda x: -len(x[1]))

    return {
        "available": bool(data),
        "total_duplicates": len(duplicates),
        "total_functions_analyzed": data.get("total_functions_analyzed", 0),
        "duplicates": duplicates,
        "file_groups": sorted_files[:10],
        "has_duplicates": len(duplicates) > 0
    }


def _normalize_deadcode(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize dead code detection data."""
    data = _extract_tool_data(raw_results, "deadcode") or _extract_tool_data(raw_results, "dead_code")

    dead_functions = data.get("dead_functions", [])
    unused_imports = data.get("unused_imports", [])
    unused_vars = data.get("unused_variables", []) or data.get("dead_variables", [])

    total = len(dead_functions) + len(unused_imports) + len(unused_vars)

    return {
        "available": bool(data) and "error" not in data,
        "dead_functions": dead_functions[:10],
        "unused_imports": unused_imports[:10],
        "unused_vars": unused_vars[:10],
        "total_dead_functions": len(dead_functions),
        "total_unused_imports": len(unused_imports),
        "total_unused_vars": len(unused_vars),
        "total_items": total,  # ADDED: for template
        "has_dead_code": total > 0,
        "error": data.get("error")
    }


def _normalize_cleanup(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize cleanup recommendations data."""
    data = _extract_tool_data(raw_results, "cleanup")

    # Handle both 'cleanup_targets' and 'targets' field names
    targets = data.get("cleanup_targets") or data.get("targets", {})

    return {
        "available": bool(data),
        "total_size_mb": data.get("total_size_mb", 0),
        "cleanup_items": data.get("items", []),
        "cleanup_targets": targets,
        "has_cleanup": len(data.get("items", [])) > 0
    }


def _normalize_typing(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize type coverage data."""
    data = _extract_tool_data(raw_results, "typing")

    return {
        "available": bool(data),
        "coverage_percent": data.get("coverage_percent") or data.get("type_coverage_percent", -1),
        "untyped_functions": data.get("untyped_functions", 0),
        "typed_functions": data.get("typed_functions") or data.get("fully_typed_functions", 0),
        "total_functions": data.get("total_functions", 0),
        "has_untyped": data.get("untyped_functions", 0) > 0
    }


def _normalize_gitignore(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize gitignore recommendations data."""
    data = _extract_tool_data(raw_results, "gitignore")

    return {
        "available": bool(data),
        "suggestions": data.get("suggestions", []),
        "has_suggestions": len(data.get("suggestions", [])) > 0
    }


def _build_tools_summary(raw_results: dict[str, Any]) -> list[dict[str, Any]]:
    """Build tool execution summary for the table."""
    # Map display names to (primary_key, fallback_keys)
    tools = [
        ("structure", "📁 Structure", []),
        ("architecture", "🏗️ Architecture", []),
        ("typing", "📝 Type Coverage", []),
        ("complexity", "🧮 Complexity", ["efficiency"]),  # Complexity comes from efficiency/FastAudit
        ("duplication", "🎭 Duplication", []),
        ("dead_code", "☠️ Dead Code", ["deadcode"]),  # Handle both key names
        ("efficiency", "⚡ Efficiency", []),
        ("cleanup", "🧹 Cleanup", []),
        ("bandit", "🔒 Security (Bandit)", []),
        ("secrets", "🔐 Secrets", []),
        ("ruff", "🧹 Code Quality (Ruff)", ["quality"]),  # Also check 'quality' key
        ("tests", "✅ Tests", []),
        ("gitignore", "📋 Gitignore", []),
        ("git_info", "📝 Git Status", ["git"]),
    ]

    summary = []

    for key, name, fallbacks in tools:
        # Try primary key first, then fallbacks
        raw_data = raw_results.get(key)
        tool_data = _extract_tool_data(raw_results, key)

        # Try fallback keys if primary not found
        if not tool_data:
            for fallback in fallbacks:
                raw_data = raw_results.get(fallback) or raw_data
                tool_data = _extract_tool_data(raw_results, fallback)
                if tool_data:
                    break

        status, details = _get_tool_status(key, tool_data)

        # Extract duration - check both wrapper (execution_time_ms) and inner (duration_s)
        duration_s = 0
        if isinstance(raw_data, dict):
            # Try execution_time_ms first (from JSON wrapper), convert to seconds
            exec_time_ms = raw_data.get("execution_time_ms", 0)
            if exec_time_ms:
                duration_s = exec_time_ms / 1000.0
            else:
                # Fall back to duration_s from inner data
                duration_s = tool_data.get("duration_s", 0) if isinstance(tool_data, dict) else 0

        summary.append({
            "name": name,
            "status": status,
            "details": details,
            "duration_s": f"{duration_s:.2f}" if duration_s else "0.00"
        })

    return summary


def _get_structure_status(data: dict[str, Any]) -> tuple:
    files = data.get("total_py_files", 0)
    dirs = len(data.get("top_directories", []))
    return "ℹ️ Info", f"{files} files, {dirs} dirs"


def _get_security_status(data: dict[str, Any]) -> tuple:
    # Handle nested structure
    if "code_security" in data:
        issues = len(data["code_security"].get("issues", []))
        files = data["code_security"].get("files_scanned", 0)
    else:
        issues = len(data.get("issues", []))
        files = data.get("files_scanned", 0)

    if issues == 0:
        return "✅ Pass", f"Scanned {files} files, 0 issues"
    return "⚠️ Issues", f"{issues} vulnerability(ies) in {files} files"


def _get_tests_status(data: dict[str, Any]) -> tuple:
    failed = data.get("tests_failed", 0)
    if failed > 0:
        return "❌ Fail", f"{failed} test(s) failed"

    coverage = data.get("coverage_percent", -1)
    total_files = data.get("total_test_files", 0)

    if coverage < 0:
        return "❌ Fail", "Coverage calculation failed"

    return "ℹ️ Info", f"{total_files} test files, {coverage}% coverage"


def _get_git_status(data: dict[str, Any]) -> tuple:
    if data.get("branch"):
        branch = data.get("branch")
        changes = data.get("uncommitted_changes", 0)
        return "ℹ️ Info", f"Branch: {branch}, {changes} pending"
    return "ℹ️ Info", "Not a git repository"


def _get_secrets_status(data: dict[str, Any]) -> tuple:
    secrets = len(data.get("secrets", []))
    if secrets == 0:
        return "✅ Pass", "No secrets detected"
    return "❌ Fail", f"{secrets} potential secret(s)"


def _get_cleanup_status(data: dict[str, Any]) -> tuple:
    items = len(data.get("items", []))
    size_mb = data.get("total_size_mb", 0)

    if items == 0:
        return "✅ Pass", "Environment is clean"
    return "ℹ️ Info", f"{items} item(s), {size_mb:.1f}MB"


def _get_generic_status(data: dict[str, Any]) -> tuple:
    issues = data.get("issues", []) or data.get("duplicates", [])

    if isinstance(issues, list) and len(issues) == 0:
        return "✅ Pass", "No issues found"
    if isinstance(issues, list):
        return "⚠️ Issues", f"{len(issues)} issue(s) found"

    return "ℹ️ Info", "Analysis complete"


def _get_tool_status(tool_key: str, data: dict[str, Any]) -> tuple:
    """Get status and details for a specific tool."""
    if not data:
        return "⚠️ Skip", "Tool did not run"

    if "error" in data:
        return "❌ Fail", f"Error: {data.get('error', 'Unknown')}"

    handlers = {
        "structure": _get_structure_status,
        "security": _get_security_status,
        "bandit": _get_security_status,
        "tests": _get_tests_status,
        "git_info": _get_git_status,
        "git": _get_git_status,
        "secrets": _get_secrets_status,
        "cleanup": _get_cleanup_status,
    }

    handler = handlers.get(tool_key, _get_generic_status)
    return handler(data)


def _calculate_top_priorities(raw_results: dict[str, Any]) -> list[dict[str, Any]]:
    """Calculate top 3 priority fixes with impact estimates."""
    priorities = []

    # Architecture issues
    arch_data = raw_results.get("architecture", {})
    if arch_data.get("issues"):
        priorities.append({
            "title": "Architecture: Improve modularity",
            "impact": 15,
            "description": "Centralize endpoints and models to improve code organization"
        })

    # Typing issues
    typing_data = raw_results.get("typing", {})
    untyped = typing_data.get("untyped_functions", 0)
    if untyped > 100:
        priorities.append({
            "title": f"Types: {untyped} untyped functions",
            "impact": 12,
            "description": "Add type hints to prevent runtime errors"
        })

    # Duplication issues
    dup_data = raw_results.get("duplication", {})
    dups = len(dup_data.get("duplicates", []))
    if dups > 10:
        priorities.append({
            "title": f"Duplicates: {dups} code blocks",
            "impact": 8,
            "description": "Extract common patterns into reusable functions"
        })

    return priorities[:3]


def _normalize_quality(raw_results: dict[str, Any]) -> dict[str, Any]:
    """Normalize quality/linting data (from Ruff/FastAudit)."""
    data = _extract_tool_data(raw_results, "quality") or _extract_tool_data(raw_results, "ruff")

    issues = []

    # 1. Try aggregated categories (FastAuditTool)
    if "quality" in data or "style" in data:
        issues.extend(data.get("quality", []))
        issues.extend(data.get("style", []))
        issues.extend(data.get("imports", []))
        issues.extend(data.get("performance", []))

    # 2. Fallback to flat 'issues' list (Basic Ruff)
    elif "issues" in data:
        all_issues = data.get("issues", [])

        # Filter out Security (S) and Complexity (C90) issues as they have their own sections
        issues = [
            i for i in all_issues
            if not (i.get("code", "").startswith("S") or i.get("code", "").startswith("C90"))
        ]

    return {
        "available": bool(data) and "error" not in data,
        "total_issues": len(issues),
        "issues": issues,
        "has_issues": len(issues) > 0,
        "severity_counts": _count_by_severity(issues),
        "files_with_issues": data.get("files_with_issues", 0)
    }


def _count_by_severity(issues: list[dict[str, Any]]) -> dict[str, int]:
    """
    Count issues by severity level.
    
    FIXED: Now works with normalized 'severity' field
    """
    counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    
    for issue in issues:
        severity = issue.get('severity', 'MEDIUM').upper()
        if severity in counts:
            counts[severity] += 1
        else:
            counts['MEDIUM'] += 1
    
    return counts
