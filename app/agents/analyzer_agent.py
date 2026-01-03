"""Main analyzer agent - Orchestrates all analysis tools."""
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

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
        report_id = str(uuid.uuid4())[:8]
        path = Path(project_path)
        
        logger.info(f"Starting analysis of {project_path} (report_id: {report_id})")
        
        # Get tools to run
        if specific_tools:
            tools = {name: registry.get_tool(name) for name in specific_tools}
            tools = {k: v for k, v in tools.items() if v is not None}
        else:
            tools = registry.get_enabled_tools()
        
        # Run each tool
        tool_results = {}
        for tool_name, tool in tools.items():
            logger.info(f"Running tool: {tool_name}")
            tool_start = time.time()
            
            try:
                result_data = tool.analyze(path)
                success = 'error' not in result_data
                errors = [result_data['error']] if 'error' in result_data else []
                
                tool_results[tool_name] = ToolResult(
                    tool_name=tool_name,
                    success=success,
                    data=result_data,
                    errors=errors,
                    execution_time=time.time() - tool_start
                )
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                tool_results[tool_name] = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    errors=[str(e)],
                    execution_time=time.time() - tool_start
                )
        
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
            summary=self._generate_summary(tool_results, score),
            total_execution_time=total_time
        )
    
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
    
    def _generate_summary(self, tool_results: Dict[str, ToolResult], score: int) -> str:
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
        
        return " ".join(summary_parts)
