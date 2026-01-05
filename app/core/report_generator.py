"""Markdown report generator for audit results."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
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
        """Generate an Enterprise-grade actionable markdown report."""
        report_path = self.reports_dir / f"{report_id}.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            # Enterprise Header
            f.write(f"# Project Audit: {Path(project_path).name}\n")
            f.write(f"**Score:** {score}/100 → **Target: 90/100** (via 3 fixes)\n\n")
            
            # Self-Healing Status (if applicable)
            if 'self_healing' in tool_results:
                self._write_self_healing_section(f, tool_results['self_healing'])
            
            # Action Roadmap (TOP PRIORITY)
            self._write_top_action_roadmap(f, tool_results)
            
            # Check for and display warnings prominently
            self._write_warnings_section(f, tool_results)
            
            f.write("---\n\n")
            
            # Focused Structure
            if 'structure' in tool_results:
                self._write_enterprise_structure(f, tool_results['structure'])
            
            # Duplicates (Grouped)
            if 'duplication' in tool_results:
                self._write_grouped_duplication(f, tool_results['duplication'])
            
            # Cleanup Commands
            if 'cleanup' in tool_results:
                self._write_cleanup_commands(f, tool_results['cleanup'])
            
            # Recent Changes (Git)
            if 'git' in tool_results:
                self._write_recent_changes(f, tool_results['git'])
            
            # Tests & Coverage
            if 'tests' in tool_results:
                self._write_enterprise_tests(f, tool_results['tests'])
            
            # Security (CRITICAL - Always show)
            if 'security' in tool_results:
                if HAS_ENHANCED_SECTIONS:
                    _write_security_section(f, tool_results['security'])

            f.write("---\n\n")
            f.write("## 🔍 Technical Details\n\n")
            
            # Architecture section
            if 'architecture' in tool_results:
                self._write_architecture_section(f, tool_results['architecture'])
            
            # Type coverage section
            if 'typing' in tool_results:
                if HAS_ENHANCED_SECTIONS:
                    _write_typing_section(f, tool_results['typing'])
            
            # Efficiency section
            if 'efficiency' in tool_results:
                self._write_efficiency_section(f, tool_results['efficiency'])
            
            # Security section
            if 'security' in tool_results:
                if HAS_ENHANCED_SECTIONS:
                    _write_security_section(f, tool_results['security'])
        
        logger.info(f"Enterprise Report generated: {report_path}")
        return str(report_path)

    def _write_top_action_roadmap(self, f, tool_results: Dict[str, Any]) -> None:
        """Write Top 3 Priority Fixes with point estimates."""
        f.write("## 🚨 TOP 3 PRIORITY FIXES\n\n")
        
        fixes = []
        
        # 1. Architecture Fix Estimate
        if 'architecture' in tool_results:
            arch_data = tool_results['architecture']
            issues = arch_data.get('issues', [])
            if any('routers/' in str(i.get('description', '')) for i in issues):
                fixes.append({
                    'title': "Architecture: Create routers/models/",
                    'impact': 15,
                    'desc': "Centralize endpoints and Pydantic models to improve modularity."
                })

        # 2. Typing Fix Estimate
        if 'typing' in tool_results:
            untyped = tool_results['typing'].get('untyped_functions', 0)
            if untyped > 100:
                fixes.append({
                    'title': f"Types: {untyped} untyped funcs",
                    'impact': 12,
                    'desc': "Add type hints to core logic to prevent runtime errors."
                })

        # 3. Duplication Fix Estimate
        if 'duplication' in tool_results:
            dups = tool_results['duplication'].get('duplicates', [])
            if dups:
                # Find file with most duplicates
                file_stats = defaultdict(int)
                for d in dups:
                    for loc in d.get('locations', []):
                        file_stats[loc.split(':')[0]] += 1
                
                if file_stats:
                    top_file = max(file_stats.items(), key=lambda x: x[1])
                    fixes.append({
                        'title': f"Duplicates: Cleanup {top_file[0]}",
                        'impact': 8,
                        'desc': f"Extract factory methods for {top_file[1]} redundant segments."
                    })

        # Display Top 3
        for i, fix in enumerate(fixes[:3], 1):
            f.write(f"├── **{i}. {fix['title']}** (+{fix['impact']} points)\n")
            f.write(f"│   └── {fix['desc']}\n")
        
        if not fixes:
            f.write("✅ No critical fixes identified. Maintain current standards!\n")
        
        f.write("\n")

    def _write_enterprise_structure(self, f, data: Dict[str, Any]) -> None:
        """Write a focused, filtered structure section."""
        f.write("## 📁 CLEAN STRUCTURE (Actionable)\n")
        if 'tree' in data:
            f.write("```\n")
            f.write(data['tree'])
            f.write("\n```\n")
        
        # Add actionable context
        f.write("*Focusing on 80% code density zones. Filtered docs/, reports/, and scripts/ for clarity.*\n\n")

    def _write_grouped_duplication(self, f, data: Dict[str, Any]) -> None:
        """Write duplication section grouped by file with actionable fixes."""
        f.write("## 🎭 DUPLICATES (Grouped + Actionable)\n")
        duplicates = data.get('duplicates', [])
        
        if not duplicates:
            f.write("✅ No significant duplication found.\n\n")
            return

        # Group by file
        file_groups = defaultdict(list)
        for dup in duplicates:
            primary_file = dup.get('locations', ['Unknown'])[0].split(':')[0]
            file_groups[primary_file].append(dup)

        # Sort files by duplicate count
        sorted_files = sorted(file_groups.items(), key=lambda x: -len(x[1]))

        for file_path, dups in sorted_files[:5]: # Top 5 files
            dup_count = len(dups)
            f.write(f"- **{file_path}** → {dup_count} funcs (heavy redundancy)\n")
            
            # Generate fix suggestion based on file type
            if 'test_' in file_path:
                f.write(f"  👉 **Fix:** Extract `test_event_factory()` or common test helpers\n")
            else:
                f.write(f"  👉 **Fix:** Extract common helper or factory methods\n")
            
            # Show top 2 examples
            for dup in dups[:2]:
                func_name = dup.get('function_name', 'unknown')
                similarity = dup.get('similarity', 0)
                f.write(f"  - `{func_name}` ({similarity:.0f}% match)\n")
        
        if len(sorted_files) > 5:
            f.write(f"\n*...and {len(sorted_files) - 5} other files*\n")
        f.write("\n")

    def _write_cleanup_commands(self, f, data: Dict[str, Any]) -> None:
        """Write cleanup section with copy-paste commands."""
        f.write(f"## 🧹 CLEANUP READY COMMANDS\n")
        items = data.get('items', [])
        total_size = data.get('total_size_mb', 0)
        
        if not items:
            f.write("✅ Environment is clean.\n\n")
            return

        f.write("```bash\n")
        for item in items:
            command = item.get('command', f"rm -rf {item.get('type')}")
            item_type = item.get('type', 'unknown')
            size_mb = item.get('size_mb', 0)
            f.write(f"{command}  # {item_type}: {size_mb:.1f}MB\n")
        f.write("```\n")
        f.write(f"**Total: {total_size:.1f}MB → 0MB**\n")
        
        # Show example paths
        f.write("\n**Example Paths:**\n")
        for item in items[:3]:  # Top 3
            locations = item.get('locations', '')
            if locations:
                f.write(f"- {item.get('type')}: {locations}\n")
        f.write("\n")
    
    def _write_recent_changes(self, f, data: Dict[str, Any]) -> None:
        """Write recent git changes section."""
        f.write(f"## 📝 RECENT CHANGES\n\n")
        
        if not data.get('has_git', False):
            f.write("*Not a git repository*\n\n")
            return
        
        # Last commit info
        commit_hash = data.get('commit_hash', '')
        commit_author = data.get('commit_author', '')
        commit_date = data.get('commit_date', '')
        last_commit = data.get('last_commit', '')
        
        if last_commit:
            f.write(f"**Last Commit:** `{commit_hash}` - {commit_author}, {commit_date}\n")
            # Extract message from last_commit if available
            if ' : ' in last_commit:
                message = last_commit.split(' : ', 1)[1]
                f.write(f"*\"{message}\"*\n\n")
            else:
                f.write("\n")
        
        # Status
        status = data.get('status', 'Unknown')
        status_icon = "✅" if status == "Clean" else "⚠️"
        f.write(f"**Status:** {status_icon} {status}\n")
        
        # Days since commit
        days_since = data.get('days_since_commit', 0)
        if days_since > 0:
            f.write(f"**Days Since Commit:** {days_since} days\n")
        
        # Branch
        branch = data.get('branch', 'unknown')
        f.write(f"**Branch:** {branch}\n\n")
    
    def _write_self_healing_section(self, f, data: Dict[str, Any]) -> None:
        """Write self-healing status and recommendations."""
        dep_status = data.get('dependencies', {})
        pytest_health = data.get('pytest_health', {})
        healing_log = data.get('healing_log', [])
        one_command_fix = data.get('one_command_fix')
        
        # Only show if there are issues or fixes
        if not dep_status.get('missing') and not healing_log and not one_command_fix:
            return
        
        f.write("## 🔧 SELF-HEALING STATUS\n\n")
        
        # Dependency health
        health_score = dep_status.get('health_score', 100)
        if health_score < 100:
            missing = dep_status.get('missing', [])
            f.write(f"**Dependency Health:** {health_score:.0f}%\n")
            f.write(f"**Missing:** {', '.join([d['name'] for d in missing])}\n\n")
            
            if one_command_fix:
                f.write(f"👉 **One-Command Fix:**\n")
                f.write(f"```bash\n{one_command_fix}\n```\n\n")
        
        # Pytest health
        if not pytest_health.get('healthy', True):
            issues = pytest_health.get('issues', [])
            fixes = pytest_health.get('fixes', [])
            f.write(f"**Pytest Issues:** {len(issues)}\n")
            for issue, fix in zip(issues, fixes):
                f.write(f"- {issue} → `{fix}`\n")
            f.write("\n")
        
        # Healing log
        if healing_log:
            f.write("**Healing Actions:**\n")
            for log in healing_log:
                f.write(f"- {log}\n")
            f.write("\n")

    def _write_enterprise_tests(self, f, data: Dict[str, Any]) -> None:
        """Write tests section with clear coverage status and detailed breakdown."""
        coverage = data.get('coverage_percent', -1)
        warning = data.get('warning', '')
        total_files = data.get('total_test_files', 0)
        
        # Header with file count and coverage
        f.write(f"## ✅ TESTS\n\n")
        f.write(f"**Files Found:** {total_files} (glob test_*.py, *_test.py)\n")
        
        # Coverage status
        if coverage <= 0 or "Config missing" in warning:
            f.write(f"**Coverage:** Config missing\n")
            f.write(f"👉 **Fix:** `pytest --cov=src --cov-report=term-missing`\n\n")
        else:
            f.write(f"**Coverage:** {coverage}% \n\n")
        
        # Detailed test type breakdown
        has_unit = data.get('has_unit_tests', False)
        has_integration = data.get('has_integration_tests', False)
        has_e2e = data.get('has_e2e_tests', False)
        
        # Count files by type
        test_files = data.get('test_files', [])
        unit_count = sum(1 for f in test_files if 'unit' in f.lower())
        integration_count = sum(1 for f in test_files if 'integration' in f.lower())
        e2e_count = sum(1 for f in test_files if 'e2e' in f.lower() or 'test_e2e' in f.lower())
        
        f.write("**Test Types:**\n")
        f.write(f"- Unit: {'✅' if has_unit else '❌'} ({unit_count} files)\n")
        f.write(f"- Integration: {'✅' if has_integration else '❌'} ({integration_count} files)\n")
        f.write(f"- E2E: {'✅' if has_e2e else '❌'} ({e2e_count} files)\n")
        f.write(f"\n*Note: {total_files} test files found via glob. Run `pytest --collect-only` to see executable tests.*\n\n")
    
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
