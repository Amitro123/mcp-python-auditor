"""Type hint coverage analysis."""
import ast
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class TypingTool(BaseTool):
    """Analyze type hint coverage in Python code."""
    
    @property
    def description(self) -> str:
        return "Analyzes type hint coverage for function arguments and return values"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze type hint coverage.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with type coverage metrics
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            all_functions = []
            typed_functions = []
            partially_typed = []
            untyped_functions = []
            
            # Use centralized file walker from BaseTool
            for py_file in self.walk_project_files(project_path):
                file_results = self._analyze_file(py_file, project_path)
                all_functions.extend(file_results['all'])
                typed_functions.extend(file_results['typed'])
                partially_typed.extend(file_results['partial'])
                untyped_functions.extend(file_results['untyped'])
            
            # Calculate coverage
            total = len(all_functions)
            fully_typed = len(typed_functions)
            partial = len(partially_typed)
            
            coverage_percent = (fully_typed / total * 100) if total > 0 else 0
            
            return {
                "total_functions": total,
                "fully_typed_functions": fully_typed,
                "partially_typed_functions": partial,
                "untyped_functions": len(untyped_functions),
                "type_coverage_percent": round(coverage_percent, 2),
                "untyped_examples": untyped_functions[:10],  # Show first 10
                "grade": self._get_coverage_grade(coverage_percent)
            }
        
        except Exception as e:
            logger.error(f"Type coverage analysis failed: {e}")
            return {"error": str(e)}
    
    def _analyze_file(self, file_path: Path, project_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze type hints in a single file."""
        results = {
            'all': [],
            'typed': [],
            'partial': [],
            'untyped': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip private functions and special methods
                    if node.name.startswith('_') and node.name not in ['__init__', '__call__']:
                        continue
                    
                    func_info = {
                        "file": str(file_path.relative_to(project_path)),
                        "function": node.name,
                        "line": node.lineno
                    }
                    
                    results['all'].append(func_info)
                    
                    # Check type hints
                    has_return_type = node.returns is not None
                    total_args = len(node.args.args)
                    
                    # Count self/cls
                    if total_args > 0 and node.args.args[0].arg in ['self', 'cls']:
                        total_args -= 1
                        typed_args = sum(
                            1 for arg in node.args.args[1:]
                            if arg.annotation is not None
                        )
                    else:
                        typed_args = sum(
                            1 for arg in node.args.args
                            if arg.annotation is not None
                        )
                    
                    # Categorize
                    if has_return_type and (total_args == 0 or typed_args == total_args):
                        results['typed'].append(func_info)
                    elif has_return_type or typed_args > 0:
                        results['partial'].append(func_info)
                    else:
                        results['untyped'].append(func_info)
        
        except Exception as e:
            logger.debug(f"Failed to analyze {file_path}: {e}")
        
        return results
    
    def _get_coverage_grade(self, coverage: float) -> str:
        """Get letter grade for type coverage."""
        if coverage >= 90:
            return 'A'
        elif coverage >= 75:
            return 'B'
        elif coverage >= 60:
            return 'C'
        elif coverage >= 40:
            return 'D'
        else:
            return 'F'
