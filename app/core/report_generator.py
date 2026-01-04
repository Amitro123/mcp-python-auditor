"""Markdown report generator for audit results."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Import section writers
try:
    from app.core.report_sections import (
        _write_complexity_section,
        _write_typing_section,
        _write_security_section
    )
    HAS_ENHANCED_SECTIONS = True
except ImportError:
    HAS_ENHANCED_SECTIONS = False


class ReportGenerator:
    """Generate comprehensive markdown reports from audit results."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(
        self,
        report_id: str,
        project_path: str,
        score: int,
        tool_results: Dict[str, Any],
        timestamp: datetime
    ) -> str:
        """
        Generate a comprehensive markdown report.
        
        Args:
            report_id: Unique report identifier
            project_path: Path to the analyzed project
            score: Overall project score (0-100)
            tool_results: Results from all analysis tools
            timestamp: Report generation timestamp
            
        Returns:
            Path to the generated report file
        """
        report_path = self.reports_dir / f"{report_id}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"# Project Audit: {project_path}\n\n")
            f.write(f"**Date:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')} | ")
            f.write(f"**Score:** {score}/100\n\n")
            
            # Check for and display warnings prominently
            self._write_warnings_section(f, tool_results)
            
            f.write("---\n\n")
            
            # Top 3 Critical Issues Summary
            self._write_top_issues_summary(f, tool_results)
            
            # Git context (if available)
            if 'git' in tool_results:
                self._write_git_section(f, tool_results['git'])
            
            # Structure section
            if 'structure' in tool_results:
                self._write_structure_section(f, tool_results['structure'])
            
            # Architecture section
            if 'architecture' in tool_results:
                self._write_architecture_section(f, tool_results['architecture'])
            
            # Duplicates section
            if 'duplication' in tool_results:
                self._write_duplication_section(f, tool_results['duplication'])
            
            # Dead code section
            if 'deadcode' in tool_results:
                self._write_deadcode_section(f, tool_results['deadcode'])
            
            # Complexity section (NEW)
            if 'complexity' in tool_results:
                if HAS_ENHANCED_SECTIONS:
                    _write_complexity_section(f, tool_results['complexity'])
            
            # Type coverage section (NEW)
            if 'typing' in tool_results:
                if HAS_ENHANCED_SECTIONS:
                    _write_typing_section(f, tool_results['typing'])
            
            # Efficiency section
            if 'efficiency' in tool_results:
                self._write_efficiency_section(f, tool_results['efficiency'])
            
            # Security section (ENHANCED)
            if 'security' in tool_results:
                if HAS_ENHANCED_SECTIONS:
                    _write_security_section(f, tool_results['security'])
                elif 'secrets' in tool_results:
                    # Fallback to old secrets section
                    self._write_secrets_section(f, tool_results['secrets'])
            
            # Cleanup section
            if 'cleanup' in tool_results:
                self._write_cleanup_section(f, tool_results['cleanup'])
            
            # Secrets section (deprecated - now part of security)
            if 'secrets' in tool_results and 'security' not in tool_results:
                self._write_secrets_section(f, tool_results['secrets'])
            
            # Tests section
            if 'tests' in tool_results:
                self._write_tests_section(f, tool_results['tests'])
            
            # Gitignore section
            if 'gitignore' in tool_results:
                self._write_gitignore_section(f, tool_results['gitignore'])
        
        logger.info(f"Report generated: {report_path}")
        return str(report_path)
    
    def _write_warnings_section(self, f, tool_results: Dict[str, Any]) -> None:
        """Write prominent warnings for missing dependencies or prerequisites."""
        warnings = []
        
        # Check tests tool for pytest-cov warning
        if 'tests' in tool_results:
            tests_data = tool_results['tests']
            if 'warning' in tests_data:
                warning_msg = tests_data['warning']
                # Check for the specific missing prerequisite message
                if '⚠️ MISSING PREREQUISITE' in warning_msg:
                    warnings.append(warning_msg)
        
        # Display warnings prominently if any exist
        if warnings:
            f.write("\n> [!WARNING]\n")
            for warning in warnings:
                f.write(f"> {warning}\n")
            f.write("\n")
    
    def _write_top_issues_summary(self, f, tool_results: Dict[str, Any]) -> None:
        """Write top 3 critical issues summary."""
        issues = []
        
        # Collect all issues with severity
        if 'architecture' in tool_results:
            for issue in tool_results['architecture'].get('issues', []):
                issues.append({
                    'severity': issue.get('severity', 'info'),
                    'title': issue.get('title', 'Issue'),
                    'file': issue.get('file', ''),
                    'category': 'Architecture'
                })
        
        if 'secrets' in tool_results:
            secrets = tool_results['secrets'].get('secrets', [])
            if secrets:
                issues.append({
                    'severity': 'error',
                    'title': f"{len(secrets)} potential secrets detected",
                    'file': secrets[0].get('file', '') if secrets else '',
                    'category': 'Security'
                })
        
        if 'deadcode' in tool_results:
            dead_count = len(tool_results['deadcode'].get('dead_functions', []))
            if dead_count > 5:
                issues.append({
                    'severity': 'warning',
                    'title': f"{dead_count} unused functions detected",
                    'file': '',
                    'category': 'Dead Code'
                })
        
        if 'duplication' in tool_results:
            dup_count = tool_results['duplication'].get('total_duplicates', 0)
            if dup_count > 3:
                issues.append({
                    'severity': 'warning',
                    'title': f"{dup_count} code duplicates found",
                    'file': '',
                    'category': 'Duplication'
                })
        
        if 'efficiency' in tool_results:
            eff_issues = tool_results['efficiency'].get('issues', [])
            if eff_issues:
                issues.append({
                    'severity': 'warning',
                    'title': f"{len(eff_issues)} efficiency issues",
                    'file': eff_issues[0].get('file', '') if eff_issues else '',
                    'category': 'Efficiency'
                })
        
        # Sort by severity (error > warning > info)
        severity_order = {'error': 0, 'warning': 1, 'info': 2}
        issues.sort(key=lambda x: severity_order.get(x['severity'], 3))
        
        # Write top 3
        if issues:
            f.write("## 🚨 Top Critical Issues\n\n")
            for i, issue in enumerate(issues[:3], 1):
                icon = "🔴" if issue['severity'] == "error" else "🟡" if issue['severity'] == "warning" else "🔵"
                f.write(f"{i}. {icon} **{issue['title']}** ({issue['category']})\n")
                if issue['file']:
                    f.write(f"   - File: `{issue['file']}`\n")
            f.write("\n---\n\n")
    
    def _write_git_section(self, f, data: Dict[str, Any]) -> None:
        """Write git context section."""
        if not data.get('has_git', False):
            return
        
        f.write("## 📝 Recent Changes\n\n")
        
        if data.get('last_commit'):
            f.write(f"**Last Commit:** {data['last_commit']}\n\n")
        
        if data.get('diff_stat'):
            f.write("**Uncommitted Changes:**\n```\n")
            f.write(data['diff_stat'])
            f.write("\n```\n\n")
        else:
            f.write("✅ No uncommitted changes\n\n")
        
        f.write("---\n\n")
    
    def _write_structure_section(self, f, data: Dict[str, Any]) -> None:
        """Write structure analysis section."""
        f.write("## 📁 Structure\n\n")
        if 'tree' in data:
            f.write("```\n")
            f.write(data['tree'])
            f.write("\n```\n\n")
        
        if 'file_counts' in data:
            f.write("**File Statistics:**\n")
            for ext, count in sorted(data['file_counts'].items(), key=lambda x: -x[1]):
                f.write(f"- `{ext}`: {count} files\n")
        f.write("\n")
    
    def _write_architecture_section(self, f, data: Dict[str, Any]) -> None:
        """Write architecture analysis section."""
        issues = data.get('issues', [])
        
        if not issues:
            # Compact display for no issues
            f.write("## 🏗️ Architecture: ✅ No issues\n\n")
            return
        
        f.write(f"## 🏗️ Architecture Issues ({len(issues)})\n\n")
        
        for issue in issues:
            severity = issue.get('severity', 'info')
            icon = "🔴" if severity == "error" else "🟡" if severity == "warning" else "🔵"
            f.write(f"{icon} **{issue.get('title', 'Issue')}**\n")
            f.write(f"   - {issue.get('description', '')}\n")
            if 'file' in issue:
                f.write(f"   - File: `{issue['file']}`\n")
            f.write("\n")
    
    def _write_duplication_section(self, f, data: Dict[str, Any]) -> None:
        """Write code duplication section."""
        duplicates = data.get('duplicates', [])
        
        if not duplicates:
            f.write("## 🎭 Code Duplicates: ✅ No issues\n\n")
            return
        
        f.write(f"## 🎭 Code Duplicates ({len(duplicates)})\n\n")
        
        for dup in duplicates:
            similarity = dup.get('similarity', 0)
            f.write(f"- **{dup.get('function_name', 'Unknown')}** ")
            f.write(f"({similarity:.0f}% similar)\n")
            locations = dup.get('locations', [])
            for loc in locations:
                f.write(f"  - `{loc}`\n")
            f.write("\n")
    
    def _write_deadcode_section(self, f, data: Dict[str, Any]) -> None:
        """Write dead code section."""
        dead_functions = data.get('dead_functions', [])
        unused_imports = data.get('unused_imports', [])
        
        total = len(dead_functions) + len(unused_imports)
        
        if total == 0:
            f.write("## ☠️ Dead Code: ✅ No issues\n\n")
            return
        
        f.write(f"## ☠️ Dead Code ({total})\n\n")
        
        if dead_functions:
            f.write("**Unused Functions:**\n")
            for func in dead_functions[:10]:  # Limit to 10
                f.write(f"- `{func.get('file', '')}:{func.get('name', '')}()` - ")
                f.write(f"{func.get('references', 0)} references\n")
            if len(dead_functions) > 10:
                f.write(f"\n*...and {len(dead_functions) - 10} more*\n")
            f.write("\n")
        
        if unused_imports:
            f.write("**Unused Imports:**\n")
            for imp in unused_imports[:10]:
                f.write(f"- `{imp.get('file', '')}`: {imp.get('import', '')}\n")
            if len(unused_imports) > 10:
                f.write(f"\n*...and {len(unused_imports) - 10} more*\n")
            f.write("\n")
    
    def _write_efficiency_section(self, f, data: Dict[str, Any]) -> None:
        """Write efficiency issues section."""
        issues = data.get('issues', [])
        
        if not issues:
            f.write("## ⚡ Efficiency: ✅ No issues\n\n")
            return
        
        f.write(f"## ⚡ Efficiency Issues ({len(issues)})\n\n")
        
        for issue in issues:
            f.write(f"- **{issue.get('type', 'Issue')}** in `{issue.get('file', '')}:{issue.get('line', '')}`\n")
            f.write(f"  - {issue.get('description', '')}\n")
            f.write("\n")
    
    def _write_cleanup_section(self, f, data: Dict[str, Any]) -> None:
        """Write cleanup recommendations section."""
        total_size = data.get('total_size_mb', 0)
        items = data.get('items', [])
        
        f.write(f"## 🧹 Cleanup ({total_size:.1f}MB)\n\n")
        
        if items:
            for item in items:
                f.write(f"- `{item.get('path', '')}` ({item.get('size_mb', 0):.1f}MB)\n")
            f.write("\n")
        else:
            f.write("✅ No cleanup needed\n\n")
    
    def _write_secrets_section(self, f, data: Dict[str, Any]) -> None:
        """Write secrets detection section."""
        secrets = data.get('secrets', [])
        
        if not secrets:
            f.write("## 🔒 Secrets: ✅ No issues\n\n")
            return
        
        f.write(f"## 🔒 Secrets ({len(secrets)})\n\n")
        f.write("⚠️ **Potential secrets found:**\n")
        for secret in secrets:
            f.write(f"- `{secret.get('file', '')}:{secret.get('line', '')}` - ")
            f.write(f"{secret.get('type', 'Unknown')}\n")
        f.write("\n")
    
    def _write_tests_section(self, f, data: Dict[str, Any]) -> None:
        """Write tests analysis section."""
        coverage = data.get('coverage_percent', 0)
        has_unit = data.get('has_unit_tests', False)
        has_integration = data.get('has_integration_tests', False)
        has_e2e = data.get('has_e2e_tests', False)
        
        f.write(f"## ✅ Tests: {coverage}% coverage\n\n")
        
        f.write("**Test Types:**\n")
        f.write(f"- Unit: {'✅' if has_unit else '❌'}\n")
        f.write(f"- Integration: {'✅' if has_integration else '❌'}\n")
        f.write(f"- E2E: {'✅' if has_e2e else '❌'}\n\n")
        
        if 'test_files' in data:
            f.write(f"**Test Files:** {len(data['test_files'])}\n\n")
    
    def _write_gitignore_section(self, f, data: Dict[str, Any]) -> None:
        """Write gitignore recommendations section."""
        suggestions = data.get('suggestions', [])
        
        if not suggestions:
            f.write("## 📋 Gitignore: ✅ Complete\n\n")
            return
        
        f.write("## 📋 Gitignore Recommendations\n\n")
        f.write("```gitignore\n")
        f.write("\n".join(suggestions))
        f.write("\n```\n\n")
