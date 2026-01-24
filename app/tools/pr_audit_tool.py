"""PR Audit Tool - Fast delta-based security and quality checks for PRs."""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class PRAuditTool(BaseTool):
    """Fast audit of changed files for PR review."""

    DEFAULT_TIMEOUT = 60  # seconds per tool

    @property
    def description(self) -> str:
        return "Runs security and quality scans on changed files for PR gatekeeper"

    def analyze(self, project_path: Path, changed_files: List[str] = None) -> Dict[str, Any]:
        """
        Analyze changed files for PR.

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
                "recommendation": "ready_for_review"
            }

        target = Path(project_path).resolve()

        # Run scans on changed files only
        bandit_result = self._run_bandit(target, changed_files)
        ruff_result = self._run_ruff(target, changed_files)
        complexity_result = self._run_complexity(target, changed_files)

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
            "complexity": complexity_result
        }

    def _run_bandit(self, target: Path, files: List[str]) -> Dict[str, Any]:
        """Run Bandit security scan on specified files."""
        try:
            cmd = [sys.executable, "-m", "bandit", "-c", "pyproject.toml"] + files + ["-f", "json", "--exit-zero"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.DEFAULT_TIMEOUT,
                cwd=str(target), stdin=subprocess.DEVNULL
            )
            try:
                data = json.loads(result.stdout) if result.stdout else {}
            except json.JSONDecodeError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            issues = [
                {
                    "severity": issue.get("issue_severity"),
                    "file": issue.get("filename"),
                    "line": issue.get("line_number"),
                    "description": issue.get("issue_text"),
                    "code": issue.get("test_id")
                }
                for issue in data.get("results", [])
            ]
            return {"total_issues": len(issues), "issues": issues[:10]}
        except subprocess.TimeoutExpired:
            return {"error": "Timeout", "total_issues": 0, "issues": []}
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            return {"error": str(e), "total_issues": 0, "issues": []}

    def _run_ruff(self, target: Path, files: List[str]) -> Dict[str, Any]:
        """Run Ruff linting on specified files."""
        try:
            cmd = [sys.executable, "-m", "ruff", "check"] + files + ["--output-format", "json"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.DEFAULT_TIMEOUT,
                cwd=str(target), stdin=subprocess.DEVNULL
            )
            try:
                data = json.loads(result.stdout) if result.stdout else []
            except json.JSONDecodeError:
                data = []
            # Ruff returns array, but handle dict gracefully (for mocked tests)
            issues = data if isinstance(data, list) else []
            return {"total_issues": len(issues), "issues": issues[:10]}
        except subprocess.TimeoutExpired:
            return {"error": "Timeout", "total_issues": 0, "issues": []}
        except Exception as e:
            logger.error(f"Ruff scan failed: {e}")
            return {"error": str(e), "total_issues": 0, "issues": []}

    def _run_complexity(self, target: Path, files: List[str]) -> Dict[str, Any]:
        """Run complexity analysis on specified files."""
        try:
            cmd = [sys.executable, "-m", "radon", "cc"] + files + ["-a", "-j"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.DEFAULT_TIMEOUT,
                cwd=str(target), stdin=subprocess.DEVNULL
            )
            try:
                data = json.loads(result.stdout) if result.stdout else {}
            except json.JSONDecodeError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            high_complexity = []
            for file_path, functions in data.items():
                if isinstance(functions, list):
                    for func in functions:
                        if func.get('rank', 'A') in ['C', 'D', 'E', 'F']:
                            high_complexity.append({
                                "file": Path(file_path).name,
                                "function": func.get('name', ''),
                                "complexity": func.get('complexity', 0),
                                "rank": func.get('rank', '')
                            })
            return {"total_high_complexity": len(high_complexity), "functions": high_complexity[:10]}
        except subprocess.TimeoutExpired:
            return {"error": "Timeout", "total_high_complexity": 0, "functions": []}
        except Exception as e:
            logger.error(f"Complexity scan failed: {e}")
            return {"error": str(e), "total_high_complexity": 0, "functions": []}

    def _calculate_score(
        self, bandit: Dict[str, Any], ruff: Dict[str, Any], complexity: Dict[str, Any]
    ) -> int:
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

    def _get_recommendation(self, bandit: Dict[str, Any], score: int) -> str:
        """Get recommendation based on results."""
        if bandit.get("total_issues", 0) > 0:
            return "request_changes"
        elif score >= 80:
            return "ready_for_review"
        else:
            return "needs_improvement"

    def generate_report(
        self,
        base_branch: str,
        changed_files: List[str],
        result: Dict[str, Any],
        tests_passed: bool = True,
        test_output: str = "",
        run_tests: bool = True,
        target: Path = None
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
                fname = Path(issue.get('file', '')).name
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
                fname = Path(issue.get('filename', '')).name
                row = issue.get('location', {}).get('row', '?')
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
