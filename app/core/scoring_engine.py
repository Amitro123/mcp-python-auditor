"""Scoring Engine - Pure deterministic calculations with zero hallucination.
All scores and penalties are calculated using fixed algorithms.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ScoreBreakdown:
    """Represents the exact score breakdown"""

    base_score: int = 100
    security_penalty: int = 0
    quality_penalty: int = 0
    testing_penalty: int = 0
    maintenance_penalty: int = 0

    @property
    def final_score(self) -> int:
        return max(
            0,
            self.base_score - self.security_penalty - self.quality_penalty - self.testing_penalty - self.maintenance_penalty,
        )

    @property
    def grade(self) -> str:
        """A+/A/B/C/D/F"""
        if self.final_score >= 95:
            return "A+"
        if self.final_score >= 90:
            return "A"
        if self.final_score >= 80:
            return "B"
        if self.final_score >= 70:
            return "C"
        if self.final_score >= 60:
            return "D"
        return "F"


class ScoringEngine:
    """Calculates scores and penalties using a fixed algorithm"""

    @staticmethod
    def calculate_score(audit_results: dict[str, Any]) -> ScoreBreakdown:
        """Calculate score breakdown from audit results.
        This is pure math - NO LLM interpretation.
        """
        breakdown = ScoreBreakdown()

        # Security penalty - algorithm from README
        bandit = audit_results.get("bandit", {})
        if bandit.get("total_issues", 0) > 0:
            breakdown.security_penalty = min(bandit["total_issues"] * 5, 30)

        # Secrets penalty
        secrets = audit_results.get("secrets", {})
        if secrets.get("total_secrets", 0) > 0:
            breakdown.security_penalty += min(secrets["total_secrets"] * 10, 40)

        # Testing penalty - updated algorithm
        tests = audit_results.get("tests", {})
        coverage = tests.get("coverage_percent", 0)

        if coverage == 0:
            breakdown.testing_penalty = 50  # No tests at all
        elif coverage < 10:
            breakdown.testing_penalty = 40  # Critical coverage
        elif coverage < 30:
            breakdown.testing_penalty = 30  # Very low coverage
        elif coverage < 50:
            breakdown.testing_penalty = 20  # Low coverage
        elif coverage < 70:
            breakdown.testing_penalty = 10  # Moderate coverage
        # 70%+ = no penalty

        # Quality penalty - dead code + duplicates
        dead_code = audit_results.get("dead_code", {})
        dead_count = dead_code.get("total_dead", 0)
        if dead_count > 0:
            breakdown.quality_penalty += min(dead_count * 2, 20)

        duplication = audit_results.get("duplication", {})
        # Count only duplicates with similarity > 95% (not test helpers)
        exact_dups = [d for d in duplication.get("duplicates", []) if d.get("similarity", 0) > 95]
        if len(exact_dups) > 10:
            breakdown.quality_penalty += min(len(exact_dups) - 10, 15)

        # Maintenance penalty - cleanup items (cache dirs, temp files, old reports)
        cleanup = audit_results.get("cleanup", {})
        cleanup_count = cleanup.get("total_items", cleanup.get("total", 0))
        if cleanup_count > 50:
            breakdown.maintenance_penalty += 5  # -5 points if >50 cleanup items

        return breakdown
