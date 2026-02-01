"""PR Audit Tool - Fast delta-based security and quality checks for PRs.

Uses BanditTool and FastAuditTool for analysis to avoid code duplication.
"""

import logging
from pathlib import Path
from typing import Any

from app.core.base_tool import BaseTool
from app.tools.bandit_tool import BanditTool
from app.tools.fast_audit_tool import FastAuditTool

logger = logging.getLogger(__name__)


class PRAuditTool(BaseTool):
    """Fast audit of changed files for PR review.

    Composes BanditTool and FastAuditTool for analysis instead of
    duplicating subprocess logic.
    """

    def __init__(self):
        """Initialize with composed tools."""
        super().__init__()
        self._bandit = BanditTool()
        self._ruff = FastAuditTool()

    @property
    def description(self) -> str:
        return "Runs security and quality scans on changed files for PR gatekeeper"

    def analyze(self, project_path: Path, changed_files: list[str] = None) -> dict[str, Any]:
        """Analyze changed files for PR.

        Args:
            project_path: Path to the project directory
            changed_files: List of changed file paths (relative to project)

        Returns:
            Dictionary with scan results, score, and recommendation

        """
        if not self.validate_path(project_path):
            return {"status": "error", "error": "Invalid path"}

        if not changed_files:
            return {
                "status": "success",
                "message": "No Python changes detected",
                "score": 100,
                "recommendation": "ready_for_review",
            }

        target = Path(project_path).resolve()

        # Use composed tools for analysis (single source of truth)
        bandit_raw = self._bandit.analyze_files(target, changed_files)
        ruff_raw = self._ruff.analyze_files(target, changed_files)

        # Transform results to PR audit format
        bandit_result = self._transform_bandit_result(bandit_raw)
        ruff_result = self._transform_ruff_result(ruff_raw)
        complexity_result = self._extract_complexity_from_ruff(ruff_raw)

        # Calculate score
        score = self._calculate_score(bandit_result, ruff_result, complexity_result)

        # Determine recommendation
        recommendation = self._get_recommendation(bandit_result, score)

        return {
            "status": "success",
            "score": score,
            "recommendation": recommendation,
            "changed_files_count": len(changed_files),
            "bandit": bandit_result,
            "ruff": ruff_result,
            "complexity": complexity_result,
        }

    def _transform_bandit_result(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Transform BanditTool result to PR audit format."""
        if raw.get("error"):
            return {"error": raw["error"], "total_issues": 0, "issues": []}

        issues = [
            {
                "severity": issue.get("issue_severity"),
                "file": issue.get("filename"),
                "line": issue.get("line_number"),
                "description": issue.get("issue_text"),
                "code": issue.get("test_id"),
            }
            for issue in raw.get("issues", [])
        ]
        return {"total_issues": len(issues), "issues": issues[:10]}

    def _transform_ruff_result(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Transform FastAuditTool result to PR audit format."""
        if raw.get("error"):
            return {"error": raw["error"], "total_issues": 0, "issues": []}

        # Collect all non-complexity issues
        all_issues = []
        for category in ["security", "quality", "style", "imports", "performance"]:
            all_issues.extend(raw.get(category, []))

        # Transform to expected format
        issues = [
            {
                "filename": issue.get("file", ""),
                "code": issue.get("code", ""),
                "message": issue.get("message", ""),
                "location": {"row": issue.get("line", 0), "column": issue.get("column", 0)},
            }
            for issue in all_issues
        ]
        return {"total_issues": len(issues), "issues": issues[:10]}

    def _extract_complexity_from_ruff(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Extract complexity findings from FastAuditTool result."""
        if raw.get("error"):
            return {"error": raw["error"], "total_high_complexity": 0, "functions": []}

        complexity_issues = raw.get("complexity", [])
        functions = [
            {
                "file": Path(issue.get("file", "")).name,
                "function": issue.get("message", "").split("'")[1] if "'" in issue.get("message", "") else "unknown",
                "complexity": self._parse_complexity_from_message(issue.get("message", "")),
                "rank": self._complexity_to_rank(self._parse_complexity_from_message(issue.get("message", ""))),
            }
            for issue in complexity_issues
        ]
        return {"total_high_complexity": len(functions), "functions": functions[:10]}

    def _parse_complexity_from_message(self, message: str) -> int:
        """Parse complexity value from Ruff C90x message."""
        import re

        match = re.search(r"complexity of (\d+)", message)
        return int(match.group(1)) if match else 0

    def _complexity_to_rank(self, complexity: int) -> str:
        """Convert complexity score to letter rank."""
        if complexity <= 5:
            return "A"
        if complexity <= 10:
            return "B"
        if complexity <= 20:
            return "C"
        if complexity <= 30:
            return "D"
        if complexity <= 40:
            return "E"
        return "F"

    def _calculate_score(self, bandit: dict[str, Any], ruff: dict[str, Any], complexity: dict[str, Any]) -> int:
        """Calculate PR score based on scan results."""
        score = 100

        # Security penalties (max -30)
        bandit_issues = bandit.get("total_issues", 0)
        if bandit_issues > 0:
            score -= min(bandit_issues * 5, 30)

        # Quality penalties (max -20)
        ruff_issues = ruff.get("total_issues", 0)
        if ruff_issues > 0:
            score -= min(ruff_issues * 2, 20)

        # Complexity penalties (max -15)
        complexity_issues = complexity.get("total_high_complexity", 0)
        if complexity_issues > 0:
            score -= min(complexity_issues * 3, 15)

        return max(0, score)

    def _get_recommendation(self, bandit: dict[str, Any], score: int) -> str:
        """Get recommendation based on results."""
        if bandit.get("total_issues", 0) > 0:
            return "request_changes"
        if score >= 80:
            return "ready_for_review"
        return "needs_improvement"

    def generate_report(
        self,
        base_branch: str,
        changed_files: list[str],
        result: dict[str, Any],
        tests_passed: bool = True,
        test_output: str = "",
        run_tests: bool = True,
        target: Path = None,
    ) -> str:
        """Generate Markdown report for PR audit."""
        score = result.get("score", 0)
        md = ["# PR Gatekeeper Report", ""]
        md.append(f"**Base Branch:** `{base_branch}`")
        md.append(f"**Changed Files:** {len(changed_files)} Python files")
        md.append(f"**Score:** {score}/100")
        md.append("")

        # Changed files section
        md.append("## Changed Files")
        for f in changed_files[:20]:
            if target:
                try:
                    rel_path = Path(f).relative_to(target) if Path(f).is_absolute() else f
                except ValueError:
                    rel_path = f
            else:
                rel_path = f
            md.append(f"- `{rel_path}`")
        if len(changed_files) > 20:
            md.append(f"- ...and {len(changed_files) - 20} more")
        md.append("")

        # Security findings
        bandit = result.get("bandit", {})
        bandit_count = bandit.get("total_issues", 0)
        md.append("## Security Scan (Bandit)")
        if bandit_count > 0:
            md.append(f"**Status:** {bandit_count} issue(s) found")
            for issue in bandit.get("issues", [])[:5]:
                fname = Path(issue.get("file", "")).name
                md.append(f"- **{issue.get('severity')}** in `{fname}:{issue.get('line')}`: {issue.get('description', '')}")
        else:
            md.append("**Status:** No security issues detected")
        md.append("")

        # Linting findings
        ruff = result.get("ruff", {})
        ruff_count = ruff.get("total_issues", 0)
        md.append("## Code Quality (Ruff)")
        if ruff_count > 0:
            md.append(f"**Status:** {ruff_count} issue(s) found")
            for issue in ruff.get("issues", [])[:5]:
                fname = Path(issue.get("filename", "")).name
                row = issue.get("location", {}).get("row", "?")
                md.append(f"- `{fname}:{row}` - {issue.get('code')}: {issue.get('message', '')}")
        else:
            md.append("**Status:** No linting issues detected")
        md.append("")

        # Complexity findings
        complexity = result.get("complexity", {})
        complexity_count = complexity.get("total_high_complexity", 0)
        md.append("## Complexity (Radon)")
        if complexity_count > 0:
            md.append(f"**Status:** {complexity_count} high-complexity function(s)")
            for func in complexity.get("functions", [])[:5]:
                md.append(f"- `{func['function']}` in `{func['file']}`: Complexity {func['complexity']} (Rank {func['rank']})")
        else:
            md.append("**Status:** No high-complexity functions")
        md.append("")

        # Test results
        if run_tests:
            md.append("## Test Safety Net")
            if score > 80:
                if tests_passed:
                    md.append("**Status:** All tests passed")
                else:
                    md.append("**Status:** Tests failed")
                    md.append(f"```\n{test_output[:500]}\n```")
            else:
                md.append("**Status:** Skipped (score too low, fix issues first)")
            md.append("")

        # Bottom line
        md.append("---\n## Bottom Line\n")
        recommendation = result.get("recommendation", "needs_improvement")
        if recommendation == "request_changes":
            md.append("### Request Changes\n\n**Blocking Issues:**")
            if bandit_count > 0:
                md.append(f"- {bandit_count} security issue(s)")
            if not tests_passed and run_tests and score > 80:
                md.append("- Tests failing")
        elif recommendation == "ready_for_review":
            md.append("### Ready for Review\n\nCode quality is good, no blocking issues detected.")
        else:
            md.append(f"### Needs Improvement\n\nScore is {score}/100. Please address the issues above.")

        md.append("\n\n---\n*Generated by Python Auditor MCP - PR Gatekeeper*")
        return "\n".join(md)
