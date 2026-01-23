"""Bandit security analysis tool - Python security linter."""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class BanditTool(BaseTool):
    """Run Bandit security analysis on Python code."""

    DEFAULT_TIMEOUT = 120  # seconds

    @property
    def description(self) -> str:
        return "Runs Bandit security linter to find security vulnerabilities in Python code"

    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Run Bandit security analysis.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with security issues found
        """
        if not self.validate_path(project_path):
            return {"tool": "bandit", "status": "error", "error": "Invalid path", "issues": [], "total_issues": 0}

        try:
            target_path = Path(project_path).resolve()

            # Use explicit config to exclude tests and skip false positives
            cmd = [
                sys.executable, "-m", "bandit",
                "-c", "pyproject.toml",
                "-r", str(target_path),
                "-f", "json",
                "--exit-zero"
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.DEFAULT_TIMEOUT,
                    cwd=str(target_path),  # Run from root so config is found
                    stdin=subprocess.DEVNULL
                )
            except subprocess.TimeoutExpired:
                return {
                    "tool": "bandit",
                    "status": "error",
                    "error": f"Timeout (>{self.DEFAULT_TIMEOUT}s)",
                    "issues": [],
                    "total_issues": 0
                }
            except FileNotFoundError:
                return {
                    "tool": "bandit",
                    "status": "skipped",
                    "error": "Bandit not installed",
                    "issues": [],
                    "total_issues": 0
                }

            # Parse JSON output
            bandit_data = {}
            if result.stdout.strip():
                try:
                    bandit_data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Bandit JSON output")

            issues = bandit_data.get("results", [])
            metrics = bandit_data.get("metrics", {})

            # Extract files scanned from metrics
            files_scanned = metrics.get("_totals", {}).get("loc", 0) if metrics else 0

            # If metrics doesn't have totals, count unique files from results
            if files_scanned == 0 and issues:
                files_scanned = len(set(issue.get("filename", "") for issue in issues))

            # Categorize by severity
            severity_counts = self._count_by_severity(issues)

            return {
                "tool": "bandit",
                "status": "issues_found" if issues else "clean",
                "total_issues": len(issues),
                "issues": issues,
                "metrics": metrics,
                "files_scanned": files_scanned,
                "severity_counts": severity_counts
            }

        except Exception as e:
            logger.error(f"Bandit analysis failed: {e}")
            return {
                "tool": "bandit",
                "status": "error",
                "error": str(e),
                "issues": [],
                "total_issues": 0
            }

    def _count_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by severity level."""
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in issues:
            severity = issue.get("issue_severity", "LOW")
            counts[severity] = counts.get(severity, 0) + 1
        return counts
