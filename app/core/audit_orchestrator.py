"""Audit Orchestrator - Coordinates parallel tool execution with caching."""
import asyncio
import time
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional

from app.core.cache_manager import CacheManager
from app.core.report_generator_v2 import ReportGeneratorV2
from app.core.scoring_engine import ScoringEngine
from app.core.trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)


class AuditOrchestrator:
    """
    Orchestrates full project audits with parallel tool execution and caching.

    This class handles:
    - Tool registration and execution
    - Caching of tool results
    - Parallel execution with asyncio
    - Report generation
    """

    def __init__(self, project_path: Path, reports_dir: Path, cache_hours: float = 1.0):
        """
        Initialize the orchestrator.

        Args:
            project_path: Path to the project being audited
            reports_dir: Directory to save reports
            cache_hours: How long to cache results (default 1 hour)
        """
        self.project_path = Path(project_path).resolve()
        self.reports_dir = reports_dir
        self.cache_mgr = CacheManager(str(self.project_path), max_age_hours=cache_hours)
        self.log_callback: Optional[Callable[[str], None]] = None

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """Set a callback function for logging."""
        self.log_callback = callback

    def _log(self, message: str) -> None:
        """Log a message using the callback if set."""
        if self.log_callback:
            self.log_callback(message)
        else:
            logger.info(message)

    async def _run_with_log(self, name: str, coro) -> Dict[str, Any]:
        """Run a coroutine with logging and timing."""
        self._log(f"Starting {name}...")
        try:
            start_t = time.time()
            result = await coro
            if isinstance(result, dict):
                result["duration_s"] = round(time.time() - start_t, 2)
            self._log(f"Finished {name} ({time.time() - start_t:.2f}s)")
            return result
        except Exception as e:
            self._log(f"Failed {name}: {e}")
            return {"tool": name.lower(), "status": "error", "error": str(e)}

    def _create_cached_runner(
        self,
        name: str,
        run_func: Callable[[Path], Dict[str, Any]],
        patterns: List[str]
    ) -> Callable:
        """Create a cached async runner for a tool."""
        async def runner():
            cached = self.cache_mgr.get_cached_result(name, patterns)
            if cached:
                return cached
            result = await asyncio.to_thread(run_func, self.project_path)
            self.cache_mgr.save_result(name, result, patterns)
            return result
        return runner

    def _create_uncached_runner(
        self,
        run_func: Callable[[Path], Dict[str, Any]]
    ) -> Callable:
        """Create an uncached async runner for a tool."""
        async def runner():
            return await asyncio.to_thread(run_func, self.project_path)
        return runner

    async def run_full_audit(
        self,
        tool_runners: Dict[str, Callable[[Path], Dict[str, Any]]],
        job_id: str
    ) -> Dict[str, Any]:
        """
        Run a full audit with all registered tools.

        Args:
            tool_runners: Dict mapping tool names to their run functions
            job_id: Unique identifier for this audit job

        Returns:
            Dictionary with all tool results and metadata
        """
        start_time = time.time()

        # Define cache patterns for each tool
        cache_patterns = {
            "bandit": ["**/*.py"],
            "secrets": ["**/*"],
            "ruff": ["**/*.py"],
            "pip_audit": ["requirements.txt", "pyproject.toml", "setup.py"],
            "structure": ["**/*.py"],
            "dead_code": ["**/*.py"],
            "efficiency": ["**/*.py"],
            "duplication": ["**/*.py"],
            "git_info": [".git/HEAD", ".git/index"],
            "architecture": ["**/*.py"],
            "tests": ["tests/**/*.py", "**/*.py", "pytest.ini", "pyproject.toml"],
            "typing": ["**/*.py"],
        }

        # Tools that don't need caching (fast or state-dependent)
        uncached_tools = {"cleanup", "gitignore"}

        # Build list of coroutines to run
        tasks = []
        task_names = []

        for name, run_func in tool_runners.items():
            if name in uncached_tools:
                runner = self._create_uncached_runner(run_func)
            else:
                patterns = cache_patterns.get(name, ["**/*.py"])
                runner = self._create_cached_runner(name, run_func, patterns)

            tasks.append(self._run_with_log(name.title(), runner()))
            task_names.append(name)

        # Run all tools in parallel
        self._log(f"Launching {len(tasks)} tools in parallel with caching...")
        results = await asyncio.gather(*tasks)

        # Build result dictionary
        duration_seconds = time.time() - start_time
        result_dict = {name: result for name, result in zip(task_names, results)}
        result_dict["duration_seconds"] = duration_seconds
        result_dict["installed_tools"] = []

        return result_dict

    def generate_report(
        self,
        job_id: str,
        result_dict: Dict[str, Any],
        record_trend: bool = True
    ) -> Path:
        """
        Generate a report from audit results.

        Args:
            job_id: Unique identifier for this audit
            result_dict: Dictionary with all tool results
            record_trend: If True, record this audit in trend history

        Returns:
            Path to the generated report file
        """
        self._log(f"Generating Markdown report with Jinja2...")

        # Calculate score for trend recording
        score_breakdown = ScoringEngine.calculate_score(result_dict)
        score = score_breakdown.final_score
        grade = score_breakdown.grade

        # Record trend if enabled
        if record_trend:
            try:
                trend_analyzer = TrendAnalyzer(self.project_path)
                trend_analyzer.record_audit(result_dict, score, grade)
                self._log(f"Recorded audit in trend history: score={score}, grade={grade}")
            except Exception as e:
                self._log(f"Warning: Failed to record trend: {e}")

        generator = ReportGeneratorV2(self.reports_dir)
        report_path = generator.generate_report(
            report_id=job_id,
            project_path=str(self.project_path),
            score=score,
            tool_results=result_dict,
            timestamp=datetime.datetime.now()
        )

        self._log(f"Report generated: {report_path}")

        # Try to generate HTML report as well (optional)
        try:
            html_path = generator.generate_html_report(
                report_id=job_id,
                project_path=str(self.project_path),
                score=score,
                tool_results=result_dict,
                timestamp=datetime.datetime.now(),
                md_report_path=report_path
            )
            self._log(f"HTML Report generated: {html_path}")
        except Exception as e:
            # HTML generation is optional, don't fail the audit
            self._log(f"HTML report generation skipped: {e}")

        return Path(report_path)


def create_default_tool_runners(target: Path) -> Dict[str, Callable[[Path], Dict[str, Any]]]:
    """
    Create the default set of tool runners for a full audit.

    Args:
        target: Path to the project being audited

    Returns:
        Dictionary mapping tool names to runner functions
    """
    # Import tools here to avoid circular imports
    from app.tools.structure_tool import StructureTool
    from app.tools.architecture_tool import ArchitectureTool
    from app.tools.typing_tool import TypingTool
    from app.tools.duplication_tool import DuplicationTool
    from app.tools.deadcode_tool import DeadcodeTool
    from app.tools.fast_audit_tool import FastAuditTool
    from app.tools.secrets_tool import SecretsTool
    from app.tools.tests_tool import TestsTool
    from app.tools.gitignore_tool import GitignoreTool
    from app.tools.git_tool import GitTool
    from app.tools.cleanup_tool import CleanupTool
    from app.tools.bandit_tool import BanditTool
    from app.tools.pip_audit_tool import PipAuditTool

    return {
        "bandit": lambda p: BanditTool().analyze(p),
        "secrets": lambda p: SecretsTool().analyze(p),
        "ruff": lambda p: FastAuditTool().analyze(p),
        "pip_audit": lambda p: PipAuditTool().analyze(p),
        "structure": lambda p: StructureTool().analyze(p),
        "dead_code": lambda p: DeadcodeTool().analyze(p),
        "efficiency": lambda p: FastAuditTool().analyze(p),
        "duplication": lambda p: DuplicationTool().analyze(p),
        "git_info": lambda p: GitTool().analyze(p),
        "cleanup": lambda p: CleanupTool().analyze(p),
        "architecture": lambda p: ArchitectureTool().generate_dependency_graph(p),
        "tests": lambda p: TestsTool().analyze(p),
        "typing": lambda p: TypingTool().analyze(p),
        "gitignore": lambda p: GitignoreTool().analyze(p),
    }


def create_default_tool_instances() -> Dict[str, Any]:
    """
    Create the default set of tool instances for incremental audits.

    Returns:
        Dictionary mapping tool names to tool instances or callables
    """
    from app.tools.structure_tool import StructureTool
    from app.tools.architecture_tool import ArchitectureTool
    from app.tools.typing_tool import TypingTool
    from app.tools.duplication_tool import DuplicationTool
    from app.tools.deadcode_tool import DeadcodeTool
    from app.tools.fast_audit_tool import FastAuditTool
    from app.tools.secrets_tool import SecretsTool
    from app.tools.tests_tool import TestsTool
    from app.tools.gitignore_tool import GitignoreTool
    from app.tools.git_tool import GitTool
    from app.tools.bandit_tool import BanditTool

    return {
        "structure": StructureTool(),
        "architecture": ArchitectureTool(),
        "typing": TypingTool(),
        "duplication": DuplicationTool(),
        "deadcode": DeadcodeTool(),
        "efficiency": FastAuditTool(),
        "secrets": SecretsTool(),
        "tests": TestsTool(),
        "gitignore": GitignoreTool(),
        "git": GitTool(),
        "bandit": BanditTool(),
        "quality": FastAuditTool(),
    }
