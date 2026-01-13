"""
Unit tests for the scoring algorithm.
Tests the realistic scoring penalties for coverage, duplicates, etc.
"""
import pytest


class TestScoringAlgorithm:
    """Test the weighted scoring algorithm."""
    
    def test_perfect_score(self):
        """Project with no issues should get 100/100."""
        results = {
            "bandit": {"issues": []},
            "secrets": {"total_findings": 0},
            "tests": {"coverage_percent": 100},
            "duplication": {"total_duplicates": 0},
            "dead_code": {"unused_items": []},
            "efficiency": {"high_complexity_functions": []}
        }
        
        score = calculate_score(results)
        assert score == 100
    
    def test_low_coverage_penalty(self):
        """9% coverage should give -40 points (exponential penalty)."""
        results = {
            "bandit": {"issues": []},
            "secrets": {"total_findings": 0},
            "tests": {"coverage_percent": 9},
            "duplication": {"total_duplicates": 0},
            "dead_code": {"unused_items": []},
            "efficiency": {"high_complexity_functions": []}
        }
        
        score = calculate_score(results)
        assert score == 60  # 100 - 40 for low coverage
    
    def test_duplicates_penalty(self):
        """78 duplicates should be capped at -15 points."""
        results = {
            "bandit": {"issues": []},
            "secrets": {"total_findings": 0},
            "tests": {"coverage_percent": 100},
            "duplication": {"total_duplicates": 78},
            "dead_code": {"unused_items": []},
            "efficiency": {"high_complexity_functions": []}
        }
        
        score = calculate_score(results)
        assert score == 85  # 100 - 15 (capped)
    
    def test_realistic_project_score(self):
        """Real project: 9% coverage + 78 duplicates = 45/100."""
        results = {
            "bandit": {"issues": []},
            "secrets": {"total_findings": 0},
            "tests": {"coverage_percent": 9},
            "duplication": {"total_duplicates": 78},
            "dead_code": {"unused_items": []},
            "efficiency": {"high_complexity_functions": []}
        }
        
        score = calculate_score(results)
        assert score == 45  # 100 - 40 (coverage) - 15 (duplicates)
    
    def test_security_penalty(self):
        """Security issues should give -20 points."""
        results = {
            "bandit": {"issues": [{"severity": "HIGH"}]},
            "secrets": {"total_findings": 0},
            "tests": {"coverage_percent": 100},
            "duplication": {"total_duplicates": 0},
            "dead_code": {"unused_items": []},
            "efficiency": {"high_complexity_functions": []}
        }
        
        score = calculate_score(results)
        assert score == 80  # 100 - 20
    
    def test_secrets_penalty(self):
        """Secrets found should give -10 points."""
        results = {
            "bandit": {"issues": []},
            "secrets": {"total_findings": 3},
            "tests": {"coverage_percent": 100},
            "duplication": {"total_duplicates": 0},
            "dead_code": {"unused_items": []},
            "efficiency": {"high_complexity_functions": []}
        }
        
        score = calculate_score(results)
        assert score == 90  # 100 - 10


def calculate_score(results: dict) -> int:
    """
    Calculate score using the same algorithm as the server.
    This is a copy for testing purposes.
    """
    score = 100
    
    # Security
    if results.get("bandit", {}).get("issues", []):
        score -= 20
    
    if results.get("secrets", {}).get("total_findings", 0) > 0:
        score -= 10
    
    # Testing (exponential)
    cov = results.get("tests", {}).get("coverage_percent", 100)
    if cov < 20:
        score -= 40
    elif cov < 50:
        score -= 25
    elif cov < 80:
        score -= 10
    
    # Quality
    duplicates = results.get("duplication", {}).get("total_duplicates", 0)
    score -= min(duplicates, 15)
    
    dead_code_items = len(results.get("dead_code", {}).get("unused_items", []))
    score -= min(dead_code_items, 5)
    
    # Complexity
    complex_funcs = len(results.get("efficiency", {}).get("high_complexity_functions", []))
    score -= min(complex_funcs * 2, 10)
    
    return max(0, score)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
