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
    
    def test_grade_a_plus(self):
        """Test A+ grade (95-100)"""
        breakdown = ScoreBreakdown(base_score=100, security_penalty=3)
        assert breakdown.final_score == 97
        assert breakdown.grade == "A+"
    
    def test_grade_a(self):
        """Test A grade (90-94)"""
        breakdown = ScoreBreakdown(base_score=100, security_penalty=8)
        assert breakdown.final_score == 92
        assert breakdown.grade == "A"
    
    def test_grade_b(self):
        """Test B grade (80-89)"""
        breakdown = ScoreBreakdown(base_score=100, testing_penalty=15)
        assert breakdown.final_score == 85
        assert breakdown.grade == "B"
    
    def test_grade_c(self):
        """Test C grade (70-79)"""
        breakdown = ScoreBreakdown(base_score=100, quality_penalty=25)
        assert breakdown.final_score == 75
        assert breakdown.grade == "C"
    
    def test_grade_d(self):
        """Test D grade (60-69)"""
        breakdown = ScoreBreakdown(base_score=100, testing_penalty=35)
        assert breakdown.final_score == 65
        assert breakdown.grade == "D"
    
    def test_grade_f(self):
        """Test F grade (0-59)"""
        breakdown = ScoreBreakdown(base_score=100, security_penalty=50)
        assert breakdown.final_score == 50
        assert breakdown.grade == "F"


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
    
    def test_security_penalty_bandit(self):
        """Test security penalty from Bandit issues"""
        audit_results = {
            "bandit": {"total_issues": 5},  # 5 * 5 = 25 penalty
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.security_penalty == 25
        assert breakdown.final_score == 75  # 100 - 25
    
    def test_security_penalty_capped(self):
        """Test that Bandit penalty is capped at 30"""
        audit_results = {
            "bandit": {"total_issues": 10},  # Would be 50, but capped at 30
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.security_penalty == 30
    
    def test_secrets_penalty(self):
        """Test security penalty from secrets"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 3},  # 3 * 10 = 30 penalty
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.security_penalty == 30
        assert breakdown.final_score == 70
    
    def test_secrets_penalty_capped(self):
        """Test that secrets penalty is capped at 40"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 10},  # Would be 100, but capped at 40
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.security_penalty == 40
    
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
    
    def test_testing_penalty_no_coverage(self):
        """Test maximum testing penalty for 0% coverage"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 0},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.testing_penalty == 50
        assert breakdown.final_score == 50
    
    def test_testing_penalty_critical(self):
        """Test critical coverage penalty (< 10%)"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 5},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.testing_penalty == 40
    
    def test_testing_penalty_very_low(self):
        """Test very low coverage penalty (< 30%)"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 20},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.testing_penalty == 30
    
    def test_testing_penalty_low(self):
        """Test low coverage penalty (< 50%)"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 40},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.testing_penalty == 20
    
    def test_testing_penalty_moderate(self):
        """Test moderate coverage penalty (< 70%)"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 60},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.testing_penalty == 10
    
    def test_testing_no_penalty(self):
        """Test no penalty for good coverage (>= 70%)"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 75},
            "dead_code": {"total_dead": 0},
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.testing_penalty == 0
    
    def test_quality_penalty_dead_code(self):
        """Test quality penalty from dead code"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 8},  # 8 * 2 = 16 penalty
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.quality_penalty == 16
    
    def test_quality_penalty_dead_code_capped(self):
        """Test that dead code penalty is capped at 20"""
        audit_results = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 20},  # Would be 40, but capped at 20
            "duplication": {"duplicates": []}
        }
        
        breakdown = ScoringEngine.calculate_score(audit_results)
        assert breakdown.quality_penalty == 20
    
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
