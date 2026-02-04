"""CLI Adapter - Maps legacy audit.py CLI interface to new AuditOrchestrator.

This module provides backward compatibility by translating the legacy tool names
and result formats used by audit.py CLI to the new orchestrator architecture.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.core.audit_orchestrator import AuditOrchestrator
from app.core.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)

# Legacy tool names from audit.py CLI
LEGACY_TOOLS = {
    "security": ["bandit", "secrets", "pip-audit"],
    "quality": ["ruff", "duplication", "deadcode", "cleanup"],
    "analysis": ["coverage", "complexity", "typing"],
}

# Mapping from legacy tool names to new orchestrator tool names
TOOL_NAME_MAP = {
    "bandit": "bandit",
    "secrets": "secrets",
    "pip-audit": "pip_audit",
    "ruff": "ruff",  # FastAuditTool provides this
    "duplication": "duplication",
    "deadcode": "dead_code",
    "cleanup": "cleanup",
    "coverage": "tests",  # TestsTool provides coverage
    "complexity": "ruff",  # FastAuditTool provides complexity via McCabe
    "typing": "typing",
}

# Tools that should be skipped in fast mode
SLOW_TOOLS = {"coverage", "pip-audit", "bandit", "deadcode", "secrets"}
VERY_SLOW_TOOLS = {"secrets", "coverage"}


class CLIAdapter:
    """Adapter to bridge legacy audit.py CLI and new AuditOrchestrator."""

    def __init__(self, project_path: Path):
        """Initialize the adapter.

        Args:
            project_path: Path to the project being audited

        """
        self.project_path = Path(project_path).resolve()
        self.orchestrator = AuditOrchestrator(
            project_path=self.project_path,
            reports_dir=Path("reports"),
            cache_hours=1.0,
        )

    async def run_audit(
        self,
        *,
        fast: bool = False,
        skip_slow: bool = False,
        skip_secrets: bool = False,
        pr_files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run audit using orchestrator with legacy CLI options.

        Args:
            fast: Skip slow tools (coverage, pip-audit, bandit, deadcode, secrets)
            skip_slow: Skip very slow tools (secrets, coverage)
            skip_secrets: Skip secrets scan
            pr_files: List of changed files for PR mode

        Returns:
            Dictionary with tool results in legacy format

        """
        # Determine which tools to skip
        skip_tools = set()
        if fast:
            skip_tools = SLOW_TOOLS
        elif skip_slow:
            skip_tools = VERY_SLOW_TOOLS
        elif skip_secrets:
            skip_tools = {"secrets"}

        # Import only available tools
        # Import file discovery for performance optimization
        from app.core.file_discovery import get_project_files
        from app.tools.bandit_tool import BanditTool
        from app.tools.cleanup_tool import CleanupTool
        from app.tools.deadcode_tool import DeadcodeTool
        from app.tools.duplication_tool import DuplicationTool
        from app.tools.fast_audit_tool import FastAuditTool
        from app.tools.pip_audit_tool import PipAuditTool
        from app.tools.secrets_tool import SecretsTool
        from app.tools.tests_tool import TestsTool
        from app.tools.typing_tool import TypingTool

        # Get project files once for all tools that need it
        project_files = get_project_files(self.project_path)

        # Create tool runners for available tools only
        tool_runners = {}

        # Helper to run tools with file lists for better performance
        def run_with_files(tool_class, p):
            """Run a tool with file discovery for better performance."""
            return tool_class().analyze(p, file_list=project_files)

        # Map legacy tool names to new tool instances
        if "bandit" not in skip_tools:
            tool_runners["bandit"] = lambda p: BanditTool().analyze(p)
        if "secrets" not in skip_tools:
            tool_runners["secrets"] = lambda p: SecretsTool().analyze(p)
        if "pip-audit" not in skip_tools:
            tool_runners["pip_audit"] = lambda p: PipAuditTool().analyze(p)
        if "ruff" not in skip_tools:
            tool_runners["ruff"] = lambda p: FastAuditTool().analyze(p)
        if "duplication" not in skip_tools:
            # Pass file list to avoid full recursive scan
            tool_runners["duplication"] = lambda p: run_with_files(DuplicationTool, p)
        if "deadcode" not in skip_tools:
            # Pass file list to avoid Vulture timeout
            tool_runners["dead_code"] = lambda p: run_with_files(DeadcodeTool, p)
        if "cleanup" not in skip_tools:
            tool_runners["cleanup"] = lambda p: CleanupTool().analyze(p)
        if "coverage" not in skip_tools:
            tool_runners["tests"] = lambda p: TestsTool().analyze(p)
        if "typing" not in skip_tools:
            tool_runners["typing"] = lambda p: TypingTool().analyze(p)

        # Run audit
        job_id = f"audit_{self.project_path.name}"
        results = await self.orchestrator.run_full_audit(tool_runners=tool_runners, job_id=job_id)

        # Transform results to legacy format
        return self._transform_to_legacy_format(results, skip_tools)


    def _transform_to_legacy_format(self, orchestrator_results: dict[str, Any], skipped_tools: set[str]) -> dict[str, Any]:
        """Transform orchestrator results to legacy audit.py format.

        Args:
            orchestrator_results: Results from AuditOrchestrator
            skipped_tools: Set of legacy tool names that were skipped

        Returns:
            Dictionary in legacy format with 'data', 'score', 'timings', etc.

        """
        legacy_data = {}

        # Map orchestrator results back to legacy tool names
        reverse_map = {v: k for k, v in TOOL_NAME_MAP.items()}

        for new_name, result in orchestrator_results.items():
            if new_name in ["duration_seconds", "installed_tools"]:
                continue

            # Handle tools that map to multiple legacy names
            if new_name == "ruff":
                # FastAuditTool provides both ruff and complexity
                legacy_data["ruff"] = self._extract_ruff_data(result)
                legacy_data["complexity"] = self._extract_complexity_data(result)
            elif new_name == "tests":
                # TestsTool provides coverage
                legacy_data["coverage"] = self._extract_coverage_data(result)
            elif new_name in reverse_map:
                legacy_name = reverse_map[new_name]
                legacy_data[legacy_name] = self._extract_generic_data(result, legacy_name)

        # Mark skipped tools
        for tool in skipped_tools:
            if tool not in legacy_data:
                legacy_data[tool] = {"total": 0, "skipped": True}

        # Calculate score using ScoringEngine
        score_breakdown = ScoringEngine.calculate_score(orchestrator_results)

        # Format penalties for legacy format
        penalties = []
        if score_breakdown.security_penalty > 0:
            penalties.append(f"-{score_breakdown.security_penalty} Security issues")
        if score_breakdown.quality_penalty > 0:
            penalties.append(f"-{score_breakdown.quality_penalty} Quality issues")
        if score_breakdown.testing_penalty > 0:
            penalties.append(f"-{score_breakdown.testing_penalty} Testing gaps")
        if score_breakdown.maintenance_penalty > 0:
            penalties.append(f"-{score_breakdown.maintenance_penalty} Maintenance issues")

        return {
            "data": legacy_data,
            "score": score_breakdown.final_score,
            "grade": score_breakdown.grade,
            "penalties": penalties,
            "timings": self._extract_timings(orchestrator_results),
            "completed": sum(1 for d in legacy_data.values() if not d.get("skipped")),
            "failed": 0,  # Orchestrator handles failures differently
        }

    def _extract_ruff_data(self, result: dict[str, Any]) -> dict[str, Any]:
        """Extract Ruff-specific data from FastAuditTool result."""
        quality_issues = result.get("quality", [])
        return {
            "total": len(quality_issues),
            "all": result.get("total_issues", 0),
            "status": result.get("status", "clean"),
            "samples": [
                {
                    "file": i.get("file"),
                    "line": i.get("line"),
                    "code": i.get("code"),
                    "msg": i.get("message"),
                }
                for i in quality_issues
            ],
        }

    def _extract_complexity_data(self, result: dict[str, Any]) -> dict[str, Any]:
        """Extract complexity data from FastAuditTool result."""
        complexity_issues = result.get("complexity", [])
        # Simplified grade mapping
        if len(complexity_issues) == 0:
            grade = "A"
        elif len(complexity_issues) < 5:
            grade = "B"
        elif len(complexity_issues) < 10:
            grade = "C"
        else:
            grade = "D"

        return {"grade": grade, "total": len(complexity_issues)}

    def _extract_coverage_data(self, result: dict[str, Any]) -> dict[str, Any]:
        """Extract coverage data from TestsTool result."""
        coverage_pct = result.get("coverage_percent", 0)
        return {
            "percent": coverage_pct,
            "status": result.get("status", "clean"),
        }

    def _extract_generic_data(self, result: dict[str, Any], tool_name: str) -> dict[str, Any]:
        """Extract generic tool data."""
        # Handle different field names used by various tools
        # Order matters: check most specific first
        total = result.get(
            "total_issues",
            result.get(
                "total_vulnerabilities",  # pip-audit uses this
                result.get("total", result.get("total_secrets", result.get("total_items", 0))),
            ),
        )
        return {
            "total": total,
            "status": result.get("status", "clean"),
            "error": result.get("error"),
            "samples": self._extract_samples(result, tool_name),
        }

    def _extract_samples(self, result: dict[str, Any], tool_name: str) -> list[dict[str, Any]]:
        """Extract sample issues from tool result."""
        samples = []

        if tool_name == "secrets":
            for s in result.get("secrets", []):
                samples.append({"file": s.get("file"), "line": s.get("line"), "type": s.get("type"), "msg": "Potential secret found"})
        elif tool_name == "bandit":
            # Handle nested code_security if present
            issues = result.get("issues", [])
            if "code_security" in result:
                issues = result["code_security"].get("issues", [])

            for i in issues:
                samples.append(
                    {
                        "file": i.get("filename") or i.get("file"),
                        "line": i.get("line_number") or i.get("line"),
                        "code": i.get("test_id") or i.get("code"),
                        "msg": i.get("issue_text") or i.get("message"),
                        "severity": i.get("issue_severity") or i.get("severity"),
                    }
                )
        elif tool_name == "pip-audit":
            # pip-audit vulnerabilities format
            for v in result.get("vulnerabilities", []):
                # Handle both list and dict format for fix_versions
                fix_versions = v.get("fix_versions", [])
                fix_version = fix_versions[0] if isinstance(fix_versions, list) and fix_versions else ""
                samples.append(
                    {
                        "package": v.get("name", ""),
                        "version": v.get("version", ""),
                        "vuln_id": v.get("id", v.get("vuln_id", "")),
                        "fix_version": fix_version,
                    }
                )

        return samples

    def _extract_timings(self, results: dict[str, Any]) -> dict[str, float]:
        """Extract timing information from orchestrator results."""
        timings = {}
        for name, result in results.items():
            if isinstance(result, dict) and "duration_s" in result:
                # Map back to legacy name
                reverse_map = {v: k for k, v in TOOL_NAME_MAP.items()}
                legacy_name = reverse_map.get(name, name)
                timings[legacy_name] = result["duration_s"]
        return timings


def run_audit_sync(
    project_path: Path,
    *,
    fast: bool = False,
    skip_slow: bool = False,
    skip_secrets: bool = False,
    pr_files: list[str] | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper for running audit (for CLI compatibility).

    Args:
        project_path: Path to the project
        fast: Skip slow tools
        skip_slow: Skip very slow tools
        skip_secrets: Skip secrets scan
        pr_files: List of changed files for PR mode

    Returns:
        Dictionary with audit results in legacy format

    """
    adapter = CLIAdapter(project_path)
    return asyncio.run(
        adapter.run_audit(
            fast=fast,
            skip_slow=skip_slow,
            skip_secrets=skip_secrets,
            pr_files=pr_files,
        )
    )
