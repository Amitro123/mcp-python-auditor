"""
Unit tests for the ReportValidator.
Ensures reports don't hallucinate numbers or use misleading language.
"""

import pytest
from app.core.report_validator import ReportValidator
from app.core.scoring_engine import ScoreBreakdown


class TestReportValidator:
    """Test the ReportValidator consistency checks"""
    
    def test_no_errors_on_consistent_report(self):
        """Test that a consistent report passes validation"""
        json_data = {
            "bandit": {"total_issues": 5},
            "secrets": {"total_secrets": 2},
            "tests": {"coverage_percent": 45.5},
            "dead_code": {"total_dead": 10}
        }
        
        markdown = """
        ## Overall Score: 75/100
        
        Coverage: 45.5%
        
        5 issues, 2 secrets
        
        10 dead code items found
        """
        
        breakdown = ScoreBreakdown(
            base_score=100,
            security_penalty=25,
            testing_penalty=0,
            quality_penalty=0
        )
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 0
    
    def test_score_mismatch_detected(self):
        """Test that score mismatches are detected"""
        json_data = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0}
        }
        
        markdown = "## Overall Score: 65/100"  # Wrong score
        
        breakdown = ScoreBreakdown(base_score=100)  # Should be 100
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 1
        assert "Score mismatch" in errors[0]
        assert "Calculated=100" in errors[0]
        assert "Report=65" in errors[0]
    
    def test_coverage_mismatch_detected(self):
        """Test that coverage mismatches are detected"""
        json_data = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 45.5},
            "dead_code": {"total_dead": 0}
        }
        
        markdown = "Coverage: 75.0%"  # Wrong coverage
        
        breakdown = ScoreBreakdown(base_score=100, testing_penalty=20)
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 1
        assert "Coverage mismatch" in errors[0]
        assert "JSON=45.5%" in errors[0]
        assert "Report=75.0%" in errors[0]
    
    def test_misleading_language_low_coverage(self):
        """Test that misleading language is detected for low coverage"""
        json_data = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 10},  # Very low
            "dead_code": {"total_dead": 0}
        }
        
        markdown = """
        Coverage: 10%
        
        This codebase has good coverage and is well tested.
        """
        
        breakdown = ScoreBreakdown(base_score=100, testing_penalty=40)
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) >= 2  # Should catch both "good coverage" and "well tested"
        assert any("good coverage" in error for error in errors)
        assert any("well tested" in error for error in errors)
    
    def test_security_count_mismatch(self):
        """Test that security issue count mismatches are detected"""
        json_data = {
            "bandit": {"total_issues": 5},
            "secrets": {"total_secrets": 2},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0}
        }
        
        markdown = "10 issues, 3 secrets"  # Wrong counts
        
        breakdown = ScoreBreakdown(base_score=100, security_penalty=35)
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 1
        assert "Security count mismatch" in errors[0]
        assert "JSON=7" in errors[0]  # 5 + 2
        assert "Report=13" in errors[0]  # 10 + 3
    
    def test_dead_code_mismatch(self):
        """Test that dead code count mismatches are detected"""
        json_data = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 15}
        }
        
        markdown = "25 dead code items found"  # Wrong count
        
        breakdown = ScoreBreakdown(base_score=100, quality_penalty=20)
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 1
        assert "Dead code mismatch" in errors[0]
        assert "JSON=15" in errors[0]
        assert "Report=25" in errors[0]
    
    def test_multiple_errors_detected(self):
        """Test that multiple inconsistencies are all detected"""
        json_data = {
            "bandit": {"total_issues": 5},
            "secrets": {"total_secrets": 2},
            "tests": {"coverage_percent": 10},
            "dead_code": {"total_dead": 15}
        }
        
        markdown = """
        ## Overall Score: 90/100
        
        Coverage: 85%
        
        This codebase has excellent coverage.
        
        2 issues, 1 secrets
        
        5 dead code items found
        """
        
        breakdown = ScoreBreakdown(
            base_score=100,
            security_penalty=35,
            testing_penalty=40,
            quality_penalty=20
        )  # Real score should be 5
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        
        # Should detect: score mismatch, coverage mismatch, misleading language,
        # security count mismatch, dead code mismatch
        assert len(errors) >= 5
    
    def test_extract_score_various_formats(self):
        """Test score extraction from different markdown formats"""
        validator = ReportValidator()
        
        assert validator._extract_score("Overall Score: 85/100") == 85
        assert validator._extract_score("Score: 72/100") == 72
        assert validator._extract_score("## Overall Score: 95/100 (A+)") == 95
    
    def test_extract_coverage_various_formats(self):
        """Test coverage extraction from different markdown formats"""
        validator = ReportValidator()
        
        assert validator._extract_coverage("Coverage: 45.5%") == 45.5
        assert validator._extract_coverage("45.5% coverage") == 45.5
        assert validator._extract_coverage("**Coverage**: 80.0%") == 80.0
    
    def test_extract_security_count(self):
        """Test security count extraction"""
        validator = ReportValidator()
        
        assert validator._extract_security_count("5 issues, 2 secrets") == 7
        assert validator._extract_security_count("10 issues, 0 secrets") == 10
        assert validator._extract_security_count("0 issues, 3 secrets") == 3
    
    def test_extract_dead_code_count(self):
        """Test dead code count extraction"""
        validator = ReportValidator()
        
        assert validator._extract_dead_code_count("15 dead code items") == 15
        assert validator._extract_dead_code_count("25 items found") == 25
    
    def test_no_false_positives_on_good_report(self):
        """Test that a well-written accurate report has no errors"""
        json_data = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 85.5},
            "dead_code": {"total_dead": 0}
        }
        
        markdown = """
        # Audit Report
        
        ## Overall Score: 100/100 (A+)
        
        ### Test Coverage
        Coverage: 85.5%
        
        The codebase has good test coverage.
        
        ### Security
        0 issues, 0 secrets
        
        ✅ No security issues detected
        
        ### Code Quality
        0 dead code items found
        """
        
        breakdown = ScoreBreakdown(base_score=100)
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 0
    
    def test_tolerates_small_score_differences(self):
        """Test that small rounding differences (<=2) are tolerated"""
        json_data = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0}
        }
        
        markdown = "Overall Score: 99/100"  # Off by 1
        
        breakdown = ScoreBreakdown(base_score=100)  # Actual: 100
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 0  # Should tolerate difference of 1
    
    def test_detects_large_score_differences(self):
        """Test that large score differences (>2) are detected"""
        json_data = {
            "bandit": {"total_issues": 0},
            "secrets": {"total_secrets": 0},
            "tests": {"coverage_percent": 80},
            "dead_code": {"total_dead": 0}
        }
        
        markdown = "Overall Score: 95/100"  # Off by 5
        
        breakdown = ScoreBreakdown(base_score=100)  # Actual: 100
        
        validator = ReportValidator()
        errors = validator.validate_consistency(json_data, markdown, breakdown)
        assert len(errors) == 1
        assert "Score mismatch" in errors[0]
