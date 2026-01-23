"""Pip-audit vulnerability scanning tool - Check for vulnerable dependencies."""
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class PipAuditTool(BaseTool):
    """Run pip-audit to check for vulnerable dependencies."""

    DEFAULT_TIMEOUT = 180  # seconds - pip-audit can be slow

    @property
    def description(self) -> str:
        return "Scans Python dependencies for known security vulnerabilities using pip-audit"

    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Run pip-audit vulnerability scan.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with vulnerabilities found
        """
        if not self.validate_path(project_path):
            return {
                "tool": "pip-audit",
                "status": "error",
                "error": "Invalid path",
                "vulnerabilities": [],
                "total_vulnerabilities": 0
            }

        try:
            target_path = Path(project_path).resolve()

            # Check if requirements.txt exists - much faster scan
            req_file = target_path / "requirements.txt"
            pyproject_file = target_path / "pyproject.toml"

            if req_file.exists():
                cmd = ["pip-audit", "-r", str(req_file), "-f", "json"]
                scan_mode = "requirements.txt"
            elif pyproject_file.exists():
                # Try pyproject.toml if available
                cmd = ["pip-audit", "-f", "json"]
                scan_mode = "pyproject.toml"
            else:
                # Fallback to environment scan
                cmd = ["pip-audit", "-f", "json"]
                scan_mode = "environment"

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.DEFAULT_TIMEOUT,
                    cwd=str(target_path),
                    stdin=subprocess.DEVNULL
                )
            except subprocess.TimeoutExpired:
                return {
                    "tool": "pip-audit",
                    "status": "error",
                    "error": f"Timeout (>{self.DEFAULT_TIMEOUT}s)",
                    "vulnerabilities": [],
                    "total_vulnerabilities": 0
                }
            except FileNotFoundError:
                return {
                    "tool": "pip-audit",
                    "status": "skipped",
                    "error": "pip-audit not installed",
                    "vulnerabilities": [],
                    "total_vulnerabilities": 0
                }

            # Parse JSON output
            try:
                data = json.loads(result.stdout) if result.stdout else []
            except json.JSONDecodeError:
                logger.warning("Failed to parse pip-audit JSON output")
                data = []

            # Safe handling - ensure data is a list
            if not isinstance(data, list):
                data = []

            # Categorize by severity if available
            severity_counts = self._count_by_severity(data)

            return {
                "tool": "pip-audit",
                "status": "vulnerabilities_found" if data else "clean",
                "total_vulnerabilities": len(data),
                "vulnerabilities": data[:20],  # Limit to first 20
                "scan_mode": scan_mode,
                "severity_counts": severity_counts
            }

        except Exception as e:
            logger.error(f"Pip-audit analysis failed: {e}")
            return {
                "tool": "pip-audit",
                "status": "error",
                "error": str(e),
                "vulnerabilities": [],
                "total_vulnerabilities": 0
            }

    def _count_by_severity(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count vulnerabilities by severity level."""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        for vuln in vulnerabilities:
            # pip-audit may have different severity field names
            severity = vuln.get("severity", vuln.get("fix_versions", "UNKNOWN"))
            if isinstance(severity, str) and severity.upper() in counts:
                counts[severity.upper()] += 1
            else:
                counts["UNKNOWN"] += 1
        return counts
