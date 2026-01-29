"""
Audit Orchestrator - Simplified Synchronous Implementation.
"""
import time
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from app.core.tool_registry import ToolRegistry
from app.core.scoring_engine import ScoringEngine
from app.core.report_generator_v2 import ReportGeneratorV2

logger = logging.getLogger(__name__)

class AuditOrchestrator:
    """Synchronous orchestrator for emergency simplification."""

    def __init__(self, project_path: Path, reports_dir: Path):
        self.project_path = Path(project_path).resolve()
        self.reports_dir = reports_dir

    def run_audit(self) -> Dict[str, Any]:
        """Run all enabled tools synchronously."""
        tools = ToolRegistry.discover_tools()
        results = {}
        
        logger.info(f"Starting synchronous audit for {self.project_path}")
        
        for tool in tools:
            try:
                logger.info(f"Running {tool.name}...")
                start = time.time()
                result = tool.analyze(self.project_path)
                duration = time.time() - start
                
                # Tag result with duration
                result['duration_seconds'] = duration
                
                logger.info(f"{tool.name} completed in {duration:.2f}s")
                results[tool.name] = result
            except Exception as e:
                logger.error(f"{tool.name} failed: {e}")
                results[tool.name] = {'status': 'error', 'error': str(e)}
        
        # Calculate score
        score_data = ScoringEngine.calculate_score(results)
        
        # Generate Report
        try:
             # Basic report generator usage
             report_gen = ReportGeneratorV2(self.reports_dir)
             report_path = report_gen.generate_report(
                 report_id="sync_audit", # Simple ID
                 project_path=str(self.project_path),
                 score=score_data['total_score'],
                 tool_results=results,
                 timestamp=datetime.now()
             )
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            report_path = "failed_to_generate.md"

        return {
            'status': 'completed',
            'score': score_data['total_score'],
            'grade': score_data['grade'],
            'report_path': str(report_path),
            'results': results
        }
