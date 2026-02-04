"""Interactive CLI runner for audits.

Provides a question-based interface for running audits with AI insights.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.auto_fixer import AutoFixer, display_fix_suggestions
from app.core.console_reporter import MarkdownReporter
from app.core.llm_client import call_llm


class InteractiveRunner:
    """Runs interactive audit sessions with user prompts."""

    def __init__(self):
        """Initialize interactive runner."""
        self.markdown_reporter = MarkdownReporter()

    def run(self) -> None:
        """Run the interactive audit session."""
        self._print_header()

        # Get project path
        target = self._prompt_for_path()
        if target is None:
            return

        # Get audit mode
        fast, pr = self._prompt_for_mode()

        # Run audit
        print()
        data = self._run_audit(target, fast, pr)

        if "error" in data:
            print(f"\nError: {data['error']}")
            return

        self._print_results(data)

        # AI analysis (optional)
        ai_analysis = self._prompt_for_ai_analysis(data)

        # Auto-fixer
        new_data = self._run_auto_fix(target, data, ai_analysis, fast, pr)
        if new_data:
            data = new_data

        # Save report
        self._save_report(target, data, ai_analysis)

        print("\nDone!")

    def _print_header(self) -> None:
        """Print interactive mode header."""
        print("\n" + "=" * 50)
        print("  Python Audit - Interactive Mode")
        print("=" * 50 + "\n")

    def _prompt_for_path(self) -> Path | None:
        """Prompt user for project path.

        Returns:
            Resolved Path or None if invalid
        """
        path_input = input("Enter project path [.]: ").strip() or "."
        target = Path(path_input).resolve()

        if not target.exists():
            print(f"Error: Path '{path_input}' does not exist.")
            return None

        return target

    def _prompt_for_mode(self) -> tuple[bool, bool]:
        """Prompt user for audit mode.

        Returns:
            Tuple of (fast, pr) booleans
        """
        print("\nAudit mode:")
        print("  1. Full audit (includes coverage, pip-audit, secrets)")
        print("  2. Fast audit (skip slow tools) [recommended]")
        print("  3. PR mode (only changed files vs origin/main)")

        mode = input("Select [2]: ").strip() or "2"
        fast = mode == "2"
        pr = mode == "3"

        return fast, pr

    def _run_audit(self, target: Path, fast: bool, pr: bool) -> dict[str, Any]:
        """Run the audit and return results.

        Args:
            target: Project path
            fast: Skip slow tools
            pr: PR mode (only changed files)

        Returns:
            Audit results dictionary
        """
        # Import here to avoid circular imports
        from audit import run_audit_internal

        return run_audit_internal(target, fast, pr)

    def _print_results(self, data: dict[str, Any]) -> None:
        """Print human-readable audit results.

        Args:
            data: Audit results dictionary
        """
        print(f"\n{'=' * 50}")
        print(f"  Audit Results: {data.get('path', 'unknown')}")
        print(f"  Score: {data.get('score', 0)}/100 ({data.get('grade', '?')})")
        print(f"{'=' * 50}\n")

        tools = data.get("tools", {})

        for tool, result in tools.items():
            total = result.get("total", result.get("percent", result.get("grade", "-")))

            if tool in ("coverage", "typing"):
                status = "OK" if (isinstance(total, int) and total >= 50) else "!"
            elif tool == "complexity":
                status = "OK" if total in ["A", "B", "?", "-"] else "!"
            else:
                ok_values = [0, "-"]
                is_ok = total in ok_values or (isinstance(total, int) and total <= 10)
                status = "OK" if is_ok else "!"

            print(f"  [{status}] {tool:12} : {total}")

    def _prompt_for_ai_analysis(self, data: dict[str, Any]) -> str | None:
        """Prompt user for optional AI analysis.

        Args:
            data: Audit results dictionary

        Returns:
            AI analysis text or None
        """
        if input("\nAI analysis? [y/N]: ").strip().lower() != "y":
            return None

        provider = input("[1] Groq [2] Ollama: ").strip() or "1"

        # Build detailed issue context
        issues_detail = []
        for tool, result in data.get("tools", {}).items():
            total = result.get("total", result.get("percent", 0))
            if not isinstance(total, int) or total <= 0:
                continue

            detail = f"{tool}: {total}"
            samples = result.get("samples", [])
            if samples:
                sample_strs = []
                for s in samples[:3]:
                    if "msg" in s:
                        sample_strs.append(f"  - {s.get('file', '')}:{s.get('line', '')} {s.get('msg', '')[:50]}")
                    elif "package" in s:
                        sample_strs.append(f"  - {s.get('package', '')} {s.get('vuln_id', '')}")
                if sample_strs:
                    detail += "\n" + "\n".join(sample_strs)
            issues_detail.append(detail)

        issues_str = "\n".join(issues_detail) if issues_detail else "No major issues"

        try:
            print("\nAnalyzing issues...")
            prompt = f"""Score: {data["score"]}/100

Issues found:
{issues_str}

Analyze these issues and suggest specific fixes:
1. What are the most critical problems?
2. What specific commands or actions would fix them?
3. Priority order for fixes?

Keep under 200 words. Be specific."""

            analysis = call_llm(prompt, provider)
            print(f"\n{analysis}")
            return analysis

        except Exception as e:
            print(f"AI error: {e}")
            return None

    def _run_auto_fix(
        self,
        target: Path,
        data: dict[str, Any],
        ai_analysis: str | None,
        fast: bool,
        pr: bool,
    ) -> dict[str, Any] | None:
        """Run auto-fixer with user confirmation.

        Args:
            target: Project path
            data: Current audit results
            ai_analysis: Optional AI analysis
            fast: Fast mode flag
            pr: PR mode flag

        Returns:
            New audit data if fixes were applied, None otherwise
        """
        fixer = AutoFixer(target)
        fixes = fixer.detect_fixes(data)

        # Print deadcode info
        dead = data.get("tools", {}).get("deadcode", {}).get("total", 0)
        if dead > 0:
            has_penalty = dead > 150
            penalty_note = "(-10pt penalty)" if has_penalty else "(no penalty, < 150)"
            print(f"\n[Info] Deadcode: {dead} items {penalty_note}")

        display_fix_suggestions(fixes, data.get("score", 0), ai_analysis)

        if not fixes:
            return None

        if input("\nApply fixes? [y/N]: ").strip().lower() != "y":
            return None

        print("\n[Applying fixes...]")
        files_changed = fixer.apply_all_fixes(fixes)

        if files_changed:
            print("\n  Re-running audit...")
            new_data = self._run_audit(target, fast=fast, pr=pr)

            if "error" not in new_data:
                old_score = data.get("score", 0)
                new_score = new_data.get("score", 0)
                diff = new_score - old_score
                print(f"\n  Score: {old_score} -> {new_score} ({'+' if diff >= 0 else ''}{diff})")
                self._print_results(new_data)
                return new_data

        return None

    def _save_report(
        self,
        target: Path,
        data: dict[str, Any],
        ai_analysis: str | None = None,
    ) -> None:
        """Save markdown report to file.

        Args:
            target: Project path
            data: Audit results
            ai_analysis: Optional AI analysis
        """
        from rich.console import Console

        console = Console()

        # Create Results-like object for report
        report_content = self.markdown_reporter.generate_report(
            path=target,
            data=data.get("tools", {}),
            timings=data.get("timings", {}),
            score=data.get("score", 0),
            ai_analysis=ai_analysis,
        )

        report_name = f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        Path(report_name).write_text(report_content, encoding="utf-8")
        console.print(f"\n[green]Report saved to {report_name}[/]")


def interactive_mode() -> None:
    """Entry point for interactive mode (backward compatibility)."""
    runner = InteractiveRunner()
    runner.run()
