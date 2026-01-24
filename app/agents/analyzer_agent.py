"""Main analyzer agent - Orchestrates all analysis tools."""
import time
import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime
import logging
import asyncio

from app.core.tool_registry import registry
from app.core.report_generator_v2 import ReportGeneratorV2 as ReportGenerator
from app.core.self_healing import SelfHealingAnalyzer
from app.core.file_discovery import get_project_files
from app.core.audit_validator import validate_report_integrity
from app.schemas import ToolResult, AuditResult

logger = logging.getLogger(__name__)

# Performance configuration
MAX_CONCURRENT_TOOLS = 3  # Semaphore limit
MAX_TOOL_TIMEOUT = 120  # seconds per tool (increased for bandit)
MAX_PY_FILES_HEAVY = 200  # Skip heavy tools above this
MAX_SIZE_MB_HEAVY = 100  # Skip heavy tools above this size


class AnalyzerAgent:
    """Main agent that orchestrates project analysis."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.report_generator = ReportGenerator(reports_dir)
        self.self_healing = SelfHealingAnalyzer()
    
    async def analyze_project(
        self,
        project_path: str,
        dry_run: bool = False,
        specific_tools: Optional[List[str]] = None
    ) -> AuditResult:
        """
        Perform comprehensive project analysis.
        
        Args:
            project_path: Path to the project directory
            dry_run: If True, only analyze without generating report
            specific_tools: List of specific tools to run (None = all)
            
        Returns:
            AuditResult with analysis results
        """
        start_time = time.time()
        path = Path(project_path)
        
        # 🎯 SMART ROOT DETECTION (NEW)
        original_path = path
        path = self._resolve_project_root(path)
        
        if path != original_path:
            logger.info(f"⚠️ Detected project root at '{path.relative_to(original_path.parent)}'. Switching context...")
        
        # Generate meaningful report ID from project name and timestamp
        project_name = path.name
        # Sanitize: replace spaces and special chars with underscores
        sanitized_name = re.sub(r'[^\w\-]', '_', project_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_id = f"audit_{sanitized_name}_{timestamp}"
        
        logger.info(f"Starting analysis of {path} (report_id: {report_id})")
        
        # 🔍 GIT-NATIVE FILE DISCOVERY (NEW)
        logger.info("Discovering project files using Git-native method...")
        scanned_files = get_project_files(path)
        logger.info(f"✅ Discovered {len(scanned_files)} Python files for analysis")
        
        # Calculate project stats (py_files + size)
        project_stats = self._calculate_project_stats(path)
        py_files_count = project_stats['py_files']
        size_mb = project_stats['size_mb']
        logger.info(f"Project stats: {py_files_count} Python files, {size_mb:.1f}MB total")
        
        # Self-healing preflight check
        dep_status = self.self_healing.check_dependencies()
        pytest_health = self.self_healing.check_pytest_health(path)
        
        if dep_status['missing']:
            logger.warning(f"Missing dependencies: {[d['name'] for d in dep_status['missing']]}")
            fix_cmd = self.self_healing.get_auto_fix_command()
            if fix_cmd:
                logger.warning(f"Auto-fix command: {fix_cmd}")
        
        heavy_tools = {'complexity', 'deadcode', 'duplication'}  # Security MUST always run
        skipped_tools = []
        
        # Define tools that support explicit file lists
        file_list_tools = {'security', 'complexity', 'duplication', 'deadcode'}
        
        # Get tools to run
        if specific_tools:
            tools_to_run = {name: registry.get_tool(name) for name in specific_tools}
            tools_to_run = {k: v for k, v in tools_to_run.items() if v is not None}
        else:
            tools_to_run = registry.get_enabled_tools()
            
        # Smart Skipping logic: Skip heavy tools for large projects
        for tool_name in list(tools_to_run.keys()):
            if self._should_skip_heavy_tool(tool_name, project_stats, heavy_tools):
                reason = f"project size ({py_files_count} files, {size_mb:.1f}MB)"
                logger.warning(f"Skipping heavy tool '{tool_name}' due to {reason}")
                skipped_tools.append(tool_name)
                del tools_to_run[tool_name]
        
        # Run tools with controlled concurrency (Semaphore)
        tool_results = {}
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_TOOLS)
        
        async def run_tool_safe(name, tool):
            """Run tool with semaphore, timeout, and error handling."""
            async with semaphore:  # Limit concurrent execution
                logger.info(f"Running tool: {name}")
                tool_start = time.time()
                try:
                    # Use asyncio.to_thread for blocking I/O with timeout
                    # Pass file_list to tools that support it
                    if name in file_list_tools:
                        result_data = await asyncio.wait_for(
                            asyncio.to_thread(tool.analyze, path, scanned_files),
                            timeout=MAX_TOOL_TIMEOUT
                        )
                    else:
                        result_data = await asyncio.wait_for(
                            asyncio.to_thread(tool.analyze, path),
                            timeout=MAX_TOOL_TIMEOUT
                        )
                    success = 'error' not in result_data
                    errors = [result_data['error']] if 'error' in result_data else []
                    
                    return name, ToolResult(
                        tool_name=name,
                        success=success,
                        data=result_data,
                        errors=errors,
                        execution_time=time.time() - tool_start
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Tool {name} timed out after {MAX_TOOL_TIMEOUT}s")
                    return name, ToolResult(
                        tool_name=name,
                        success=False,
                        data={'skipped': True, 'reason': f'timeout ({MAX_TOOL_TIMEOUT}s)'},
                        errors=[f"Tool timed out after {MAX_TOOL_TIMEOUT}s"],
                        warnings=[f"Skipped: timeout ({MAX_TOOL_TIMEOUT}s)"],
                        execution_time=MAX_TOOL_TIMEOUT
                    )
                except Exception as e:
                    logger.error(f"Tool {name} failed: {e}")
                    return name, ToolResult(
                        tool_name=name,
                        success=False,
                        errors=[str(e)],
                        execution_time=time.time() - tool_start
                    )
        
        # Execute all tools concurrently with semaphore control
        tasks = [run_tool_safe(name, tool) for name, tool in tools_to_run.items()]
        if tasks:
            results = await asyncio.gather(*tasks)
            tool_results = {name: result for name, result in results}
        
        # Calculate score
        score = self._calculate_score(tool_results)
        
        # Generate report if not dry run
        report_path = None
        if not dry_run:
            try:
                # Convert ToolResult to dict for report generator
                results_dict = {
                    name: result.data
                    for name, result in tool_results.items()
                    if result.success
                }
                
                # Add self-healing data
                results_dict['self_healing'] = {
                    'dependencies': dep_status,
                    'pytest_health': pytest_health,
                    'healing_log': self.self_healing.healing_log,
                    'one_command_fix': self.self_healing.get_one_command_fix()
                }
                
                report_path = self.report_generator.generate_report(
                    report_id=report_id,
                    project_path=str(path),  # Use resolved path
                    score=score,
                    tool_results=results_dict,
                    timestamp=datetime.now(),
                    scanned_files=scanned_files  # Pass file list for validation
                )
                logger.info(f"Report generated: {report_path}")

                # Try to generate HTML report as well (optional)
                try:
                    html_path = self.report_generator.generate_html_report(
                        report_id=report_id,
                        project_path=str(path),
                        score=score,
                        tool_results=results_dict,
                        timestamp=datetime.now(),
                        scanned_files=scanned_files,
                        md_report_path=report_path
                    )
                    logger.info(f"HTML Report generated: {html_path}")
                except Exception as e:
                    logger.warning(f"HTML report generation skipped: {e}")

            except Exception as e:
                logger.error(f"Failed to generate report: {e}")
        
        total_time = time.time() - start_time
        
        return AuditResult(
            report_id=report_id,
            project_path=str(path),  # Use resolved path, not original
            score=score,
            tool_results=tool_results,
            report_path=report_path,
            summary=self._generate_summary(tool_results, score, skipped_tools),
            total_execution_time=total_time
        )
    
    def _count_python_files(self, project_path: Path) -> int:
        """Count Python files in project, excluding common non-source directories."""
        exclude_dirs = {'.venv', 'node_modules', 'tests', '__pycache__', '.git', '.pytest_cache'}
        count = 0
        try:
            for p in project_path.rglob('*.py'):
                # Check if any part of the path is in exclude_dirs
                if not any(excluded in p.parts for excluded in exclude_dirs):
                    count += 1
        except Exception as e:
            logger.error(f"Error counting python files: {e}")
        return count
    
    def _calculate_score(self, tool_results: Dict[str, ToolResult]) -> int:
        """
        Calculate overall project score (0-100).
        
        Scoring criteria:
        - Architecture: 20 points
        - Tests: 20 points
        - Dead code: 15 points
        - Duplicates: 15 points
        - Efficiency: 10 points
        - Secrets: 10 points
        - Cleanup: 5 points
        - Structure: 5 points
        """
        score = 100
        
        # Architecture issues
        if 'architecture' in tool_results and tool_results['architecture'].success:
            data = tool_results['architecture'].data
            issues = data.get('total_issues', 0)
            severity_counts = data.get('severity_counts', {})
            
            # Deduct based on severity
            score -= severity_counts.get('error', 0) * 5
            score -= severity_counts.get('warning', 0) * 2
            score -= severity_counts.get('info', 0) * 1
        
        # Tests
        if 'tests' in tool_results and tool_results['tests'].success:
            data = tool_results['tests'].data
            coverage = data.get('coverage_percent', 0)
            
            # Score based on coverage (max 20 points)
            test_score = (coverage / 100) * 20
            
            # Bonus for having different test types
            if data.get('has_unit_tests'):
                test_score += 5
            if data.get('has_integration_tests'):
                test_score += 3
            if data.get('has_e2e_tests'):
                test_score += 2
            
            score = score - 20 + min(test_score, 20)
        else:
            score -= 20  # No tests = -20
        
        # Dead code
        if 'deadcode' in tool_results and tool_results['deadcode'].success:
            data = tool_results['deadcode'].data
            dead_count = data.get('total_dead', 0)
            
            # Deduct based on amount of dead code
            score -= min(dead_count, 15)
        
        # Duplicates
        if 'duplication' in tool_results and tool_results['duplication'].success:
            data = tool_results['duplication'].data
            dup_count = data.get('total_duplicates', 0)
            
            # Deduct based on duplicates
            score -= min(dup_count * 2, 15)
        
        # Efficiency
        if 'efficiency' in tool_results and tool_results['efficiency'].success:
            data = tool_results['efficiency'].data
            issues = data.get('total_issues', 0)
            
            score -= min(issues, 10)
        
        # Secrets
        if 'secrets' in tool_results and tool_results['secrets'].success:
            data = tool_results['secrets'].data
            secrets_count = data.get('total_secrets', 0)
            
            if secrets_count > 0:
                score -= 10  # Any secrets = -10
        
        # Cleanup
        if 'cleanup' in tool_results and tool_results['cleanup'].success:
            data = tool_results['cleanup'].data
            size_mb = data.get('total_size_mb', 0)
            
            # Deduct if cleanup size is large
            if size_mb > 100:
                score -= 5
            elif size_mb > 50:
                score -= 3
        
        return max(0, min(100, score))
    
    def _generate_summary(
        self, 
        tool_results: Dict[str, ToolResult], 
        score: int,
        skipped_tools: Optional[List[str]] = None
    ) -> str:
        """Generate a brief summary of the analysis."""
        successful_tools = sum(1 for r in tool_results.values() if r.success)
        total_tools = len(tool_results)
        
        summary_parts = [
            f"Analysis complete: {successful_tools}/{total_tools} tools succeeded.",
            f"Overall score: {score}/100."
        ]
        
        # Add key findings
        if 'secrets' in tool_results and tool_results['secrets'].success:
            secrets_count = tool_results['secrets'].data.get('total_secrets', 0)
            if secrets_count > 0:
                summary_parts.append(f"⚠️ {secrets_count} potential secrets detected!")
        
        if 'tests' in tool_results and tool_results['tests'].success:
            coverage = tool_results['tests'].data.get('coverage_percent', 0)
            summary_parts.append(f"Test coverage: {coverage}%")
        
        # Add skipping info
        if skipped_tools:
            tools_str = ", ".join(skipped_tools)
            summary_parts.append(f"⚠️ Heavy tools skipped due to project size: {tools_str}.")
        
        return " ".join(summary_parts)
    
    def _calculate_project_stats(self, path: Path) -> Dict[str, Any]:
        """
        Calculate project statistics (file count and size).
        
        Returns:
            Dict with 'py_files' (int) and 'size_mb' (float)
        """
        py_files = 0
        total_size = 0
        
        # 🛡️ SAFETY FILTER: Ignore Antigravity/System folders (HARDCODED)
        SYSTEM_FOLDERS = {
            '.gemini',
            'antigravity',
            'brain',
            'conversations',
            'scratch',  # Will be allowed if it's the actual project root
            '.vscode',
            '.idea',
            'node_modules',
            '.venv',
            'venv',
            '__pycache__',
            '.git',
            '.pytest_cache',
            'browser_recordings',
            'code_tracker',
            'context_state',
            'implicit',
            'playground'
        }
        
        try:
            for item in path.rglob('*'):
                # Skip system/wrapper directories
                if any(excluded in item.parts for excluded in SYSTEM_FOLDERS):
                    # BUT: Allow 'scratch' if it's the actual project root
                    if 'scratch' in item.parts:
                        # Check if 'scratch' is exactly the path we're scanning
                        if path.name != 'scratch':
                            continue
                    else:
                        continue
                
                if item.is_file():
                    # Count Python files
                    if item.suffix == '.py':
                        py_files += 1
                    
                    # Calculate total size
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        pass
        except Exception as e:
            logger.warning(f"Error calculating project stats: {e}")
        
        size_mb = total_size / (1024 * 1024)  # Convert to MB
        
        return {
            'py_files': py_files,
            'size_mb': size_mb
        }
    
    def _should_skip_heavy_tool(
        self, 
        tool_name: str, 
        project_stats: Dict[str, Any],
        heavy_tools: Set[str]
    ) -> bool:
        """
        Determine if a heavy tool should be skipped based on project size.
        
        Args:
            tool_name: Name of the tool
            project_stats: Dict with 'py_files' and 'size_mb'
            heavy_tools: Set of tool names considered heavy
            
        Returns:
            True if tool should be skipped
        """
        if tool_name not in heavy_tools:
            return False
        
        py_files = project_stats.get('py_files', 0)
        size_mb = project_stats.get('size_mb', 0)
        
        # Skip if exceeds either threshold
        return py_files > MAX_PY_FILES_HEAVY or size_mb > MAX_SIZE_MB_HEAVY
    
    def _resolve_project_root(self, path: Path) -> Path:
        """
        Smart Root Detection: Auto-detect actual project directory.
        
        If the given path doesn't contain project markers (pyproject.toml, 
        requirements.txt, .git), check immediate subdirectories for these markers.
        
        Args:
            path: The initial path provided by the user
            
        Returns:
            Resolved project root path (may be a subdirectory)
        """
        # Project markers (in order of preference)
        PROJECT_MARKERS = [
            'pyproject.toml',
            'setup.py',
            'requirements.txt',
            '.git',
            'Cargo.toml',  # Rust
            'package.json',  # JavaScript/TypeScript
        ]
        
        # Check if current path has project markers
        def has_project_markers(p: Path) -> bool:
            """Check if path contains any project markers."""
            for marker in PROJECT_MARKERS:
                if (p / marker).exists():
                    return True
            return False
        
        # If current path has markers, use it
        if has_project_markers(path):
            logger.info(f"✅ Project markers found in '{path.name}'")
            return path
        
        # Otherwise, check immediate subdirectories
        logger.info(f"⚠️ No project markers in '{path}'. Scanning subdirectories...")
        
        try:
            subdirs = [d for d in path.iterdir() if d.is_dir() and not d.name.startswith('.')]
            
            for subdir in subdirs:
                if has_project_markers(subdir):
                    logger.info(f"✅ Found project root: '{subdir.name}'")
                    return subdir
            
            # If no subdirectories have markers, return original path
            logger.warning(
                f"⚠️ No project markers found in '{path}' or subdirectories. "
                f"Proceeding with original path."
            )
            return path
            
        except (PermissionError, OSError) as e:
            logger.warning(f"Error scanning subdirectories: {e}. Using original path.")
            return path

