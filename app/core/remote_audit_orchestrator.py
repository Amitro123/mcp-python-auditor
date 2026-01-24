"""Remote Audit Orchestrator - Handles git clone + audit for remote repositories."""
import shutil
import subprocess
import tempfile
import time
import datetime
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from app.core.audit_orchestrator import AuditOrchestrator, create_default_tool_runners
from app.core.scoring_engine import ScoringEngine
from app.core.report_generator_v2 import ReportGeneratorV2

logger = logging.getLogger(__name__)


class RemoteAuditOrchestrator:
    """
    Orchestrates audits of remote Git repositories.

    Handles:
    - URL validation
    - Git clone operations
    - Audit execution via AuditOrchestrator
    - Cleanup of temporary directories
    """

    def __init__(self, reports_dir: Path, cache_hours: float = 1.0):
        """
        Initialize remote audit orchestrator.

        Args:
            reports_dir: Directory to save reports
            cache_hours: How long to cache results
        """
        self.reports_dir = reports_dir
        self.cache_hours = cache_hours
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

    def validate_url(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """
        Validate repository URL.

        Returns None if valid, error dict if invalid.
        """
        if not repo_url.startswith(("http://", "https://", "git@")):
            return {
                "status": "error",
                "error": "Invalid repository URL.",
                "suggestion": "Use http://, https://, or git@ URL"
            }
        return None

    def clone_repository(
        self,
        repo_url: str,
        branch: str,
        target_path: Path,
        timeout: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        Clone a repository to target path.

        Returns None on success, error dict on failure.
        """
        if not shutil.which("git"):
            return {
                "status": "error",
                "error": "Git not installed",
                "suggestion": "Install git command line tool"
            }

        clone_cmd = ["git", "clone", "--depth", "1", "-b", branch, repo_url, str(target_path)]

        try:
            result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL
            )

            if result.returncode != 0:
                err = result.stderr
                suggestion = "Check the repository URL and network connection."

                if "not found" in err.lower():
                    suggestion = "Check the URL and ensure the repository exists."
                elif "authentication" in err.lower() or "private" in err.lower():
                    suggestion = "This tool supports public repositories. Check credentials for private ones."
                elif f"branch '{branch}'" in err.lower() or "did not match any" in err.lower():
                    suggestion = f"Check the branch name. '{branch}' may not exist."

                return {
                    "status": "error",
                    "error": f"Git clone failed: {err}",
                    "suggestion": suggestion
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": f"Clone operation timeout (>{timeout}s)",
                "suggestion": "Repository might be too large or network is slow."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Clone error: {e}",
                "suggestion": "Unexpected error during clone."
            }

        return None  # Success

    async def audit_repository(
        self,
        repo_url: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Audit a remote Git repository.

        Args:
            repo_url: URL of the repository to audit
            branch: Branch to audit (default: main)

        Returns:
            Dictionary with audit results
        """
        self._log(f"Starting remote audit: {repo_url} (branch: {branch})")

        # Validate URL
        validation_error = self.validate_url(repo_url)
        if validation_error:
            return validation_error

        try:
            with tempfile.TemporaryDirectory(prefix="audit_remote_") as temp_dir:
                temp_path = Path(temp_dir)

                # Clone repository
                clone_error = self.clone_repository(repo_url, branch, temp_path)
                if clone_error:
                    return clone_error

                # Check for Python files
                py_files = list(temp_path.glob("**/*.py"))
                if not py_files:
                    return {
                        "status": "warning",
                        "message": "No Python files found",
                        "repo_url": repo_url,
                        "branch": branch
                    }

                # Create job ID
                job_id = f"remote_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                start_time = time.time()

                # Use AuditOrchestrator for the actual audit
                orchestrator = AuditOrchestrator(temp_path, self.reports_dir, self.cache_hours)
                orchestrator.set_log_callback(self._log)

                tool_runners = create_default_tool_runners(temp_path)
                result_dict = await orchestrator.run_full_audit(tool_runners, job_id)

                duration_seconds = time.time() - start_time
                result_dict["duration_seconds"] = duration_seconds

                # Calculate score
                score_breakdown = ScoringEngine.calculate_score(result_dict)
                score = score_breakdown.final_score

                # Generate report
                generator = ReportGeneratorV2(self.reports_dir)
                report_path = generator.generate_report(
                    report_id=job_id,
                    project_path=str(temp_path),
                    score=score,
                    tool_results=result_dict,
                    timestamp=datetime.datetime.now()
                )
                report_md = Path(report_path).read_text(encoding='utf-8')

                return {
                    "status": "success",
                    "repo_url": repo_url,
                    "branch": branch,
                    "score": score,
                    "duration": f"{duration_seconds:.1f}s",
                    "files_analyzed": len(py_files),
                    "report_path": str(report_path),
                    "report": report_md,
                    "summary": {
                        "security_issues": result_dict.get("bandit", {}).get("total_issues", 0),
                        "secrets_found": result_dict.get("secrets", {}).get("total_findings", 0),
                        "test_coverage": result_dict.get("tests", {}).get("coverage_percent", 0),
                        "duplicates": result_dict.get("duplication", {}).get("total_duplicates", 0),
                        "dead_code": result_dict.get("dead_code", {}).get("total_dead_code", 0),
                        "high_complexity": len(result_dict.get("efficiency", {}).get("complexity", []))
                    }
                }

        except Exception as e:
            self._log(f"Remote audit failed: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "suggestion": "Check system logs."
            }
