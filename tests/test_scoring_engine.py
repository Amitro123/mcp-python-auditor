"""
Unit tests for the ScoringEngine.
Ensures all score calculations are deterministic and match the documented algorithm.
"""

import pytest
from app.core.scoring_engine import ScoringEngine, ScoreBreakdown


class TestScoreBreakdown:
    """Test the ScoreBreakdown dataclass"""
    
    def test_final_score_calculation(self):
        """Test that final score is calculated correctly"""
        breakdown = ScoreBreakdown(
            base_score=100,
            security_penalty=10,
            quality_penalty=15,
            testing_penalty=20,
            maintenance_penalty=5
        )
        assert breakdown.final_score == 50  # 100 - 10 - 15 - 20 - 5
    
    def test_final_score_minimum_zero(self):
        """Test that final score never goes below 0"""
        breakdown = ScoreBreakdown(
            base_score=100,
            security_penalty=60,
            quality_penalty=30,
            testing_penalty=30,
            maintenance_penalty=10
        )
        assert breakdown.final_score == 0  # Should cap at 0, not negative
    
    @pytest.mark.parametrize("penalty_kwargs,expected_score,expected_grade", [
        ({"security_penalty": 3}, 97, "A+"),    # 95-100 = A+
        ({"security_penalty": 8}, 92, "A"),     # 90-94 = A
        ({"testing_penalty": 15}, 85, "B"),     # 80-89 = B
        ({"quality_penalty": 25}, 75, "C"),     # 70-79 = C
        ({"testing_penalty": 35}, 65, "D"),     # 60-69 = D
        ({"security_penalty": 50}, 50, "F"),    # 0-59 = F
    ])
    def test_grades(self, penalty_kwargs, expected_score, expected_grade):
        """Test grade calculation for various penalty levels."""
        breakdown = ScoreBreakdown(base_score=100, **penalty_kwargs)
        assert breakdown.final_score == expected_score
        assert breakdown.grade == expected_grade


class TestScoringEngine:
    """Test the ScoringEngine calculations"""
    
    def test_perfect_score(self):
        """Test a perfect codebase with no issues"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 85},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.final_score == 100
        assert breakdown.grade == "A+"
        assert breakdown.security_penalty == 0
        assert breakdown.testing_penalty == 0
        assert breakdown.quality_penalty == 0
    
    @pytest.mark.parametrize("bandit_issues,secrets_count,expected_penalty,expected_score,description", [
        (5, 0, 25, 75, "bandit issues (5 * 5 = 25)"),
        (10, 0, 30, 70, "bandit capped at 30"),
        (0, 3, 30, 70, "secrets (3 * 10 = 30)"),
        (0, 10, 40, 60, "secrets capped at 40"),
    ])
    def test_security_penalties(self, bandit_issues, secrets_count, expected_penalty, expected_score, description):
        """Test security penalty calculation for Bandit and secrets."""
        audit_results = {
            "bandit": {"total_issues": bandit_issues},
            "secrets": {"total_secrets": secrets_count},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.security_penalty == expected_penalty, f"Failed for {description}"
        assert breakdown.final_score == expected_score
    
    def test_combined_security_penalties(self):
        """Test that Bandit and secrets penalties combine"""
        audit_results = {
            "bandit": {"total_issues": 6},  # 30 (capped)
            "secrets": {"total_secrets": 4},  # 40 (capped)
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.security_penalty == 70  # 30 + 40
    
    @pytest.mark.parametrize("coverage,expected_penalty,description", [
        (0, 50, "no coverage (0%)"),
        (5, 40, "critical coverage (< 10%)"),
        (20, 30, "very low coverage (< 30%)"),
        (40, 20, "low coverage (< 50%)"),
        (60, 10, "moderate coverage (< 70%)"),
        (75, 0, "good coverage (>= 70%)"),
    ])
    def test_testing_penalties(self, coverage, expected_penalty, description):
        """Test testing penalty calculation for various coverage levels."""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": coverage},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.testing_penalty == expected_penalty, f"Failed for {description}"
        assert breakdown.final_score == 100 - expected_penalty
    
    @pytest.mark.parametrize("dead_code_count,expected_penalty,description", [
        (8, 16, "dead code (8 * 2 = 16)"),
        (20, 20, "dead code capped at 20"),
    ])
    def test_quality_penalty_dead_code(self, dead_code_count, expected_penalty, description):
        """Test quality penalty from dead code."""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": dead_code_count},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.quality_penalty == expected_penalty, f"Failed for {description}"
    
    def test_quality_penalty_duplication(self):
        """Test quality penalty from code duplication"""
        duplicates = [
            {"similarity": 96, "function_name": "func1"},
            {"similarity": 97, "function_name": "func2"},
            {"similarity": 98, "function_name": "func3"},
            {"similarity": 99, "function_name": "func4"},
            {"similarity": 100, "function_name": "func5"},
        ]
        
        # Add 10 more to exceed threshold
        for i in range(6, 16):
            duplicates.append({"similarity": 96, "function_name": f"func{i}"})
        
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": duplicates}  # 15 total, 5 over threshold
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.quality_penalty == 5  # 15 - 10 = 5
    
    def test_quality_penalty_ignores_low_similarity(self):
        """Test that duplicates with < 95% similarity are ignored"""
        duplicates = [
            {"similarity": 90, "function_name": "func1"},
            {"similarity": 92, "function_name": "func2"},
            {"similarity": 94, "function_name": "func3"},
        ]
        
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": duplicates}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.quality_penalty == 0  # All below 95% threshold
    
    def test_realistic_scenario(self):
        """Test a realistic codebase with multiple issues"""
        audit_results = {
            "bandit": {"total_issues": 3},  # 15 penalty
            "secrets": {"total_secrets": 1},  # 10 penalty
            "tests": {"coverage_percent": 45},  # 20 penalty
            "dead_code": {"total_dead": 5},  # 10 penalty
            "duplication": {"duplicates": [
                {"similarity": 96, "function_name": f"func{i}"} 
                for i in range(12)  # 2 over threshold
            ]}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.security_penalty == 25  # 15 + 10
        assert breakdown.testing_penalty == 20
        assert breakdown.quality_penalty == 12  # 10 (dead) + 2 (dup)
        assert breakdown.final_score == 43  # 100 - 25 - 20 - 12
        assert breakdown.grade == "F"
