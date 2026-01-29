"""Scoring Engine - Simplified Emergency Logic."""
from typing import Dict, Any

class ScoringEngine:
    """Calculates scores using simplified rules."""
    
    @staticmethod
    def calculate_score(tool_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate score based on 7 core tools.
        Max Score: 100
        """
        score = 100
        
        # Security (30 points)
        # security = Bandit, secrets = Detect-Secrets
        security_issues = tool_results.get('security', {}).get('total_issues', 0)
        secrets_count = tool_results.get('secrets', {}).get('total_secrets', 0)
        
        # Penalty: 5 points per security issue, 10 per secret
        security_penalty = (security_issues * 5) + (secrets_count * 10)
        score -= min(30, security_penalty)
        
        # Tests (25 points)
        # coverage = pytest coverage %
        coverage = tool_results.get('tests', {}).get('coverage', 0)
        if coverage < 70:
            score -= min(25, 70 - coverage)
        
        # Code Quality (45 points total)
        # duplication, deadcode, cleanup, quality (ruff)
        duplication = tool_results.get('duplication', {}).get('total_duplicates', 0)
        deadcode = tool_results.get('deadcode', {}).get('total_items', 0)
        cleanup = tool_results.get('cleanup', {}).get('total_issues', 0)
        ruff = tool_results.get('quality', {}).get('total_issues', 0) # Ruff returns total_issues
        
        score -= min(15, duplication * 3)      # 15 points for duplicates
        score -= min(10, deadcode // 5)        # 10 points for dead code items (1 pt per 5 items is too low? user said // 5)
        # actually user snippet: score -= min(10, deadcode // 5)
        # Let's check user request again:
        # score -= min(10, deadcode // 5)  -> 50 items = 10 pts penalty. Seems OK.
        
        score -= min(10, cleanup // 10)        # 10 points for cleanup (1 pt per 10 items)
        score -= min(10, ruff // 20)           # 10 points for linting (1 pt per 20 issues)
        
        final_score = max(0, int(score))
        
        return {
            'total_score': final_score,
            'grade': ScoringEngine.grade(final_score),
            'breakdown': {
                'security_penalty': min(30, security_penalty),
                'testing_penalty': min(25, 70 - coverage) if coverage < 70 else 0,
                'quality_penalty': 100 - final_score - min(30, security_penalty) - (min(25, 70 - coverage) if coverage < 70 else 0)
            }
        }

    @staticmethod
    def grade(score: int) -> str:
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 70: return "C"
        if score >= 60: return "D"
        return "F"
