"""Data normalization layer for audit report context.

This module transforms raw audit results into a clean, normalized context
for Jinja2 template rendering. It handles missing keys, inconsistent formats,
and provides safe defaults to prevent "N/A" bugs.
"""
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def build_report_context(
    raw_results: Dict[str, Any],
    project_path: str,
    score: int,
    report_id: str,
    timestamp: datetime
) -> Dict[str, Any]:
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
        
    Returns:
        Normalized context dictionary ready for template rendering
    """
    context = {
        # === METADATA ===
        'project_name': Path(project_path).name,
        'score': score,
        'report_id': report_id,
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M'),
        'date': timestamp.strftime('%Y-%m-%d'),
        'time': timestamp.strftime('%H:%M'),
        
        # === NORMALIZED SECTIONS ===
        'git': _normalize_git_info(raw_results),
        'structure': _normalize_structure(raw_results),
        'architecture': _normalize_architecture(raw_results),
        'security': _normalize_security(raw_results),
        'secrets': _normalize_secrets(raw_results),
        'tests': _normalize_tests(raw_results),
        'complexity': _normalize_complexity(raw_results),
        'efficiency': _normalize_efficiency(raw_results),
        'duplication': _normalize_duplication(raw_results),
        'quality': _normalize_quality(raw_results),
        'deadcode': _normalize_deadcode(raw_results),
        'cleanup': _normalize_cleanup(raw_results),
        'typing': _normalize_typing(raw_results),
        'gitignore': _normalize_gitignore(raw_results),
        
        # === TOOL EXECUTION SUMMARY ===
        'tools_summary': _build_tools_summary(raw_results),
        
        # === TOP PRIORITIES ===
        'top_priorities': _calculate_top_priorities(raw_results),
    }
    
    return context


def _normalize_git_info(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize git information - handles both 'git' and 'git_info' keys."""
    # Try git_info first (new format), then git (legacy)
    git_data = raw_results.get('git_info') or raw_results.get('git', {})
    
    if not git_data:
        return {
            'available': False,
            'branch': 'N/A',
            'uncommitted_changes': 0,
            'last_commit': {},
            'status': 'Not a git repository'
        }
    
    # Extract last commit info
    last_commit = git_data.get('last_commit', {})
    if isinstance(last_commit, str):
        # Legacy format: "hash : message"
        parts = last_commit.split(' : ', 1)
        last_commit = {
            'hash': parts[0] if parts else 'N/A',
            'message': parts[1] if len(parts) > 1 else '',
            'author': git_data.get('commit_author', 'Unknown'),
            'when': git_data.get('commit_date', 'Unknown')
        }
    
    return {
        'available': True,
        'branch': git_data.get('branch', 'unknown'),
        'uncommitted_changes': git_data.get('uncommitted_changes', 0),
        'last_commit': last_commit,
        'status': git_data.get('status', 'Unknown'),
        'days_since_commit': git_data.get('days_since_commit', 0)
    }


def _normalize_structure(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize project structure data."""
    data = raw_results.get('structure', {})
    
    return {
        'available': bool(data),
        'total_files': data.get('total_py_files', 0),
        'total_lines': data.get('total_lines', 0),
        'total_directories': len(data.get('top_directories', [])),
        'tree': data.get('directory_tree', 'N/A'),
        'top_directories': data.get('top_directories', [])
    }


def _normalize_architecture(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize architecture analysis data."""
    data = raw_results.get('architecture', {})
    
    return {
        'available': bool(data),
        'total_dependencies': data.get('total_dependencies', 0),
        'total_files': data.get('total_files', 0),
        'mermaid_graph': data.get('mermaid_graph', ''),
        'has_graph': bool(data.get('mermaid_graph')),
        'nodes': data.get('nodes', []),
        'issues': data.get('issues', []),
        'has_issues': len(data.get('issues', [])) > 0
    }


def _normalize_security(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize security (Bandit) data."""
    data = raw_results.get('bandit') or raw_results.get('security', {})
    
    # Handle nested structure
    if 'code_security' in data:
        bandit_data = data['code_security']
    else:
        bandit_data = data
    
    issues = bandit_data.get('issues', [])
    
    return {
        'available': bool(data) and 'error' not in data,
        'files_scanned': bandit_data.get('files_scanned', 0),
        'total_issues': len(issues),
        'issues': issues[:20],  # Limit to top 20 for display
        'has_issues': len(issues) > 0,
        'severity_counts': _count_by_severity(issues)
    }


def _normalize_secrets(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize secrets detection data."""
    data = raw_results.get('secrets', {})
    secrets = data.get('secrets', [])
    
    return {
        'available': bool(data),
        'total_secrets': len(secrets),
        'secrets': secrets,
        'has_secrets': len(secrets) > 0,
        'status': data.get('status', 'unknown')
    }


def _normalize_tests(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize test execution data."""
    data = raw_results.get('tests', {})
    
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

    # Validation: Test files found but no results
    if total_files > 0 and total_executed == 0:
        msg = "⚠️ Test files found but no tests executed."
        warning = f"{warning} {msg}" if warning else msg

    # Validation: Coverage reported but no test files
    coverage_percent = data.get('coverage_percent', 0)
    if coverage_percent > 0 and total_files == 0:
        msg = "⚠️ Coverage reported but no test files detected."
        warning = f"{warning} {msg}" if warning else msg
    
    return {
        'available': bool(data),
        'coverage_percent': data.get('coverage_percent', -1),
        'coverage_report': data.get('coverage_report', ''),
        'total_test_files': total_files,
        'tests_passed': tests_passed,
        'tests_failed': tests_failed,
        'tests_skipped': tests_skipped,
        'total_executed': total_executed,
        'premature_stop': premature_stop,
        'has_unit': data.get('has_unit_tests', False),
        'has_integration': data.get('has_integration_tests', False),
        'has_e2e': data.get('has_e2e_tests', False),
        'test_breakdown': data.get('test_breakdown', {}),
        'warning': warning
    }


def _normalize_complexity(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize complexity analysis data."""
    data = raw_results.get('complexity', {})
    
    # Fallback to Ruff (quality) complexity findings if main tool missing
    if not data and ('quality' in raw_results or 'ruff' in raw_results):
        ruff_data = raw_results.get('quality') or raw_results.get('ruff', {})
        complexity_issues = ruff_data.get('complexity', [])
        if complexity_issues:
            return {
                'available': True,
                'total_functions': 'N/A', # Not available from Ruff directly
                'average_complexity': 'N/A',
                'high_complexity': complexity_issues, # Mapping Ruff complexity issues
                'very_high_complexity': [], 
                'has_complex_functions': len(complexity_issues) > 0
            }

    return {
        'available': bool(data),
        'total_functions': data.get('total_functions_analyzed', 0),
        'average_complexity': data.get('average_complexity', 0),
        'high_complexity': data.get('high_complexity_functions', []),
        'very_high_complexity': data.get('very_high_complexity_functions', []),
        'has_complex_functions': len(data.get('high_complexity_functions', [])) > 0
    }


def _normalize_efficiency(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize efficiency analysis data."""
    data = raw_results.get('efficiency', {})
    
    # Map high_complexity_functions to issues if needed
    issues = data.get('issues', [])
    if not issues and 'high_complexity_functions' in data:
        for func in data.get('high_complexity_functions', []):
            issues.append({
                'type': 'High Complexity',
                'file': func.get('file', ''),
                'line': func.get('line', ''),
                'description': f"Complexity: {func.get('complexity', 0)} (Function: {func.get('function', '')})"
            })
    
    return {
        'available': bool(data),
        'total_functions': data.get('total_functions_analyzed', 0),
        'average_complexity': data.get('average_complexity', 0),
        'average_maintainability': data.get('average_maintainability', 0),
        'maintainability_grade': data.get('maintainability_grade', 'N/A'),
        'files_analyzed': data.get('files_analyzed', 0),
        'issues': issues,
        'has_issues': len(issues) > 0
    }


def _normalize_duplication(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize code duplication data."""
    data = raw_results.get('duplication', {})
    duplicates = data.get('duplicates', [])
    
    # Group by file for better display
    from collections import defaultdict
    file_groups = defaultdict(list)
    for dup in duplicates:
        locations = dup.get('locations', [])
        if locations:
            primary_file = locations[0].split(':')[0]
            file_groups[primary_file].append(dup)
    
    sorted_files = sorted(file_groups.items(), key=lambda x: -len(x[1]))
    
    return {
        'available': bool(data),
        'total_duplicates': len(duplicates),
        'total_functions_analyzed': data.get('total_functions_analyzed', 0),
        'duplicates': duplicates,
        'file_groups': sorted_files[:10],  # Top 10 files
        'has_duplicates': len(duplicates) > 0
    }


def _normalize_deadcode(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize dead code detection data."""
    data = raw_results.get('deadcode') or raw_results.get('dead_code', {})
    
    dead_functions = data.get('dead_functions', [])
    unused_imports = data.get('unused_imports', [])
    unused_vars = data.get('unused_variables', [])
    
    total = len(dead_functions) + len(unused_imports) + len(unused_vars)
    
    return {
        'available': bool(data) and 'error' not in data,
        'dead_functions': dead_functions[:10],  # Limit display
        'unused_imports': unused_imports[:10],
        'unused_vars': unused_vars[:10],
        'total_dead_functions': len(dead_functions),
        'total_unused_imports': len(unused_imports),
        'total_unused_vars': len(unused_vars),
        'total_items': total,
        'has_dead_code': total > 0,
        'error': data.get('error')
    }


def _normalize_cleanup(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize cleanup recommendations data."""
    data = raw_results.get('cleanup', {})
    
    return {
        'available': bool(data),
        'total_size_mb': data.get('total_size_mb', 0),
        'items': data.get('items', []),
        'cleanup_targets': data.get('cleanup_targets', {}),
        'has_cleanup': len(data.get('items', [])) > 0
    }


def _normalize_typing(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize type coverage data."""
    data = raw_results.get('typing', {})
    
    return {
        'available': bool(data),
        'coverage_percent': data.get('coverage_percent', -1),
        'untyped_functions': data.get('untyped_functions', 0),
        'typed_functions': data.get('typed_functions', 0),
        'total_functions': data.get('total_functions', 0),
        'has_untyped': data.get('untyped_functions', 0) > 0
    }


def _normalize_gitignore(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize gitignore recommendations data."""
    data = raw_results.get('gitignore', {})
    
    return {
        'available': bool(data),
        'suggestions': data.get('suggestions', []),
        'has_suggestions': len(data.get('suggestions', [])) > 0
    }


def _build_tools_summary(raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build tool execution summary for the table."""
    tools = [
        ('structure', '📁 Structure'),
        ('architecture', '🏗️ Architecture'),
        ('typing', '📝 Type Coverage'),
        ('complexity', '🧮 Complexity'),
        ('duplication', '🎭 Duplication'),
        ('deadcode', '☠️ Dead Code'),
        ('efficiency', '⚡ Efficiency'),
        ('cleanup', '🧹 Cleanup'),
        ('secrets', '🔐 Secrets'),
        ('quality', '🧹 Code Quality'),
        ('security', '🔒 Security (Bandit)'),
        ('tests', '✅ Tests'),
        ('gitignore', '📋 Gitignore'),
        ('git_info', '📝 Git Status'),
    ]
    
    summary = []
    for key, name in tools:
        # Try both possible keys
        data = raw_results.get(key) or raw_results.get(key.replace('_info', ''), {})
        
        status, details = _get_tool_status(key, data)
        summary.append({
            'name': name,
            'status': status,
            'details': details
        })
    
    return summary


def _get_tool_status(tool_key: str, data: Dict[str, Any]) -> tuple:
    """Get status and details for a specific tool."""
    if not data:
        return '⚠️ Skip', 'Tool did not run'
    
    if 'error' in data:
        return '❌ Fail', f"Error: {data.get('error', 'Unknown')}"
    
    # Tool-specific logic
    if tool_key == 'structure':
        files = data.get('total_py_files', 0)
        dirs = len(data.get('top_directories', []))
        return 'ℹ️ Info', f'{files} files, {dirs} dirs'
    
    elif tool_key == 'security':
        # Handle nested structure
        if 'code_security' in data:
            issues = len(data['code_security'].get('issues', []))
            files = data['code_security'].get('files_scanned', 0)
        else:
            issues = len(data.get('issues', []))
            files = data.get('files_scanned', 0)
        
        if issues == 0:
            return '✅ Pass', f'Scanned {files} files, 0 issues'
        return '⚠️ Issues', f'{issues} vulnerability(ies) in {files} files'
    
    elif tool_key == 'tests':
        failed = data.get('tests_failed', 0)
        if failed > 0:
            return '❌ Fail', f'{failed} test(s) failed'
        coverage = data.get('coverage_percent', -1)
        total_files = data.get('total_test_files', 0)
        if coverage < 0:
            return '❌ Fail', 'Coverage calculation failed'
        return 'ℹ️ Info', f'{total_files} test files, {coverage}% coverage'
    
    elif tool_key in ('git_info', 'git'):
        if data.get('branch'):
            branch = data.get('branch')
            changes = data.get('uncommitted_changes', 0)
            return 'ℹ️ Info', f'Branch: {branch}, {changes} pending'
        return 'ℹ️ Info', 'Not a git repository'
    
    elif tool_key == 'secrets':
        secrets = len(data.get('secrets', []))
        if secrets == 0:
            return '✅ Pass', 'No secrets detected'
        return '❌ Fail', f'{secrets} potential secret(s)'
    
    elif tool_key == 'cleanup':
        items = len(data.get('items', []))
        size_mb = data.get('total_size_mb', 0)
        if items == 0:
            return '✅ Pass', 'Environment is clean'
        return 'ℹ️ Info', f'{items} item(s), {size_mb:.1f}MB'
    
    # Generic handling for other tools
    issues = data.get('issues', []) or data.get('duplicates', [])
    if isinstance(issues, list) and len(issues) == 0:
        return '✅ Pass', 'No issues found'
    elif isinstance(issues, list):
        return '⚠️ Issues', f'{len(issues)} issue(s) found'
    
    return 'ℹ️ Info', 'Analysis complete'



def _calculate_top_priorities(raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Calculate top 3 priority fixes with impact estimates."""
    priorities = []
    
    # Architecture issues
    arch_data = raw_results.get('architecture', {})
    if arch_data.get('issues'):
        priorities.append({
            'title': 'Architecture: Improve modularity',
            'impact': 15,
            'description': 'Centralize endpoints and models to improve code organization'
        })
    
    # Typing issues
    typing_data = raw_results.get('typing', {})
    untyped = typing_data.get('untyped_functions', 0)
    if untyped > 100:
        priorities.append({
            'title': f'Types: {untyped} untyped functions',
            'impact': 12,
            'description': 'Add type hints to prevent runtime errors'
        })
    
    # Duplication issues
    dup_data = raw_results.get('duplication', {})
    dups = len(dup_data.get('duplicates', []))
    if dups > 10:
        priorities.append({
            'title': f'Duplicates: {dups} code blocks',
            'impact': 8,
            'description': 'Extract common patterns into reusable functions'
        })
    
    return priorities[:3]


def _normalize_quality(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize quality/linting data (from Ruff/FastAudit)."""
    data = raw_results.get('quality') or raw_results.get('ruff', {})
    
    issues = []
    
    # 1. Try aggregated categories (FastAuditTool)
    if 'quality' in data or 'style' in data:
        issues.extend(data.get('quality', []))
        issues.extend(data.get('style', []))
        issues.extend(data.get('imports', []))
        issues.extend(data.get('performance', []))
    
    # 2. Fallback to flat 'issues' list (Basic Ruff)
    elif 'issues' in data:
        all_issues = data.get('issues', [])
        # Filter out Security (S) and Complexity (C90) issues as they have their own sections
        issues = [
            i for i in all_issues 
            if not (i.get('code', '').startswith('S') or i.get('code', '').startswith('C90'))
        ]
    
    return {
        'available': bool(data) and 'error' not in data,
        'total_issues': len(issues),
        'issues': issues,  # All linting issues
        'has_issues': len(issues) > 0,
        'severity_counts': _count_by_severity(issues),
        'files_with_issues': data.get('files_with_issues', 0)
    }


def _count_by_severity(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count issues by severity level."""
    from collections import Counter
    severities = [issue.get('severity', 'UNKNOWN').upper() for issue in issues]
    return dict(Counter(severities))
