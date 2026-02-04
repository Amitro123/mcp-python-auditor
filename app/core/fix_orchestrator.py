"""Interactive Auto-Fix Orchestrator for code quality remediation."""

import logging
from pathlib import Path
from typing import Any

from app.tools.code_editor_tool import CodeEditorTool
from app.tools.deadcode_tool import DeadcodeTool
from app.tools.git_tool import GitTool

logger = logging.getLogger(__name__)


# ANSI color codes
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class AutoFixOrchestrator:
    """Interactive orchestrator for automatic code quality fixes."""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path)
        self.deadcode_tool = DeadcodeTool()
        self.editor_tool = CodeEditorTool()
        self.git_tool = GitTool()

    def run_cleanup_mission(self, interactive: bool = True):
        """Main cleanup mission: identify and fix dead code.

        Args:
            interactive: If True, ask user before each fix

        """
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}🚀 AUTO-FIX ORCHESTRATOR{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.RESET}")
        print(f"📂 Project: {self.project_path.absolute()}\n")

        # 1. Run analysis
        print(f"{Colors.BLUE}🔍 Scanning for dead code...{Colors.RESET}")
        report = self.deadcode_tool.analyze(self.project_path)

        # 2. Classify and extract fixes
        fixes = self._classify_fixes(report)

        if not fixes:
            print(f"\n{Colors.GREEN}✅ No dead code found. Project is clean!{Colors.RESET}\n")
            return {"status": "clean", "fixes_applied": 0}

        # 3. Display summary
        self._display_summary(fixes)

        # 4. Apply fixes (with user confirmation if interactive)
        applied_fixes = []
        skipped_fixes = []

        for fix in fixes:
            if interactive:
                if self._prompt_user(fix):
                    result = self._apply_fix(fix)
                    if result["status"] == "success":
                        applied_fixes.append(fix)
                    else:
                        print(f"   {Colors.RED}❌ Failed: {result.get('error')}{Colors.RESET}")
                        skipped_fixes.append(fix)
                else:
                    skipped_fixes.append(fix)
            # Auto mode - only apply low risk fixes
            elif fix["risk"] == "LOW":
                result = self._apply_fix(fix)
                if result["status"] == "success":
                    applied_fixes.append(fix)
            else:
                skipped_fixes.append(fix)

        # 5. Summary report
        self._display_results(applied_fixes, skipped_fixes)

        return {
            "status": "success",
            "fixes_applied": len(applied_fixes),
            "fixes_skipped": len(skipped_fixes),
            "files_modified": list({f["file"] for f in applied_fixes}),
        }

    def _classify_fixes(self, report: dict) -> list[dict]:
        """Classify and extract fixable issues with risk levels.

        Returns sorted list of fixes (descending by line number).
        """
        fixes = []

        # Low Risk: Unused Imports
        for item in report.get("unused_imports", []):
            fixes.append(
                {
                    "type": "unused_import",
                    "risk": "LOW",
                    "file": item["file"],
                    "line": item["line"],
                    "name": item.get("name", ""),
                    "message": item.get("message", ""),
                }
            )

        # High Risk: Unused Functions (definition line only)
        for item in report.get("dead_functions", []):
            fixes.append(
                {
                    "type": "unused_function",
                    "risk": "HIGH",
                    "file": item["file"],
                    "line": item["line"],
                    "name": item.get("name", ""),
                    "message": item.get("message", ""),
                }
            )

        # High Risk: Unused Variables
        for item in report.get("dead_variables", []):
            fixes.append(
                {
                    "type": "unused_variable",
                    "risk": "HIGH",
                    "file": item["file"],
                    "line": item["line"],
                    "name": item.get("name", ""),
                    "message": item.get("message", ""),
                }
            )

        # Sort by file and line (descending) - CRITICAL for preserving line numbers!
        fixes.sort(key=lambda x: (x["file"], -x["line"]))

        return fixes

    def _display_summary(self, fixes: list[dict]):
        """Display a summary of detected issues."""
        low_risk = sum(1 for f in fixes if f["risk"] == "LOW")
        high_risk = sum(1 for f in fixes if f["risk"] == "HIGH")

        print(f"\n{Colors.YELLOW}⚠️  Found {len(fixes)} fixable issue(s):{Colors.RESET}")
        print(f"   {Colors.GREEN}[LOW RISK]{Colors.RESET}  Unused Imports: {low_risk}")
        print(f"   {Colors.RED}[HIGH RISK]{Colors.RESET} Functions/Variables: {high_risk}")
        print()

    def _prompt_user(self, fix: dict) -> bool:
        """Display fix details and prompt user for confirmation.

        Returns True if user confirms, False otherwise.
        """
        # Read file to show context
        file_path = self.project_path / fix["file"]
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Get context (2 lines before/after)
            line_idx = fix["line"] - 1  # Convert to 0-indexed
            start = max(0, line_idx - 2)
            end = min(len(lines), line_idx + 3)

            # Color code based on risk
            risk_color = Colors.GREEN if fix["risk"] == "LOW" else Colors.RED
            risk_label = f"{risk_color}[{fix['risk']} RISK]{Colors.RESET}"

            print(f"\n{Colors.BOLD}{'─' * 70}{Colors.RESET}")
            print(f"{risk_label} {fix['type'].replace('_', ' ').title()}")
            print(f"📄 File: {Colors.CYAN}{fix['file']}{Colors.RESET}")
            print(f"📍 Line: {Colors.YELLOW}{fix['line']}{Colors.RESET}")
            print(f"🏷️  Name: {Colors.MAGENTA}{fix['name']}{Colors.RESET}")
            print(f"\n{Colors.BOLD}Context:{Colors.RESET}")

            for i in range(start, end):
                line_num = i + 1
                line_content = lines[i].rstrip()

                if i == line_idx:
                    # Highlight the target line
                    print(f"  {Colors.RED}→ {line_num:4d} | {line_content}{Colors.RESET}")
                else:
                    print(f"    {line_num:4d} | {line_content}")

            # Prompt
            print(f"\n{Colors.BOLD}Delete this line?{Colors.RESET} ", end="")
            response = input(f"[{Colors.GREEN}y{Colors.RESET}/{Colors.RED}N{Colors.RESET}]: ").strip().lower()

            return response == "y"

        except Exception as e:
            logger.exception(f"Failed to read {file_path}: {e}")
            return False

    def _apply_fix(self, fix: dict) -> dict[str, Any]:
        """Apply a single fix using CodeEditorTool."""
        file_path = self.project_path / fix["file"]

        print(f"   {Colors.BLUE}🛠️  Applying fix...{Colors.RESET}", end=" ")

        result = self.editor_tool.delete_line(file_path=str(file_path), line_number=fix["line"])

        if result["status"] == "success":
            print(f"{Colors.GREEN}✓ Done{Colors.RESET}")

        return result

    def _display_results(self, applied: list[dict], skipped: list[dict]):
        """Display final results summary."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}📊 MISSION COMPLETE{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.RESET}")

        print(f"\n{Colors.GREEN}✅ Fixes Applied: {len(applied)}{Colors.RESET}")
        if applied:
            files_modified = {f["file"] for f in applied}
            for file in sorted(files_modified):
                count = sum(1 for f in applied if f["file"] == file)
                print(f"   • {file} ({count} fix{'es' if count > 1 else ''})")

        print(f"\n{Colors.YELLOW}⏭️  Fixes Skipped: {len(skipped)}{Colors.RESET}")

        if applied:
            print(f"\n{Colors.MAGENTA}💡 TIP: Backup files created with .bak extension{Colors.RESET}")
            print(f"{Colors.MAGENTA}    To restore: use CodeEditorTool.restore_backup(){Colors.RESET}")

        print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 70}{Colors.RESET}\n")


def main():
    """Main entry point for CLI usage."""
    import sys

    # Parse args
    interactive = "--auto" not in sys.argv
    project_path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--auto" else "."

    orchestrator = AutoFixOrchestrator(project_path=project_path)
    result = orchestrator.run_cleanup_mission(interactive=interactive)

    # Exit code based on result
    sys.exit(0 if result["fixes_applied"] >= 0 else 1)


if __name__ == "__main__":
    main()
