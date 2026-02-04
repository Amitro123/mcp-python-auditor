"""Auto-fixer for audit issues.

Detects fixable issues and applies automated fixes with accurate score predictions.
"""

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FixSuggestion:
    """Represents a suggested fix with score impact prediction."""

    name: str
    description: str
    gain: int = 0
    note: str = ""
    cmd: list[str] | None = None
    action: str | None = None
    packages: list[str] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)


class AutoFixer:
    """Detects and applies automated fixes for audit issues."""

    def __init__(self, project_path: Path, verbose: bool = True):
        """Initialize AutoFixer.

        Args:
            project_path: Path to the project root
            verbose: Print progress messages
        """
        self.project_path = Path(project_path).resolve()
        self.verbose = verbose

    def detect_fixes(self, audit_data: dict[str, Any]) -> list[FixSuggestion]:
        """Detect all available fixes based on audit results.

        Args:
            audit_data: Audit results with tool data

        Returns:
            List of fix suggestions
        """
        tools = audit_data.get("tools", audit_data)
        fixes = []

        # Detect fixes for each tool type
        if ruff_fix := self._detect_ruff_fixes(tools):
            fixes.append(ruff_fix)

        if pip_fix := self._detect_pip_fixes(tools):
            fixes.append(pip_fix)

        if bandit_fix := self._detect_bandit_fixes(tools):
            fixes.append(bandit_fix)

        if cleanup_fix := self._detect_cleanup_fixes(tools):
            fixes.append(cleanup_fix)

        if test_fix := self._detect_test_fixes(tools):
            fixes.append(test_fix)

        return fixes

    def _detect_ruff_fixes(self, tools: dict[str, Any]) -> FixSuggestion | None:
        """Detect Ruff auto-fixable issues.

        Args:
            tools: Tool results dictionary

        Returns:
            Fix suggestion or None if no fixes available
        """
        ruff_data = tools.get("ruff", {})
        ruff_total = ruff_data.get("total", 0)

        if ruff_total <= 0:
            return None

        # Calculate current and estimated penalties
        current_penalty = min((ruff_total - 20) // 10, 20) if ruff_total > 20 else 0

        # Ruff --fix with E,F,I rules typically fixes only ~5% of issues
        estimated_fixed = max(1, int(ruff_total * 0.05))
        estimated_after = ruff_total - estimated_fixed
        new_penalty = min((estimated_after - 20) // 10, 20) if estimated_after > 20 else 0
        gain = current_penalty - new_penalty

        # Build user-facing note
        if gain > 0:
            note = f"penalty {current_penalty} -> {new_penalty}"
        else:
            issues_needed = ((current_penalty + 1) * 10 + 20) - ruff_total
            note = f"no score gain (need to fix {abs(issues_needed)} more issues for +1pt)"

        return FixSuggestion(
            name="Ruff",
            description=f"Fix ~{estimated_fixed} of {ruff_total} issues (E/F/I auto-fixable rules)",
            gain=gain,
            note=note,
            cmd=[sys.executable, "-m", "ruff", "check", "--fix", "--select", "E,F,I", "."],
        )

    def _detect_pip_fixes(self, tools: dict[str, Any]) -> FixSuggestion | None:
        """Detect pip-audit vulnerability fixes.

        Args:
            tools: Tool results dictionary

        Returns:
            Fix suggestion or None if no fixes available
        """
        pip_data = tools.get("pip-audit", {})
        vulns = pip_data.get("total", 0)

        if vulns <= 0:
            return None

        # Extract vulnerable packages
        packages = []
        for sample in pip_data.get("samples", []):
            pkg = sample.get("package", "")
            if pkg:
                packages.append(pkg)

        if not packages:
            return None

        # Calculate penalty: min(vulns * 5, 10)
        current_penalty = min(vulns * 5, 10)
        pkg_display = ", ".join(packages[:3])
        if len(packages) > 3:
            pkg_display += "..."

        return FixSuggestion(
            name="pip-audit",
            description=f"Upgrade {len(packages)} packages: {pkg_display}",
            gain=current_penalty,
            note=f"removes {current_penalty}pt penalty",
            action="pip-upgrade",
            packages=packages,
        )

    def _detect_bandit_fixes(self, tools: dict[str, Any]) -> FixSuggestion | None:
        """Detect Bandit security fixes (B101 assert statements).

        Args:
            tools: Tool results dictionary

        Returns:
            Fix suggestion or None if no fixes available
        """
        bandit_data = tools.get("bandit", {})
        bandit_total = bandit_data.get("total", bandit_data.get("total_issues", 0))

        if bandit_total <= 0:
            return None

        if bandit_data.get("status") not in ["issues_found", "clean", None]:
            return None

        # Get issues list
        issues_list = bandit_data.get("samples", bandit_data.get("issues", []))
        fixable_issues = []

        for issue in issues_list:
            issue_id = issue.get("code", issue.get("test_id", ""))
            # Only auto-fix safe patterns (assert usage)
            if issue_id == "B101":
                fixable_issues.append(
                    {
                        "file": issue.get("file", issue.get("filename", "")),
                        "line": issue.get("line", issue.get("line_number", 0)),
                        "code": issue_id,
                        "text": issue.get("msg", issue.get("issue_text", "")),
                    }
                )

        if not fixable_issues:
            return None

        # Current penalty is 10 if bandit has issues
        current_penalty = 10
        gain = current_penalty if len(fixable_issues) == bandit_total else current_penalty // 2

        return FixSuggestion(
            name="Bandit Security",
            description=f"Fix {len(fixable_issues)} security issue(s) (assert statements)",
            gain=gain,
            note=f"removes {gain}pt security penalty",
            action="bandit-fix",
            issues=fixable_issues,
        )

    def _detect_cleanup_fixes(self, tools: dict[str, Any]) -> FixSuggestion | None:
        """Detect cleanup (cache directory) fixes.

        Args:
            tools: Tool results dictionary

        Returns:
            Fix suggestion or None if no fixes available
        """
        cleanup_data = tools.get("cleanup", {})
        cleanup_total = cleanup_data.get("total", 0)

        if cleanup_total <= 0:
            return None

        # Penalty only if > 50 dirs
        has_penalty = cleanup_total > 50
        gain = 5 if has_penalty else 0
        note = "removes 5pt penalty" if gain > 0 else "no penalty (< 50 dirs)"

        return FixSuggestion(
            name="Cleanup",
            description=f"Remove {cleanup_total} items (cache dirs, temp files, old reports)",
            gain=gain,
            note=note,
            action="cleanup",
        )

    def _detect_test_fixes(self, tools: dict[str, Any]) -> FixSuggestion | None:
        """Detect test coverage improvements.

        Args:
            tools: Tool results dictionary

        Returns:
            Fix suggestion or None if no fixes available
        """
        coverage_data = tools.get("coverage", {})
        coverage_pct = coverage_data.get("percent", coverage_data.get("coverage_percent", 0))

        if coverage_pct >= 50:
            return None

        # Import test generator
        from app.tools.test_generator import find_untested_files

        untested_files = find_untested_files(self.project_path)
        if not untested_files:
            return None

        # Estimate coverage improvement (~2-3% per test file)
        estimated_gain_pct = min(len(untested_files) * 2, 50 - coverage_pct)

        # Calculate score gain based on coverage penalty formula
        current_penalty = 30 if coverage_pct < 50 else (15 if coverage_pct < 70 else 0)
        new_coverage = min(coverage_pct + estimated_gain_pct, 70)
        new_penalty = 30 if new_coverage < 50 else (15 if new_coverage < 70 else 0)
        gain = current_penalty - new_penalty

        return FixSuggestion(
            name="Test Coverage",
            description=f"Generate test skeletons for {len(untested_files)} untested file(s)",
            gain=gain,
            note=f"could improve coverage from {coverage_pct}% to ~{new_coverage}%",
            action="generate-tests",
            files=untested_files[:15],
        )

    def calculate_expected_score(self, current_score: int, fixes: list[FixSuggestion]) -> int:
        """Calculate expected score after applying fixes.

        Args:
            current_score: Current audit score
            fixes: List of fixes to apply

        Returns:
            Expected score after fixes
        """
        total_gain = sum(f.gain for f in fixes)
        return min(100, current_score + total_gain)

    def apply_fix(self, fix: FixSuggestion) -> bool:
        """Apply a single fix.

        Args:
            fix: Fix suggestion to apply

        Returns:
            True if fix was applied successfully
        """
        if fix.cmd:
            return self._apply_command_fix(fix)
        if fix.action == "pip-upgrade":
            return self._apply_pip_upgrade(fix)
        if fix.action == "bandit-fix":
            return self._apply_bandit_fix(fix)
        if fix.action == "cleanup":
            return self._apply_cleanup(fix)
        if fix.action == "generate-tests":
            return self._apply_test_generation(fix)
        return False

    def _apply_command_fix(self, fix: FixSuggestion) -> bool:
        """Apply a command-based fix (e.g., ruff --fix).

        Args:
            fix: Fix with cmd field

        Returns:
            True if successful
        """
        if not fix.cmd:
            return False

        if self.verbose:
            print(f"\n  [{fix.name}] Running: {' '.join(fix.cmd)}")

        result = subprocess.run(
            fix.cmd,
            cwd=str(self.project_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if self.verbose and result.stdout:
            for line in result.stdout.strip().split("\n")[:3]:
                print(f"    {line}")

        return True

    def _apply_pip_upgrade(self, fix: FixSuggestion) -> bool:
        """Apply pip package upgrades.

        Args:
            fix: Fix with packages list

        Returns:
            True if at least one package was upgraded
        """
        if not fix.packages:
            return False

        if self.verbose:
            print(f"\n  [pip-audit] Upgrading: {', '.join(fix.packages)}")

        upgraded = 0
        for pkg in fix.packages:
            if self.verbose:
                print(f"    Upgrading {pkg}...")

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", pkg],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                if self.verbose:
                    print(f"    [OK] {pkg} upgraded")
                upgraded += 1
            elif self.verbose:
                err_msg = result.stderr[:50] if result.stderr else "unknown error"
                print(f"    [FAIL] {pkg}: {err_msg}")

        return upgraded > 0

    def _apply_bandit_fix(self, fix: FixSuggestion) -> bool:
        """Apply Bandit security fixes (convert assert to if/raise).

        Args:
            fix: Fix with issues list

        Returns:
            True if at least one issue was fixed
        """
        if not fix.issues:
            return False

        if self.verbose:
            print("\n  [Bandit Security] Fixing security issues...")

        fixed_count = 0
        for issue in fix.issues:
            file_path = Path(issue["file"])
            if not file_path.exists():
                continue

            try:
                lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
                line_num = issue["line"] - 1  # 0-indexed

                if 0 <= line_num < len(lines):
                    original_line = lines[line_num]

                    # Fix B101: assert statements
                    if issue["code"] == "B101" and "assert" in original_line:
                        indent = len(original_line) - len(original_line.lstrip())
                        indent_str = " " * indent

                        assert_match = original_line.strip()
                        if assert_match.startswith("assert "):
                            condition = assert_match[7:].strip()
                            lines[line_num] = f"{indent_str}if not ({condition}):\n"
                            lines.insert(line_num + 1, f"{indent_str}    raise AssertionError('{condition}')\n")

                            file_path.write_text("".join(lines), encoding="utf-8")
                            fixed_count += 1
                            if self.verbose:
                                print(f"    Fixed {file_path}:{issue['line']} (assert -> if/raise)")

            except Exception as e:
                if self.verbose:
                    print(f"    [WARN] Could not fix {file_path}:{issue['line']}: {e}")

        if self.verbose and fixed_count > 0:
            print(f"    Fixed {fixed_count} security issue(s)")

        return fixed_count > 0

    def _apply_cleanup(self, fix: FixSuggestion) -> bool:
        """Apply cleanup: cache directories, temp files, and old reports.

        Args:
            fix: Fix suggestion

        Returns:
            True if items were deleted
        """
        import shutil
        from datetime import datetime, timedelta

        if self.verbose:
            print("\n  [Cleanup] Cleaning up project...")

        deleted_dirs = 0
        deleted_files = 0

        # 1. Delete cache directories
        cache_dirs = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
        for cache_name in cache_dirs:
            for cache_path in self.project_path.rglob(cache_name):
                if ".venv" in str(cache_path) or "venv" in str(cache_path):
                    continue
                try:
                    shutil.rmtree(cache_path)
                    deleted_dirs += 1
                except Exception:
                    pass  # nosec B110

        # 2. Delete temp/debug files in root (not in tests/ or app/)
        temp_patterns = ["test_*.json", "debug_*.py", "verify_*.py", "analyze_*.py", "*.log", "*.bak", "*.tmp"]
        for pattern in temp_patterns:
            for temp_file in self.project_path.glob(pattern):
                # Only delete files in project root, not subdirectories
                if temp_file.parent == self.project_path and temp_file.is_file():
                    try:
                        temp_file.unlink()
                        deleted_files += 1
                        if self.verbose:
                            print(f"    Deleted: {temp_file.name}")
                    except Exception:
                        pass  # nosec B110

        # 3. Delete old reports (>7 days old)
        reports_dir = self.project_path / "reports"
        if reports_dir.exists():
            cutoff = datetime.now() - timedelta(days=7)
            for report in reports_dir.glob("*.md"):
                try:
                    mtime = datetime.fromtimestamp(report.stat().st_mtime)
                    if mtime < cutoff:
                        report.unlink()
                        deleted_files += 1
                except Exception:
                    pass  # nosec B110

        if self.verbose:
            print(f"    Deleted {deleted_dirs} cache directories, {deleted_files} files")

        return (deleted_dirs + deleted_files) > 0

    def _apply_test_generation(self, fix: FixSuggestion) -> bool:
        """Apply test skeleton generation.

        Args:
            fix: Fix with files list

        Returns:
            True if tests were generated
        """
        if not fix.files:
            return False

        from app.tools.test_generator import generate_test_skeleton

        if self.verbose:
            print("\n  [Test Coverage] Generating test skeletons...")

        generated_count = 0
        for source_file in fix.files:
            try:
                test_file = generate_test_skeleton(source_file, self.project_path)
                if self.verbose:
                    print(f"    Created {test_file.relative_to(self.project_path)}")
                generated_count += 1
            except Exception as e:
                if self.verbose:
                    print(f"    [WARN] Could not generate test for {source_file.name}: {e}")

        if self.verbose and generated_count > 0:
            print(f"    Generated {generated_count} test file(s)")
            print("    [INFO] Fill in TODO placeholders with actual test assertions")

        return generated_count > 0

    def apply_all_fixes(self, fixes: list[FixSuggestion]) -> bool:
        """Apply all fixes in sequence.

        Args:
            fixes: List of fixes to apply

        Returns:
            True if any fix was applied
        """
        applied_any = False
        for fix in fixes:
            if self.apply_fix(fix):
                applied_any = True
        return applied_any


def display_fix_suggestions(
    fixes: list[FixSuggestion],
    current_score: int,
    ai_analysis: str | None = None,
) -> None:
    """Display fix suggestions to the user.

    Args:
        fixes: List of fix suggestions
        current_score: Current audit score
        ai_analysis: Optional AI analysis text
    """
    print("\n" + "=" * 50)
    print("  Suggested Fixes")
    print("=" * 50)

    if ai_analysis:
        print("\n[AI Recommendations above]")

    print("\nAvailable fixes:")
    for i, fix in enumerate(fixes, 1):
        gain_str = f"+{fix.gain}pt" if fix.gain > 0 else "~0pt"
        note = f" ({fix.note})" if fix.note else ""
        print(f"  {i}. {fix.name}: {fix.description} [{gain_str}]{note}")

    total_gain = sum(f.gain for f in fixes)
    expected_score = min(100, current_score + total_gain)

    if total_gain > 0:
        print(f"\nExpected: {current_score} -> {expected_score} (+{total_gain}pt)")
    else:
        print(f"\nExpected: {current_score} (minimal impact - issues below penalty thresholds)")
