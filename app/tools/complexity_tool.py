"""Cyclomatic complexity analysis using Radon."""
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
from app.core.subprocess_wrapper import SubprocessWrapper
import logging
import json

logger = logging.getLogger(__name__)


class ComplexityTool(BaseTool):
    """Analyze cyclomatic complexity using Radon."""
    
    @property
    def description(self) -> str:
        return "Measures cyclomatic complexity and maintainability index using Radon"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze code complexity using Radon.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with complexity metrics
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            # Get cyclomatic complexity
            cc_results = self._get_cyclomatic_complexity(project_path)
            
            # Get maintainability index
            mi_results = self._get_maintainability_index(project_path)
            
            # Analyze results
            high_complexity = [
                item for item in cc_results
                if item['complexity'] > 10
            ]
            
            very_high_complexity = [
                item for item in cc_results
                if item['complexity'] > 15
            ]
            
            # Calculate averages
            avg_complexity = (
                sum(item['complexity'] for item in cc_results) / len(cc_results)
                if cc_results else 0
            )
            
            avg_maintainability = (
                sum(item['maintainability'] for item in mi_results) / len(mi_results)
                if mi_results else 0
            )
            
            return {
                "high_complexity_functions": high_complexity,
                "very_high_complexity_functions": very_high_complexity,
                "total_functions_analyzed": len(cc_results),
                "average_complexity": round(avg_complexity, 2),
                "average_maintainability": round(avg_maintainability, 2),
                "maintainability_grade": self._get_mi_grade(avg_maintainability),
                "files_analyzed": len(mi_results),
                "tool": "radon"
            }
        
        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return {"error": str(e)}
    
    def _get_cyclomatic_complexity(self, project_path: Path) -> List[Dict[str, Any]]:
        """Get cyclomatic complexity metrics."""
        success, stdout, stderr = SubprocessWrapper.run_command(
            ['radon', 'cc', str(project_path), '-j', '-a'],
            cwd=project_path,
            timeout=60,
            check_venv=False
        )
        
        if not success:
            if "not found" in stderr.lower():
                logger.warning("Radon not installed")
                return []
            logger.error(f"Radon cc failed: {stderr}")
            return []
        
        try:
            data = json.loads(stdout)
            results = []
            
            for file_path, functions in data.items():
                if isinstance(functions, list):
                    for func in functions:
                        results.append({
                            "file": file_path,
                            "function": func.get('name', 'unknown'),
                            "line": func.get('lineno', 0),
                            "complexity": func.get('complexity', 0),
                            "rank": func.get('rank', 'A')
                        })
            
            return results
        
        except json.JSONDecodeError:
            logger.error("Failed to parse radon output")
            return []
    
    def _get_maintainability_index(self, project_path: Path) -> List[Dict[str, Any]]:
        """Get maintainability index metrics."""
        success, stdout, stderr = SubprocessWrapper.run_command(
            ['radon', 'mi', str(project_path), '-j'],
            cwd=project_path,
            timeout=60,
            check_venv=False
        )
        
        if not success:
            logger.error(f"Radon mi failed: {stderr}")
            return []
        
        try:
            data = json.loads(stdout)
            results = []
            
            for file_path, metrics in data.items():
                if isinstance(metrics, dict):
                    results.append({
                        "file": file_path,
                        "maintainability": metrics.get('mi', 0),
                        "rank": metrics.get('rank', 'A')
                    })
            
            return results
        
        except json.JSONDecodeError:
            logger.error("Failed to parse radon mi output")
            return []
    
    def _get_mi_grade(self, mi_score: float) -> str:
        """Convert maintainability index to letter grade."""
        if mi_score >= 80:
            return 'A'
        elif mi_score >= 60:
            return 'B'
        elif mi_score >= 40:
            return 'C'
        elif mi_score >= 20:
            return 'D'
        else:
            return 'F'
