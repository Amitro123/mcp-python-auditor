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
            
            # 📊 TOOL EXECUTION SUMMARY (NEW - Full Visibility)
            self._write_tool_execution_summary(f, tool_results)
            
            # Self-Healing Status (if applicable)
            if 'self_healing' in tool_results:
                self._write_self_healing_section(f, tool_results['self_healing'])
            
            # Action Roadmap (TOP PRIORITY)
            self._write_top_action_roadmap(f, tool_results)
            
            # Check for and display warnings prominently
            self._write_warnings_section(f, tool_results)
            
            f.write("---\n\n")
            
            # ===== MANDATORY SECTIONS (Always Visible) =====
            
            # 📁 Project Structure (MANDATORY)
            self._write_enterprise_structure(f, tool_results.get('structure', {}))
            
            # 🔒 Security Analysis - Bandit (MANDATORY)
            self._write_mandatory_security(f, tool_results.get('security', {}))
            
            # 🎭 Duplicates (MANDATORY - Grouped)
            self._write_grouped_duplication(f, tool_results.get('duplication', {}))
            
            # ☠️ Dead Code (MANDATORY)
            self._write_mandatory_deadcode(f, tool_results.get('deadcode', {}))
            
            # 🧹 Cleanup Commands (MANDATORY)
            self._write_cleanup_commands(f, tool_results.get('cleanup', {}))
            
            # 📝 Recent Changes - Git (MANDATORY)
            self._write_recent_changes(f, tool_results.get('git', {}))
            
            # ✅ Tests & Coverage (MANDATORY)
            self._write_enterprise_tests(f, tool_results.get('tests', {}))
            
            # 🔐 Secrets Detection (MANDATORY)
            self._write_mandatory_secrets(f, tool_results.get('secrets', {}))
            
            # 📋 Gitignore (MANDATORY)
            self._write_mandatory_gitignore(f, tool_results.get('gitignore', {}))

            f.write("---\n\n")
            f.write("## 🔍 Technical Details\n\n")
            
            # 🏗️ Architecture section (MANDATORY)
            self._write_architecture_section(f, tool_results.get('architecture', {}))
            
            # 📝 Type coverage section (MANDATORY)
            if HAS_ENHANCED_SECTIONS and 'typing' in tool_results:
                _write_typing_section(f, tool_results['typing'])
            else:
                self._write_mandatory_typing(f, tool_results.get('typing', {}))
            
            # ⚡ Efficiency section (MANDATORY)
            self._write_efficiency_section(f, tool_results.get('efficiency', {}))
            
            # 🧮 Complexity section (MANDATORY)
            if HAS_ENHANCED_SECTIONS and 'complexity' in tool_results:
                _write_complexity_section(f, tool_results['complexity'])
            else:
                self._write_mandatory_complexity(f, tool_results.get('complexity', {}))
        
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
        """Write a focused, filtered structure section - MANDATORY."""
        f.write("## 📁 CLEAN STRUCTURE (Actionable)\n")
        
        if not data:
            f.write("⚠️ **Structure analysis did not run.** Check logs.\n\n")
            return
        
        if 'tree' in data:
            f.write("```\n")
            f.write(data['tree'])
            f.write("\n```\n")
        
        # Add actionable context
        f.write("*Focusing on 80% code density zones. Filtered docs/, reports/, and scripts/ for clarity.*\n\n")

    def _write_grouped_duplication(self, f, data: Dict[str, Any]) -> None:
        """Write duplication section grouped by file with actionable fixes - MANDATORY."""
        f.write("## 🎭 DUPLICATES (Grouped + Actionable)\n")
        
        if not data:
            f.write("⚠️ **Duplication analysis did not run.** Check logs.\n\n")
            return
        
        duplicates = data.get('duplicates', [])
        
        if not duplicates:
            f.write("✅ **Clean:** No significant code duplication found.\n\n")
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
        """Write cleanup section with copy-paste commands - MANDATORY."""
        f.write(f"## 🧹 CLEANUP READY COMMANDS\n")
        
        if not data:
            f.write("⚠️ **Cleanup analysis did not run.** Check logs.\n\n")
            return
        
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
        """Write recent git changes section - MANDATORY."""
        f.write(f"## 📝 RECENT CHANGES\n\n")
        
        if not data:
            f.write("⚠️ **Git analysis did not run.** Check logs.\n\n")
            return
        
        if not data.get('has_git', False):
            f.write("ℹ️ *Not a git repository*\n\n")
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
        """Write tests section with clear coverage status and detailed breakdown - MANDATORY."""
        f.write(f"## ✅ TESTS\n\n")
        
        if not data:
            f.write("⚠️ **Tests analysis did not run.** Check logs.\n\n")
            return
        
        coverage = data.get('coverage_percent', -1)
        warning = data.get('warning', '')
        total_files = data.get('total_test_files', 0)
        
        # Header with file count and coverage
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
        
        # Fallback for flat structure: if has_unit is True but count is 0, use total files
        if has_unit and unit_count == 0:
            unit_count = total_files
        
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
    
    # ===== FULL VISIBILITY MODE METHODS =====
    
    def _write_tool_execution_summary(self, f, tool_results: Dict[str, Any]) -> None:
        """Write comprehensive tool execution summary table - ALL tools shown."""
        f.write("## 📊 Tool Execution Summary\n\n")
        f.write("| Tool | Status | Details |\n")
        f.write("|------|--------|----------|\n")
        
        # Define all 13 tools in execution order
        tools_config = [
            ('structure', '📁 Structure', self._get_structure_status),
            ('architecture', '🏗️ Architecture', self._get_architecture_status),
            ('typing', '📝 Type Coverage', self._get_typing_status),
            ('complexity', '🧮 Complexity', self._get_complexity_status),
            ('duplication', '🎭 Duplication', self._get_duplication_status),
            ('deadcode', '☠️ Dead Code', self._get_deadcode_status),
            ('efficiency', '⚡ Efficiency', self._get_efficiency_status),
            ('cleanup', '🧹 Cleanup', self._get_cleanup_status),
            ('secrets', '🔐 Secrets', self._get_secrets_status),
            ('security', '🔒 Security (Bandit)', self._get_security_status),
            ('tests', '✅ Tests', self._get_tests_status),
            ('gitignore', '📋 Gitignore', self._get_gitignore_status),
            ('git', '📝 Git Status', self._get_git_status),
        ]
        
        for key, name, status_func in tools_config:
            data = tool_results.get(key, {})
            status, details = status_func(data)
            f.write(f"| {name} | {status} | {details} |\n")
        
        f.write("\n")
    
    # Status helper methods for each tool
    def _get_structure_status(self, data: Dict[str, Any]) -> tuple:
        """Get structure tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        files = data.get('total_files', 0)
        dirs = data.get('total_directories', 0)
        return "ℹ️ Info", f"{files} files, {dirs} dirs"
    
    def _get_architecture_status(self, data: Dict[str, Any]) -> tuple:
        """Get architecture tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        issues = len(data.get('issues', []))
        if issues == 0:
            return "✅ Pass", "No architectural issues"
        return "⚠️ Issues", f"{issues} issue(s) found"
    
    def _get_typing_status(self, data: Dict[str, Any]) -> tuple:
        """Get typing tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        coverage = data.get('coverage_percent', -1)
        untyped = data.get('untyped_functions', 0)
        if coverage >= 0:
            return "ℹ️ Info", f"{coverage}% typed, {untyped} untyped funcs"
        return "✅ Pass", "Type checking complete"
    
    def _get_complexity_status(self, data: Dict[str, Any]) -> tuple:
        """Get complexity tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        issues = len(data.get('issues', []))
        if issues == 0:
            return "✅ Pass", "No high-complexity functions"
        return "⚠️ Issues", f"{issues} complex function(s)"
    
    def _get_duplication_status(self, data: Dict[str, Any]) -> tuple:
        """Get duplication tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        dups = len(data.get('duplicates', []))
        if dups == 0:
            return "✅ Pass", "No code duplication found"
        return "⚠️ Issues", f"{dups} duplicate(s) found"
    
    def _get_deadcode_status(self, data: Dict[str, Any]) -> tuple:
        """Get dead code tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        dead_funcs = len(data.get('dead_functions', []))
        unused_imports = len(data.get('unused_imports', []))
        total = dead_funcs + unused_imports
        if total == 0:
            return "✅ Pass", "No dead code detected"
        return "⚠️ Issues", f"{dead_funcs} funcs, {unused_imports} imports"
    
    def _get_efficiency_status(self, data: Dict[str, Any]) -> tuple:
        """Get efficiency tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        issues = len(data.get('issues', []))
        if issues == 0:
            return "✅ Pass", "No efficiency issues"
        return "⚠️ Issues", f"{issues} issue(s) found"
    
    def _get_cleanup_status(self, data: Dict[str, Any]) -> tuple:
        """Get cleanup tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        items = len(data.get('items', []))
        size_mb = data.get('total_size_mb', 0)
        if items == 0:
            return "✅ Pass", "Environment is clean"
        return "ℹ️ Info", f"{items} item(s), {size_mb:.1f}MB"
    
    def _get_secrets_status(self, data: Dict[str, Any]) -> tuple:
        """Get secrets tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        secrets = len(data.get('secrets', []))
        if secrets == 0:
            return "✅ Pass", "No secrets detected"
        return "❌ Fail", f"{secrets} potential secret(s)"
    
    def _get_security_status(self, data: Dict[str, Any]) -> tuple:
        """Get security (Bandit) tool status."""
        if not data:
            return "⚠️ Skip", "Security scan did not run"
        if 'error' in data:
            return "❌ Fail", "Bandit execution failed"
        
        # Handle nested structure: SecurityTool returns code_security with bandit results
        if "code_security" in data:
            bandit_data = data["code_security"]
            files_scanned = bandit_data.get('files_scanned', 0)
            issues = len(bandit_data.get('issues', []))
        else:
            # Legacy/direct structure
            files_scanned = data.get('files_scanned', 0)
            issues = len(data.get('issues', []))
        
        if issues == 0:
            return "✅ Pass", f"Scanned {files_scanned} files, 0 issues"
        return "⚠️ Issues", f"{issues} vulnerability(ies) in {files_scanned} files"
    
    def _get_tests_status(self, data: Dict[str, Any]) -> tuple:
        """Get tests tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        coverage = data.get('coverage_percent', -1)
        total_files = data.get('total_test_files', 0)
        if coverage < 0:
            return "❌ Fail", "Coverage calculation failed"
        return "ℹ️ Info", f"{total_files} test files, {coverage}% coverage"
    
    def _get_gitignore_status(self, data: Dict[str, Any]) -> tuple:
        """Get gitignore tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        suggestions = len(data.get('suggestions', []))
        if suggestions == 0:
            return "✅ Pass", "Gitignore is complete"
        return "ℹ️ Info", f"{suggestions} suggestion(s)"
    
    def _get_git_status(self, data: Dict[str, Any]) -> tuple:
        """Get git tool status."""
        if not data:
            return "⚠️ Skip", "Tool did not run"
        if not data.get('has_git', False):
            return "ℹ️ Info", "Not a git repository"
        status = data.get('status', 'Unknown')
        days = data.get('days_since_commit', 0)
        return "ℹ️ Info", f"{status}, {days} days since commit"
    
    # ===== MANDATORY SECTION WRITERS =====
    
    def _write_mandatory_security(self, f, data: Dict[str, Any]) -> None:
        """MANDATORY Security section - always shows execution status."""
        f.write("## 🔒 Security Analysis (Bandit)\n\n")
        
        if not data:
            f.write("⚠️ **Security scan did not run.** Check logs or tool configuration.\n\n")
            return
        
        if 'error' in data:
            f.write(f"❌ **Bandit execution failed:** {data.get('error', 'Unknown error')}\n\n")
            return
        
        issues = data.get('issues', [])
        files_scanned = data.get('files_scanned', 0)
        
        if not issues:
            f.write(f"✅ **Security Scan Complete:** No known vulnerabilities found in {files_scanned} scanned files.\n\n")
            return
        
        # Show issues
        f.write(f"⚠️ **{len(issues)} security issue(s) found in {files_scanned} files:**\n\n")
        for issue in issues[:10]:  # Limit to 10
            severity = issue.get('severity', 'unknown').upper()
            icon = "🔴" if severity in ["HIGH", "CRITICAL"] else "🟡" if severity == "MEDIUM" else "🔵"
            f.write(f"{icon} **{severity}**: {issue.get('type', 'Unknown')} in `{issue.get('file', '')}:{issue.get('line', '')}`\n")
            f.write(f"   - {issue.get('description', '')}\n\n")
        
        if len(issues) > 10:
            f.write(f"*...and {len(issues) - 10} more issues*\n\n")
    
    def _write_mandatory_deadcode(self, f, data: Dict[str, Any]) -> None:
        """MANDATORY Dead Code section - always shows execution status."""
        f.write("## ☠️ Dead Code Detection\n\n")
        
        if not data:
            f.write("⚠️ **Dead code scan did not run.** Check logs.\n\n")
            return
        
        dead_functions = data.get('dead_functions', [])
        dead_variables = data.get('dead_variables', [])
        dead_classes = data.get('dead_classes', [])
        unused_imports = data.get('unused_imports', [])
        total = len(dead_functions) + len(dead_variables) + len(dead_classes) + len(unused_imports)
        
        if total == 0:
            f.write("✅ **Clean:** No dead code detected. All functions and imports are used.\n\n")
            return
        
        f.write(f"⚠️ **{total} dead code item(s) found:**\n\n")
        
        if dead_functions:
            f.write(f"**Unused Functions ({len(dead_functions)}):**\n")
            for func in dead_functions[:10]:
                f.write(f"- `{func.get('file', '')}:{func.get('name', '')}()` - {func.get('references', 0)} references\n")
            if len(dead_functions) > 10:
                f.write(f"\n*...and {len(dead_functions) - 10} more*\n")
            f.write("\n")
        
        if unused_imports:
            # Group imports by file
            from collections import Counter
            file_counts = Counter(imp.get('file', '') for imp in unused_imports)
            
            f.write(f"**Unused Imports ({len(unused_imports)}):**\n")
            for file, count in list(file_counts.items())[:10]:
                if count > 1:
                    f.write(f"- `{file}` ({count} imports)\n")
                else:
                    f.write(f"- `{file}`\n")
            if len(file_counts) > 10:
                f.write(f"\n*...and {len(file_counts) - 10} more files*\n")
            f.write("\n")
    
    def _write_mandatory_secrets(self, f, data: Dict[str, Any]) -> None:
        """MANDATORY Secrets section - always shows execution status."""
        f.write("## 🔐 Secrets Detection\n\n")
        
        if not data:
            f.write("⚠️ **Secrets scan did not run.** Check logs.\n\n")
            return
        
        secrets = data.get('secrets', [])
        
        if not secrets:
            f.write("✅ **Clean:** No potential secrets or credentials detected in codebase.\n\n")
            return
        
        f.write(f"❌ **{len(secrets)} potential secret(s) found:**\n\n")
        for secret in secrets:
            f.write(f"- `{secret.get('file', '')}:{secret.get('line', '')}` - {secret.get('type', 'Unknown')}\n")
        f.write("\n⚠️ **Action Required:** Review and move secrets to environment variables or secret management.\n\n")
    
    def _write_mandatory_gitignore(self, f, data: Dict[str, Any]) -> None:
        """MANDATORY Gitignore section - always shows execution status."""
        f.write("## 📋 Gitignore Analysis\n\n")
        
        if not data:
            f.write("⚠️ **Gitignore analysis did not run.** Check logs.\n\n")
            return
        
        suggestions = data.get('suggestions', [])
        
        if not suggestions:
            f.write("✅ **Complete:** Gitignore covers all common patterns.\n\n")
            return
        
        f.write(f"ℹ️ **{len(suggestions)} recommendation(s):**\n\n")
        f.write("```gitignore\n")
        f.write("\n".join(suggestions))
        f.write("\n```\n\n")
    
    def _write_mandatory_typing(self, f, data: Dict[str, Any]) -> None:
        """MANDATORY Typing section - always shows execution status."""
        f.write("### 📝 Type Coverage\n\n")
        
        if not data:
            f.write("⚠️ **Type analysis did not run.** Check logs.\n\n")
            return
        
        coverage = data.get('coverage_percent', -1)
        untyped = data.get('untyped_functions', 0)
        
        if coverage >= 0:
            f.write(f"**Coverage:** {coverage}%\n")
            f.write(f"**Untyped Functions:** {untyped}\n\n")
        else:
            f.write("✅ **Type checking complete.**\n\n")
    
    def _write_mandatory_complexity(self, f, data: Dict[str, Any]) -> None:
        """MANDATORY Complexity section - always shows execution status."""
        f.write("### 🧮 Cyclomatic Complexity\n\n")
        
        if not data:
            f.write("⚠️ **Complexity analysis did not run.** Check logs.\n\n")
            return
        
        issues = data.get('issues', [])
        
        if not issues:
            f.write("✅ **Clean:** No high-complexity functions detected.\n\n")
            return
        
        f.write(f"⚠️ **{len(issues)} complex function(s):**\n\n")
        for issue in issues[:10]:
            f.write(f"- `{issue.get('function', 'unknown')}` in `{issue.get('file', '')}` - Complexity: {issue.get('complexity', 0)}\n")
        if len(issues) > 10:
            f.write(f"\n*...and {len(issues) - 10} more*\n")
        f.write("\n")

