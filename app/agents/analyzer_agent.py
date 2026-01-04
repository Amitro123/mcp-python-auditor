"""Main analyzer agent - Orchestrates all analysis tools."""
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import logging
import asyncio

from app.core.tool_registry import registry
from app.core.report_generator import ReportGenerator
from app.schemas import ToolResult, AuditResult

logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """Main agent that orchestrates project analysis."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.report_generator = ReportGenerator(reports_dir)
    
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
        
        # Generate meaningful report ID from project name and timestamp
        project_name = path.name
        # Sanitize: replace spaces and special chars with underscores
        sanitized_name = re.sub(r'[^\w\-]', '_', project_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_id = f"audit_{sanitized_name}_{timestamp}"
        
        logger.info(f"Starting analysis of {project_path} (report_id: {report_id})")
        
        # Pre-flight check: Count python files
        py_files_count = self._count_python_files(path)
        logger.info(f"Project contains {py_files_count} Python files")
        
        heavy_tools = {'complexity', 'deadcode', 'duplication'}
        skipped_tools = []
        
        # Get tools to run
        if specific_tools:
            tools_to_run = {name: registry.get_tool(name) for name in specific_tools}
            tools_to_run = {k: v for k, v in tools_to_run.items() if v is not None}
        else:
            tools_to_run = registry.get_enabled_tools()
            
        # Smart Skipping logic
        if py_files_count > 300:
            for tool_name in list(tools_to_run.keys()):
                if tool_name in heavy_tools:
                    logger.warning(f"Skipping heavy tool '{tool_name}' due to project size ({py_files_count} files)")
                    skipped_tools.append(tool_name)
                    del tools_to_run[tool_name]
        
        # Run tools in parallel
        tool_results = {}
        
        async def run_tool_safe(name, tool):
            logger.info(f"Running tool: {name}")
            tool_start = time.time()
            try:
                # Use asyncio.to_thread for blocking I/O (subprocess calls in tools)
                result_data = await asyncio.to_thread(tool.analyze, path)
                success = 'error' not in result_data
                errors = [result_data['error']] if 'error' in result_data else []
                
                return name, ToolResult(
                    tool_name=name,
                    success=success,
                    data=result_data,
                    errors=errors,
                    execution_time=time.time() - tool_start
                )
            except Exception as e:
                logger.error(f"Tool {name} failed: {e}")
                return name, ToolResult(
                    tool_name=name,
                    success=False,
                    errors=[str(e)],
                    execution_time=time.time() - tool_start
                )
        
        # Execute all tools concurrently
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
                
                report_path = self.report_generator.generate_report(
                    report_id=report_id,
                    project_path=project_path,
                    score=score,
                    tool_results=results_dict,
                    timestamp=datetime.now()
                )
                logger.info(f"Report generated: {report_path}")
            except Exception as e:
                logger.error(f"Failed to generate report: {e}")
        
        total_time = time.time() - start_time
        
        return AuditResult(
            report_id=report_id,
            project_path=project_path,
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
