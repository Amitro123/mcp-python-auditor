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
            f.write("---\n\n")
            
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
        f.write(f"## 🏗️ Architecture Issues ({len(issues)})\n\n")
        
        if not issues:
            f.write("✅ No architecture issues detected\n\n")
        else:
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
        f.write(f"## 🎭 Code Duplicates ({len(duplicates)})\n\n")
        
        if not duplicates:
            f.write("✅ No significant code duplication detected\n\n")
        else:
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
        
        if not dead_functions and not unused_imports:
            f.write("✅ No dead code detected\n\n")
    
    def _write_efficiency_section(self, f, data: Dict[str, Any]) -> None:
        """Write efficiency issues section."""
        issues = data.get('issues', [])
        f.write(f"## ⚡ Efficiency Issues ({len(issues)})\n\n")
        
        if not issues:
            f.write("✅ No efficiency issues detected\n\n")
        else:
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
        f.write(f"## 🔒 Secrets ({len(secrets)})\n\n")
        
        if not secrets:
            f.write("✅ No secrets detected\n\n")
        else:
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
        f.write("## 📋 Gitignore Recommendations\n\n")
        
        if 'suggestions' in data and data['suggestions']:
            f.write("```gitignore\n")
            f.write("\n".join(data['suggestions']))
            f.write("\n```\n\n")
        else:
            f.write("✅ Gitignore appears complete\n\n")
