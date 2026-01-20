"""
Report Validator - Ensures consistency between JSON data and generated markdown.
Catches hallucinations and data mismatches.
"""

from typing import Dict, Any, List, Optional
import re
from .scoring_engine import ScoreBreakdown


class ReportValidator:
    """Validates consistency between JSON data and generated report"""
    
    def validate_consistency(self, 
                           json_data: Dict[str, Any],
                           markdown_report: str,
                           score_breakdown: ScoreBreakdown) -> List[str]:
        """Returns list of inconsistency errors"""
        errors = []
        
        # Validate score
        md_score = self._extract_score(markdown_report)
        if md_score and abs(score_breakdown.final_score - md_score) > 2:
            errors.append(
                f"Score mismatch: Calculated={score_breakdown.final_score}, "
                f"Report={md_score}"
            )
        
        # Validate coverage
        json_coverage = json_data.get("tests", {}).get("coverage_percent", 0)
        md_coverage = self._extract_coverage(markdown_report)
        if md_coverage is not None and json_coverage != md_coverage:
            errors.append(
                f"Coverage mismatch: JSON={json_coverage}%, Report={md_coverage}%"
            )
        
        # Check for misleading language
        if json_coverage < 30:
            misleading_phrases = [
                "good coverage", "excellent coverage", "well tested",
                "comprehensive tests", "strong test suite"
            ]
            for phrase in misleading_phrases:
                if phrase.lower() in markdown_report.lower():
                    errors.append(
                        f"Misleading phrase '{phrase}' found for {json_coverage}% coverage"
                    )
        
        # Validate security issues count
        json_bandit = json_data.get("bandit", {}).get("total_issues", 0)
        json_secrets = json_data.get("secrets", {}).get("total_secrets", 0)
        total_security = json_bandit + json_secrets
        
        md_security = self._extract_security_count(markdown_report)
        if md_security is not None and md_security != total_security:
            errors.append(
                f"Security count mismatch: JSON={total_security}, Report={md_security}"
            )
        
        # Validate dead code count
        json_dead = json_data.get("dead_code", {}).get("total_dead", 0)
        md_dead = self._extract_dead_code_count(markdown_report)
        if md_dead is not None and md_dead != json_dead:
            errors.append(
                f"Dead code mismatch: JSON={json_dead}, Report={md_dead}"
            )
        
        return errors
    
    def _extract_score(self, markdown: str) -> Optional[int]:
        """Extract overall score from markdown"""
        # Match "Score: X/100" or "Overall Score: X/100"
        match = re.search(r'(?:Overall\s+)?Score:\s*(\d+)/100', markdown, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_coverage(self, markdown: str) -> Optional[float]:
        """Extract coverage percentage from markdown"""
        # Look for patterns like "Coverage: 45.2%", "**Coverage**: 45.2%", or "45.2% coverage"
        match = re.search(r'\*?\*?Coverage\*?\*?[:\s]+(\d+\.?\d*)%', markdown, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r'(\d+\.?\d*)%\s+coverage', markdown, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_security_count(self, markdown: str) -> Optional[int]:
        """Extract total security issues count"""
        # Look for "X issues, Y secrets" pattern
        match = re.search(r'(\d+)\s+issues,\s+(\d+)\s+secrets', markdown)
        if match:
            return int(match.group(1)) + int(match.group(2))
        return None
    
    def _extract_dead_code_count(self, markdown: str) -> Optional[int]:
        """Extract dead code count"""
        match = re.search(r'(\d+)\s+dead code items', markdown)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)\s+items found', markdown)
        if match:
            return int(match.group(1))
        return None
