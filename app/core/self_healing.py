"""Self-healing analyzer with dependency detection and auto-fix recommendations."""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SelfHealingAnalyzer:
    """Detects issues and provides auto-fix recommendations."""

    def __init__(self):
        self.healing_log = []
        self.missing_deps = []
        self.fixes_applied = []

    def check_dependencies(self) -> dict[str, Any]:
        """Check for missing critical dependencies."""
        required_deps = {
            "radon": "Code complexity analysis",
            "vulture": "Dead code detection",
            "bandit": "Security scanning",
            "detect-secrets": "Secret detection",
            "coverage": "Test coverage",
        }

        missing = []
        available = []

        for dep, purpose in required_deps.items():
            try:
                __import__(dep)
                available.append(dep)
            except ImportError:
                missing.append({"name": dep, "purpose": purpose})
                self.missing_deps.append(dep)

        return {
            "missing": missing,
            "available": available,
            "total_required": len(required_deps),
            "health_score": len(available) / len(required_deps) * 100,
        }

    def get_auto_fix_command(self) -> str | None:
        """Get the command to auto-fix missing dependencies."""
        if not self.missing_deps:
            return None

        deps_str = " ".join(self.missing_deps)
        return f"pip install {deps_str} --no-deps"

    def check_pytest_health(self, project_path: Path) -> dict[str, Any]:
        """Check pytest configuration and detect issues."""
        issues = []
        fixes = []

        # Check for deepeval (causes GRPC crashes)
        try:
            __import__("deepeval")
            issues.append("deepeval installed (causes pytest GRPC crashes)")
            fixes.append("pip uninstall deepeval -y")
            self.healing_log.append("⚠️ Detected: deepeval (pytest crash risk)")
        except ImportError:
            pass

        # Check for pytest-cov
        try:
            __import__("pytest_cov")
        except ImportError:
            issues.append("pytest-cov not installed")
            fixes.append("pip install pytest-cov")

        return {"issues": issues, "fixes": fixes, "healthy": len(issues) == 0}

    def should_force_tool(self, tool_name: str, project_stats: dict[str, Any]) -> bool:
        """Determine if a tool should be forced to run despite project size."""
        critical_tools = {"security", "secrets", "tests", "typing", "architecture"}

        # Always run critical tools
        if tool_name in critical_tools:
            return True

        # For large projects, use sampling for heavy tools
        py_files = project_stats.get("py_files", 0)
        if py_files > 500:
            # Force with sampling for duplication
            if tool_name == "duplication":
                self.healing_log.append(f"🔧 Forcing {tool_name} with 20% sampling")
                return True

            # Force with top-100 limit for complexity/deadcode
            if tool_name in ["complexity", "deadcode"]:
                self.healing_log.append(f"🔧 Forcing {tool_name} (top 100 files)")
                return True

        return False

    def generate_healing_report(self) -> str:
        """Generate a healing report section."""
        if not self.healing_log and not self.missing_deps:
            return "✅ System healthy - no fixes needed"

        report = []

        if self.missing_deps:
            report.append(f"⚠️ Missing dependencies: {', '.join(self.missing_deps)}")
            fix_cmd = self.get_auto_fix_command()
            if fix_cmd:
                report.append(f"👉 **Auto-fix:** `{fix_cmd}`")

        if self.healing_log:
            report.append("\n**Healing Actions:**")
            for log in self.healing_log:
                report.append(f"- {log}")

        return "\n".join(report)

    def get_one_command_fix(self) -> str | None:
        """Get a single command that fixes all detected issues."""
        commands = []

        # Add dependency installation
        if self.missing_deps:
            deps_str = " ".join(self.missing_deps)
            commands.append(f"pip install {deps_str}")

        # Add deepeval removal if needed
        try:
            __import__("deepeval")
            commands.append("pip uninstall deepeval -y")
        except ImportError:
            pass

        if not commands:
            return None

        return " && ".join(commands)
