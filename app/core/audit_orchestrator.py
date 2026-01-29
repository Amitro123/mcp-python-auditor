"""
Audit Orchestrator - Async Implementation with DB Support.
"""
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from app.core.tool_registry import ToolRegistry
from app.core.scoring_engine import ScoringEngine
from app.core.report_generator_v2 import ReportGeneratorV2
from app.core.audit_state import AuditStateManager

logger = logging.getLogger(__name__)

# Global lock to prevent concurrent SQLite writes
_DB_LOCK = asyncio.Lock()

class AuditOrchestrator:
    """Orchestrator for code audit tools."""

    def __init__(self, project_path: Path, reports_dir: Path):
        self.project_path = Path(project_path).resolve()
        self.reports_dir = reports_dir

    def run_audit(self) -> Dict[str, Any]:
        """Run all enabled tools synchronously (Legacy)."""
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

    async def run_audit_async(self, audit_id: str) -> Dict[str, Any]:
        """Async version with parallel execution and DB updates."""
        state_manager = AuditStateManager()

        tools = ToolRegistry.discover_tools()

        logger.info(f"Starting async audit for {self.project_path} (id={audit_id})")

        # Init DB
        try:
            async with _DB_LOCK:
                await asyncio.to_thread(state_manager.create_audit, audit_id, str(self.project_path), len(tools))
                await asyncio.to_thread(state_manager.start_audit, audit_id)
        except Exception as e:
            logger.error(f"Failed to initialize audit state: {e}")
            # Continue anyway, DB might be locked or issues, but we want results

        async def _run_tool_safe(tool):
            try:
                start = time.time()
                logger.info(f"Starting {tool.name}...")

                # Run in thread pool to avoid blocking event loop
                result = await asyncio.to_thread(tool.analyze, self.project_path)
                duration = time.time() - start

                result['duration_seconds'] = duration
                logger.info(f"{tool.name} completed in {duration:.2f}s")

                # Save result to DB (in thread to avoid blocking loop with SQLite)
                async with _DB_LOCK:
                    await asyncio.to_thread(
                        state_manager.save_tool_result,
                        audit_id, tool.name, result, duration
                    )

                return tool.name, result
            except Exception as e:
                logger.error(f"{tool.name} failed: {e}")
                err_result = {'status': 'error', 'error': str(e)}

                try:
                    async with _DB_LOCK:
                        await asyncio.to_thread(
                            state_manager.save_tool_result,
                            audit_id, tool.name, err_result, 0, status='failed', error=str(e)
                        )
                except Exception as db_err:
                    logger.error(f"Failed to save error state for {tool.name}: {db_err}")

                return tool.name, err_result

        # Execute in parallel
        tasks = [_run_tool_safe(tool) for tool in tools]
        tool_results_list = await asyncio.gather(*tasks)
        results = dict(tool_results_list)

        # Calculate score
        score_data = ScoringEngine.calculate_score(results)

        # Generate Report
        report_path = "failed_to_generate.md"
        try:
             report_gen = ReportGeneratorV2(self.reports_dir)
             # Use audit_id for report filename
             report_path = report_gen.generate_report(
                 report_id=audit_id,
                 project_path=str(self.project_path),
                 score=score_data['total_score'],
                 tool_results=results,
                 timestamp=datetime.now()
             )
        except Exception as e:
            logger.error(f"Report generation failed: {e}")

        # Complete DB
        try:
            if report_path != "failed_to_generate.md":
                 # Save summary first
                 async with _DB_LOCK:
                     await asyncio.to_thread(
                         state_manager.save_audit_summary,
                         audit_id,
                         {
                             'score': score_data['total_score'],
                             'grade': score_data['grade'],
                             'metrics': {'duration': sum(r.get('duration_seconds', 0) for r in results.values())}
                         }
                     )
                     # Mark complete
                     await asyncio.to_thread(state_manager.complete_audit, audit_id)
            else:
                 async with _DB_LOCK:
                     await asyncio.to_thread(state_manager.fail_audit, audit_id, "Report generation failed")
        except Exception as e:
            logger.error(f"Failed to update final audit state: {e}")

        return {
            'status': 'completed',
            'score': score_data['total_score'],
            'grade': score_data['grade'],
            'report_path': str(report_path),
            'results': results
        }
