"""Console and Markdown report generation for audit results.

Provides both Rich console output and markdown report generation.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from app.core.grading import get_letter_grade, get_score_color, get_score_emoji

# Tool categories for display organization
TOOL_CATEGORIES = {
    "security": ["bandit", "secrets", "pip-audit"],
    "quality": ["ruff", "duplication", "deadcode", "cleanup"],
    "analysis": ["coverage", "complexity", "typing"],
}

CATEGORY_EMOJIS = {
    "security": "\U0001f512",  # lock
    "quality": "\U0001f9f9",  # broom
    "analysis": "\U0001f4ca",  # chart
}


class ConsoleReporter:
    """Handles Rich console output for audit results."""

    def __init__(self, console: Console | None = None):
        """Initialize console reporter.

        Args:
            console: Rich Console instance. Creates new one if not provided.
        """
        self.console = console or Console()

    def print_summary_table(
        self,
        data: dict[str, Any],
        timings: dict[str, float],
        score: int,
        completed: int,
        failed: int,
        failed_tools: list[tuple[str, str]] | None = None,
        comprehensive: bool = False,
    ) -> None:
        """Print summary table to console.

        Args:
            data: Tool results dictionary
            timings: Tool timing dictionary
            score: Final audit score
            completed: Number of completed tools
            failed: Number of failed tools
            failed_tools: List of (tool_name, reason) tuples
            comprehensive: Show all ruff issues, not just critical
        """
        table = Table(title="Audit Summary")
        table.add_column("Category", style="cyan")
        table.add_column("Tool")
        table.add_column("Result", justify="right")
        table.add_column("Duration", justify="right", style="dim")
        table.add_column("Status", justify="center")

        for cat, tools in TOOL_CATEGORIES.items():
            for tool in tools:
                tool_data = data.get(tool, {})
                value = tool_data.get("total", tool_data.get("percent", tool_data.get("grade", "-")))

                if tool_data.get("skipped"):
                    value = "-"
                elif tool == "ruff" and comprehensive:
                    all_issues = tool_data.get("all", 0)
                    total = tool_data.get("total", 0)
                    if all_issues > total:
                        value = f"{total} ({all_issues} total)"

                dur = timings.get(tool, 0)
                dur_str = f"{dur:.1f}s" if dur > 0 else "-"

                if tool_data.get("error"):
                    status = "[red]ERR[/]"
                elif tool_data.get("skipped"):
                    status = "[dim]skip[/]"
                else:
                    status = "[green]OK[/]"

                table.add_row(cat, tool, str(value), dur_str, status)

        self.console.print(table)

        # Print score
        total_tools = completed + failed
        color = get_score_color(score)
        grade = get_letter_grade(score)
        self.console.print(f"\n[bold {color}]Score: {score}/100 ({grade})[/] [dim](completed: {completed}/{total_tools})[/]")

        if failed_tools:
            failed_summary = ", ".join(f"{t} ({r})" for t, r in failed_tools)
            self.console.print(f"[red]Failed: {failed_summary}[/]")

    def print_samples(self, data: dict[str, Any]) -> None:
        """Print sample issues from each tool.

        Args:
            data: Tool results dictionary with samples
        """
        self.console.print("[bold]Sample Issues:[/]")

        for tool_name, tool_data in data.items():
            samples = tool_data.get("samples", [])
            if not samples:
                continue

            self.console.print(f"\n  [cyan]{tool_name}[/]:")
            for sample in samples[:3]:
                self._print_sample(sample)

        self.console.print()

    def _print_sample(self, sample: dict[str, Any]) -> None:
        """Print a single sample issue.

        Args:
            sample: Sample issue dictionary
        """
        if "msg" in sample:
            # Ruff/bandit format
            file_loc = f"{sample.get('file', '')}:{sample.get('line', '')}"
            code = sample.get("code", "")
            msg = sample.get("msg", "")
            self.console.print(f"    {file_loc} [{code}] {msg}")
        elif "type" in sample:
            # Secrets format
            file_loc = f"{sample.get('file', '')}:{sample.get('line', '')}"
            secret_type = sample.get("type", "")
            self.console.print(f"    {file_loc} [{secret_type}]")
        elif "package" in sample:
            # pip-audit format
            pkg = sample.get("package", "")
            version = sample.get("version", "")
            vuln_id = sample.get("vuln_id", "")
            self.console.print(f"    {pkg} {version} - {vuln_id}")
        else:
            self.console.print(f"    {sample}")

    def print_penalties(self, penalties: list[str]) -> None:
        """Print penalty list.

        Args:
            penalties: List of penalty strings
        """
        for penalty in penalties:
            self.console.print(f"  [yellow]{penalty}[/]")


class MarkdownReporter:
    """Generates markdown reports for audit results."""

    def generate_report(
        self,
        path: Path,
        data: dict[str, Any],
        timings: dict[str, float],
        score: int,
        ai_analysis: str | None = None,
        old_score: int | None = None,
        changed_files: list[str] | None = None,
    ) -> str:
        """Generate markdown report.

        Args:
            path: Project path
            data: Tool results dictionary
            timings: Tool timing dictionary
            score: Final audit score
            ai_analysis: Optional AI analysis text
            old_score: Optional previous score (for fix comparisons)
            changed_files: Optional list of modified files

        Returns:
            Markdown report string
        """
        score_emoji = get_score_emoji(score)
        grade = get_letter_grade(score)
        completed = sum(1 for d in data.values() if not d.get("skipped") and not d.get("error"))
        total = len(data)

        lines = [
            f"# {score_emoji} Audit Report: {path.name}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Score:** {score}/100 ({grade})",
            f"**Tools:** {completed}/{total} completed",
        ]

        # Before/after scores if fixes were applied
        if old_score is not None and old_score != score:
            diff = score - old_score
            sign = "+" if diff > 0 else ""
            lines.append(f"**Improvement:** {old_score} -> {score} ({sign}{diff} points)")

        # Changed files summary
        if changed_files:
            lines.append(f"**Files Fixed:** {len(changed_files)}")

        lines.extend(["", "---", ""])

        # Add Critical Security Issues section if any security issues found
        security_issues = self._collect_security_issues(data)
        if security_issues:
            lines.extend(
                [
                    "## \U0001f6a8 Critical Security Issues",
                    "",
                    "> **Action Required:** The following security issues were detected and should be addressed immediately.",
                    "",
                ]
            )
            for issue in security_issues:
                lines.append(issue)
            lines.extend(["", "---", ""])

        lines.extend(["## Results", ""])

        # Results by category
        for cat, tools in TOOL_CATEGORIES.items():
            cat_emoji = CATEGORY_EMOJIS.get(cat, "\U0001f4cb")  # clipboard
            lines.append(f"### {cat_emoji} {cat.title()}")
            lines.append("")

            for tool in tools:
                tool_data = data.get(tool, {})
                value = tool_data.get("total", tool_data.get("percent", tool_data.get("grade", "-")))
                dur = timings.get(tool, 0)

                # Status indicator
                if tool_data.get("skipped"):
                    status = "\u23ed\ufe0f skipped"  # skip forward
                elif tool_data.get("error"):
                    status = f"\u274c {tool_data.get('error')}"  # red X
                elif value in {0, "-"} or value in ["A", "B"]:
                    status = "\u2705"  # check mark
                else:
                    status = "\u26a0\ufe0f"  # warning

                lines.append(f"- **{tool}**: {value} ({dur:.1f}s) {status}")

                # Add sample issues
                samples = tool_data.get("samples", [])
                lines.extend(self._format_samples(samples))

            lines.append("")

        # AI Analysis section
        if ai_analysis:
            lines.extend(["---", "", "## \U0001f916 AI Analysis", "", ai_analysis, ""])

        # Changed files detail
        if changed_files and len(changed_files) > 0:
            lines.extend(["---", "", "## \U0001f527 Files Modified", ""])
            for f in changed_files[:10]:
                lines.append(f"- `{f}`")
            if len(changed_files) > 10:
                lines.append(f"- ... and {len(changed_files) - 10} more")
            lines.append("")

        # Footer
        lines.extend(["---", "", "*Generated by Python Audit CLI*"])

        return "\n".join(lines)

    def _collect_security_issues(self, data: dict[str, Any]) -> list[str]:
        """Collect all security issues from bandit, secrets, and pip-audit tools.

        Args:
            data: Tool results dictionary

        Returns:
            List of formatted markdown lines describing security issues
        """
        lines = []

        # Collect bandit issues (code security vulnerabilities)
        bandit_data = data.get("bandit", {})
        bandit_samples = bandit_data.get("samples", [])
        bandit_total = bandit_data.get("total", 0)

        if bandit_total > 0 or bandit_samples:
            lines.append("### 🔓 Code Security Issues (Bandit)")
            lines.append("")
            if bandit_samples:
                for sample in bandit_samples[:10]:  # Show up to 10 issues
                    file_path = sample.get("file", "")
                    # Shorten path for readability
                    if "\\" in file_path or "/" in file_path:
                        parts = file_path.replace("\\", "/").split("/")
                        file_path = "/".join(parts[-3:]) if len(parts) > 3 else "/".join(parts)
                    line_num = sample.get("line", "?")
                    code = sample.get("code", "")
                    msg = sample.get("msg", "")
                    severity = sample.get("severity", "")
                    sev_icon = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "⚪"
                    lines.append(f"- {sev_icon} `{file_path}:{line_num}` **[{code}]** {msg}")
                if bandit_total > 10:
                    lines.append(f"- *... and {bandit_total - 10} more issues*")
            else:
                lines.append(f"- {bandit_total} security issue(s) detected")
            lines.append("")

        # Collect secrets issues (exposed credentials)
        secrets_data = data.get("secrets", {})
        secrets_samples = secrets_data.get("samples", [])
        secrets_total = secrets_data.get("total", 0)

        if secrets_total > 0 or secrets_samples:
            lines.append("### 🔑 Exposed Secrets")
            lines.append("")
            lines.append("> ⚠️ **WARNING:** These files may contain sensitive credentials that should NOT be committed to version control.")
            lines.append("")
            if secrets_samples:
                for sample in secrets_samples[:10]:  # Show up to 10 secrets
                    file_path = sample.get("file", "")
                    line_num = sample.get("line", "?")
                    secret_type = sample.get("type", "Unknown Secret")
                    lines.append(f"- 🚨 `{file_path}:{line_num}` — **{secret_type}**")
                if secrets_total > 10:
                    lines.append(f"- *... and {secrets_total - 10} more exposed secrets*")
            else:
                lines.append(f"- {secrets_total} exposed secret(s) detected")
            lines.append("")

        # Collect pip-audit vulnerabilities
        pip_audit_data = data.get("pip-audit", {})
        pip_samples = pip_audit_data.get("samples", [])
        pip_total = pip_audit_data.get("total", 0)

        if pip_total > 0 or pip_samples:
            lines.append("### 📦 Vulnerable Dependencies")
            lines.append("")
            if pip_samples:
                for sample in pip_samples[:10]:
                    pkg = sample.get("package", "")
                    version = sample.get("version", "")
                    vuln_id = sample.get("vuln_id", "")
                    fix_version = sample.get("fix_version", "")
                    fix_info = f" → upgrade to {fix_version}" if fix_version else ""
                    lines.append(f"- ⚠️ `{pkg}` {version} — **{vuln_id}**{fix_info}")
                if pip_total > 10:
                    lines.append(f"- *... and {pip_total - 10} more vulnerabilities*")
            else:
                lines.append(f"- {pip_total} vulnerable package(s) detected")
            lines.append("")

        return lines

    def _format_samples(self, samples: list[dict[str, Any]], max_samples: int = 5) -> list[str]:
        """Format sample issues as markdown list items.

        Args:
            samples: List of sample dictionaries
            max_samples: Maximum number of samples to include

        Returns:
            List of markdown lines
        """
        lines = []
        for sample in samples[:max_samples]:
            if "code" in sample:
                # Ruff/bandit format - show relative path
                file_path = sample.get("file", "")
                # Extract just filename or relative path
                if "\\" in file_path or "/" in file_path:
                    parts = file_path.replace("\\", "/").split("/")
                    # Keep last 2-3 parts for context
                    file_path = "/".join(parts[-3:]) if len(parts) > 3 else "/".join(parts)
                file_loc = f"{file_path}:{sample.get('line', '')}"
                code = sample.get("code", "")
                msg = sample.get("msg", "")[:80]
                lines.append(f"  - `{file_loc}` **[{code}]** {msg}")
            elif "type" in sample:
                # Secrets format - show file and type clearly
                file_path = sample.get("file", "")
                file_loc = f"{file_path}:{sample.get('line', '')}"
                secret_type = sample.get("type", "")
                lines.append(f"  - `{file_loc}` **[{secret_type}]**")
            elif "package" in sample:
                # pip-audit format
                pkg = sample.get("package", "")
                version = sample.get("version", "")
                vuln_id = sample.get("vuln_id", "")
                lines.append(f"  - `{pkg}` {version} - **{vuln_id}**")

        # Show count of remaining items
        if len(samples) > max_samples:
            lines.append(f"  - *... and {len(samples) - max_samples} more*")

        return lines
