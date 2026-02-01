"""Trend Analyzer - Track audit metrics over time with ASCII visualization."""

import datetime
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditSnapshot:
    """A single point-in-time audit record."""

    timestamp: str
    score: int
    grade: str
    coverage_percent: float
    security_issues: int
    secrets_count: int
    ruff_issues: int
    complexity_issues: int
    dead_code_count: int
    duplicate_count: int
    files_scanned: int
    duration_seconds: float
    commit_hash: str | None = None
    branch: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditSnapshot":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class TrendAnalyzer:
    """Analyzes audit trends over time.

    Stores history in JSONL format for easy appending and parsing.
    Provides ASCII-based visualizations for terminal/markdown output.
    """

    HISTORY_FILE = "history.jsonl"
    MAX_HISTORY_ENTRIES = 100  # Keep last 100 audits

    def __init__(self, project_path: Path):
        """Initialize trend analyzer.

        Args:
            project_path: Root path of the project being audited

        """
        self.project_path = Path(project_path).resolve()
        self.index_dir = self.project_path / ".audit_index"
        self.history_file = self.index_dir / self.HISTORY_FILE

    def _ensure_index_dir(self) -> None:
        """Create index directory if it doesn't exist."""
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Add to .gitignore if not already there
        gitignore = self.project_path / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")
            if ".audit_index/" not in content:
                with open(gitignore, "a", encoding="utf-8") as f:
                    f.write("\n# Audit history cache\n.audit_index/\n")

    def record_audit(self, results: dict[str, Any], score: int, grade: str) -> AuditSnapshot:
        """Record an audit result to history.

        Args:
            results: Full audit results dictionary
            score: Calculated audit score (0-100)
            grade: Letter grade (A+, A, B, C, D, F)

        Returns:
            The created AuditSnapshot

        """
        self._ensure_index_dir()

        # Extract metrics from results
        snapshot = AuditSnapshot(
            timestamp=datetime.datetime.now().isoformat(),
            score=score,
            grade=grade,
            coverage_percent=results.get("tests", {}).get("coverage_percent", 0),
            security_issues=results.get("bandit", {}).get("total_issues", 0),
            secrets_count=results.get("secrets", {}).get("total_secrets", 0),
            ruff_issues=results.get("ruff", {}).get("total_issues", 0),
            complexity_issues=len(results.get("efficiency", {}).get("complexity", [])),
            dead_code_count=results.get("dead_code", {}).get("total_dead", 0),
            duplicate_count=results.get("duplication", {}).get("total_duplicates", 0),
            files_scanned=results.get("structure", {}).get("total_files", 0),
            duration_seconds=results.get("duration_seconds", 0),
            commit_hash=results.get("git_info", {}).get("commit_hash"),
            branch=results.get("git_info", {}).get("branch"),
        )

        # Append to JSONL file
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot.to_dict()) + "\n")

        # Trim old entries if needed
        self._trim_history()

        logger.info(f"Recorded audit snapshot: score={score}, grade={grade}")
        return snapshot

    def _trim_history(self) -> None:
        """Keep only the last MAX_HISTORY_ENTRIES entries."""
        if not self.history_file.exists():
            return

        lines = self.history_file.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) > self.MAX_HISTORY_ENTRIES:
            # Keep only the most recent entries
            trimmed = lines[-self.MAX_HISTORY_ENTRIES :]
            self.history_file.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
            logger.debug(f"Trimmed history from {len(lines)} to {len(trimmed)} entries")

    def get_history(self, limit: int = 20) -> list[AuditSnapshot]:
        """Get recent audit history.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of AuditSnapshot objects, most recent last

        """
        if not self.history_file.exists():
            return []

        snapshots = []
        try:
            lines = self.history_file.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-limit:]:
                if line.strip():
                    try:
                        data = json.loads(line)
                        snapshots.append(AuditSnapshot.from_dict(data))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Error reading history: {e}")

        return snapshots

    def get_trend_summary(self) -> dict[str, Any]:
        """Get a summary of trends from recent history.

        Returns:
            Dictionary with trend analysis

        """
        history = self.get_history(limit=10)

        if len(history) < 2:
            return {"has_history": False, "message": "Not enough history for trend analysis"}

        current = history[-1]
        previous = history[-2]
        oldest = history[0]

        # Calculate deltas
        score_delta = current.score - previous.score
        coverage_delta = current.coverage_percent - previous.coverage_percent
        security_delta = current.security_issues - previous.security_issues

        # Calculate overall improvement from oldest
        overall_score_change = current.score - oldest.score
        audit_count = len(history)

        # Determine trend direction
        if score_delta > 0:
            trend = "improving"
            trend_emoji = "📈"
        elif score_delta < 0:
            trend = "declining"
            trend_emoji = "📉"
        else:
            trend = "stable"
            trend_emoji = "➡️"

        return {
            "has_history": True,
            "audit_count": audit_count,
            "current_score": current.score,
            "previous_score": previous.score,
            "score_delta": score_delta,
            "coverage_delta": round(coverage_delta, 1),
            "security_delta": security_delta,
            "overall_score_change": overall_score_change,
            "trend": trend,
            "trend_emoji": trend_emoji,
            "sparkline": self.generate_sparkline([h.score for h in history]),
            "coverage_sparkline": self.generate_sparkline([h.coverage_percent for h in history], max_val=100),
        }

    def generate_sparkline(self, values: list[float], width: int = 10, max_val: float | None = None) -> str:
        """Generate an ASCII sparkline from values.

        Args:
            values: List of numeric values
            width: Maximum width of sparkline
            max_val: Optional maximum value for scaling

        Returns:
            ASCII sparkline string

        """
        if not values:
            return "─" * width

        # Use last N values if we have more than width
        if len(values) > width:
            values = values[-width:]

        # Determine scale
        min_v = min(values)
        max_v = max_val if max_val else max(values)

        if max_v == min_v:
            return "─" * len(values)

        # Sparkline characters (8 levels)
        chars = "▁▂▃▄▅▆▇█"

        sparkline = ""
        for v in values:
            # Normalize to 0-7 range
            normalized = (v - min_v) / (max_v - min_v) * 7
            idx = min(7, max(0, int(normalized)))
            sparkline += chars[idx]

        return sparkline

    def generate_trend_report(self) -> str:
        """Generate a markdown trend report section.

        Returns:
            Markdown string for inclusion in audit report

        """
        summary = self.get_trend_summary()

        if not summary["has_history"]:
            return "## 📈 Trend Analysis\n\n_First audit - no historical data yet._\n"

        lines = [
            "## 📈 Trend Analysis",
            "",
            f"**Audits Recorded:** {summary['audit_count']}",
            f"**Score Trend:** {summary['trend_emoji']} {summary['trend'].title()}",
            "",
            "### Score History",
            "```",
            f"Score: {summary['sparkline']} ({summary['previous_score']} → {summary['current_score']})",
            "```",
            "",
        ]

        # Add delta information
        delta_sign = "+" if summary["score_delta"] >= 0 else ""
        lines.append(f"**Last Change:** {delta_sign}{summary['score_delta']} points")

        if summary["coverage_delta"] != 0:
            cov_sign = "+" if summary["coverage_delta"] >= 0 else ""
            lines.append(f"**Coverage Change:** {cov_sign}{summary['coverage_delta']}%")

        if summary["security_delta"] != 0:
            sec_sign = "+" if summary["security_delta"] > 0 else ""
            # For security, negative is good (fewer issues)
            status = "⚠️" if summary["security_delta"] > 0 else "✅"
            lines.append(f"**Security Issues:** {status} {sec_sign}{summary['security_delta']}")

        # Overall progress
        if summary["audit_count"] > 2:
            overall_sign = "+" if summary["overall_score_change"] >= 0 else ""
            lines.append("")
            lines.append(f"**Overall Progress:** {overall_sign}{summary['overall_score_change']} points over {summary['audit_count']} audits")

        lines.append("")
        return "\n".join(lines)

    def get_improvement_suggestions(self) -> list[str]:
        """Generate improvement suggestions based on trends.

        Returns:
            List of actionable suggestions

        """
        history = self.get_history(limit=5)
        suggestions = []

        if len(history) < 2:
            return ["Run more audits to get trend-based suggestions"]

        current = history[-1]

        # Coverage suggestions
        if current.coverage_percent < 50:
            suggestions.append(f"📊 Coverage is {current.coverage_percent}% - aim for 70%+")

        # Security suggestions
        if current.security_issues > 0:
            suggestions.append(f"🔒 Fix {current.security_issues} security issue(s)")

        # Check for worsening trends
        if len(history) >= 3:
            recent_scores = [h.score for h in history[-3:]]
            if recent_scores == sorted(recent_scores, reverse=True):
                suggestions.append("📉 Scores declining - review recent changes")

        # Complexity suggestions
        if current.complexity_issues > 5:
            suggestions.append(f"🧮 Reduce complexity in {current.complexity_issues} functions")

        return suggestions if suggestions else ["✅ No immediate improvements needed"]
