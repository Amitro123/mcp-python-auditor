"""Additional report section writers for enhanced metrics."""
from typing import Dict, Any


def _write_complexity_section(f, data: Dict[str, Any]) -> None:
    """Write complexity analysis section."""
    avg_complexity = data.get('average_complexity', 0)
    avg_mi = data.get('average_maintainability', 0)
    mi_grade = data.get('maintainability_grade', 'N/A')
    high_complexity = data.get('high_complexity_functions', [])
    very_high = data.get('very_high_complexity_functions', [])
    
    f.write(f"## 🔄 Complexity & Maintainability\n\n")
    f.write(f"**Maintainability Index:** {avg_mi:.1f}/100 (Grade: {mi_grade})\n")
    f.write(f"**Average Complexity:** {avg_complexity:.1f}\n\n")
    
    if very_high:
        f.write(f"**⚠️ Very High Complexity (>15):** {len(very_high)}\n")
        for func in very_high[:5]:
            f.write(f"- `{func.get('file', '')}:{func.get('function', '')}()` - ")
            f.write(f"CC: {func.get('complexity', 0)}\n")
        if len(very_high) > 5:
            f.write(f"\n*...and {len(very_high) - 5} more*\n")
        f.write("\n")
    
    if high_complexity:
        f.write(f"**High Complexity (>10):** {len(high_complexity)}\n")
        for func in high_complexity[:5]:
            f.write(f"- `{func.get('file', '')}:{func.get('function', '')}()` - ")
            f.write(f"CC: {func.get('complexity', 0)}\n")
        if len(high_complexity) > 5:
            f.write(f"\n*...and {len(high_complexity) - 5} more*\n")
        f.write("\n")
    
    if not high_complexity and not very_high:
        f.write("✅ No high complexity functions detected\n\n")


def _write_typing_section(f, data: Dict[str, Any]) -> None:
    """Write type coverage section."""
    coverage = data.get('type_coverage_percent', 0)
    grade = data.get('grade', 'F')
    total = data.get('total_functions', 0)
    typed = data.get('fully_typed_functions', 0)
    partial = data.get('partially_typed_functions', 0)
    untyped_examples = data.get('untyped_examples', [])
    
    f.write(f"## 🏷️ Type Hint Coverage: {coverage:.1f}% (Grade: {grade})\n\n")
    f.write(f"- Fully typed: {typed}/{total} functions\n")
    f.write(f"- Partially typed: {partial} functions\n")
    f.write(f"- Untyped: {total - typed - partial} functions\n\n")
    
    if untyped_examples:
        f.write("**Examples of untyped functions:**\n")
        for func in untyped_examples[:5]:
            f.write(f"- `{func.get('file', '')}:{func.get('function', '')}()`\n")
        f.write("\n")


def _write_security_section(f, data: Dict[str, Any]) -> None:
    """Write comprehensive security section."""
    total_issues = data.get('total_issues', 0)
    severity_counts = data.get('severity_counts', {})
    
    f.write(f"## 🔒 Security Analysis ({total_issues} issues)\n\n")
    
    if severity_counts:
        f.write("**Severity Breakdown:**\n")
        for severity, count in severity_counts.items():
            icon = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "🟢"
            f.write(f"- {icon} {severity}: {count}\n")
        f.write("\n")
    
    # Code security (Bandit)
    code_sec = data.get('code_security', {})
    if not code_sec.get('skipped', False):
        code_issues = code_sec.get('issues', [])
        if code_issues:
            f.write(f"**Code Security Issues (Bandit):** {len(code_issues)}\n")
            for issue in code_issues[:5]:
                f.write(f"- `{issue.get('file', '')}:{issue.get('line', '')}` - ")
                f.write(f"{issue.get('severity', 'UNKNOWN')}: {issue.get('issue', '')}\n")
            if len(code_issues) > 5:
                f.write(f"\n*...and {len(code_issues) - 5} more*\n")
            f.write("\n")
    
    # Dependency vulnerabilities
    dep_sec = data.get('dependency_security', {})
    if not dep_sec.get('skipped', False):
        vulns = dep_sec.get('vulnerabilities', [])
        if vulns:
            f.write(f"**Dependency Vulnerabilities (pip-audit):** {len(vulns)}\n")
            for vuln in vulns[:5]:
                f.write(f"- `{vuln.get('package', '')}` {vuln.get('version', '')} - ")
                f.write(f"{vuln.get('vulnerability_id', '')}\n")
            if len(vulns) > 5:
                f.write(f"\n*...and {len(vulns) - 5} more*\n")
            f.write("\n")
    
    # Secrets
    secrets_data = data.get('secrets', {})
    if not secrets_data.get('skipped', False):
        secrets = secrets_data.get('secrets', [])
        if secrets:
            f.write(f"**⚠️ Potential Secrets Detected:** {len(secrets)}\n")
            for secret in secrets[:5]:
                f.write(f"- `{secret.get('file', '')}:{secret.get('line', '')}` - ")
                f.write(f"{secret.get('type', 'Unknown')}\n")
            f.write("\n")
    
    if total_issues == 0:
        f.write("✅ No security issues detected\n\n")
