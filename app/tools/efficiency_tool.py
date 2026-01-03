"""Code efficiency analysis tool."""
import ast
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class EfficiencyTool(BaseTool):
    """Detect code efficiency issues and anti-patterns."""
    
    @property
    def description(self) -> str:
        return "Detects efficiency issues like nested loops, inefficient operations, and anti-patterns"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze code for efficiency issues.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with efficiency issues
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            issues = []
            
            for py_file in project_path.rglob("*.py"):
                if any(p in py_file.parts for p in ['__pycache__', '.venv', 'venv', 'test']):
                    continue
                
                file_issues = self._analyze_file(py_file, project_path)
                issues.extend(file_issues)
            
            return {
                "issues": issues,
                "total_issues": len(issues),
                "by_type": self._count_by_type(issues)
            }
        except Exception as e:
            logger.error(f"Efficiency analysis failed: {e}")
            return {"error": str(e)}
    
    def _analyze_file(self, file_path: Path, project_path: Path) -> List[Dict[str, Any]]:
        """Analyze a single file for efficiency issues."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            relative_path = str(file_path.relative_to(project_path))
            
            # Check for nested loops
            issues.extend(self._check_nested_loops(tree, relative_path))
            
            # Check for inefficient list operations
            issues.extend(self._check_list_operations(tree, relative_path))
            
            # Check for global variables in functions
            issues.extend(self._check_global_usage(tree, relative_path))
            
            # Check for string concatenation in loops
            issues.extend(self._check_string_concat(tree, relative_path, content))
        
        except Exception as e:
            logger.debug(f"Failed to analyze {file_path}: {e}")
        
        return issues
    
    def _check_nested_loops(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Check for deeply nested loops."""
        issues = []
        
        def count_loop_depth(node, depth=0):
            if isinstance(node, (ast.For, ast.While)):
                depth += 1
                if depth >= 3:
                    issues.append({
                        "type": "nested_loops",
                        "file": file_path,
                        "line": node.lineno,
                        "description": f"Nested loops at depth {depth} - consider optimization",
                        "severity": "warning" if depth == 3 else "error"
                    })
            
            for child in ast.iter_child_nodes(node):
                count_loop_depth(child, depth)
        
        count_loop_depth(tree)
        return issues
    
    def _check_list_operations(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Check for inefficient list operations."""
        issues = []
        
        for node in ast.walk(tree):
            # Check for list comprehension that could be generator
            if isinstance(node, ast.ListComp):
                # If list comp is only used in iteration context, suggest generator
                parent = getattr(node, 'parent', None)
                if parent and isinstance(parent, (ast.For, ast.Call)):
                    issues.append({
                        "type": "list_comprehension",
                        "file": file_path,
                        "line": node.lineno,
                        "description": "List comprehension could be generator expression for better memory efficiency",
                        "severity": "info"
                    })
            
            # Check for repeated list.append in loop
            if isinstance(node, ast.For):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute):
                            if child.func.attr == 'append':
                                # This is fine, but if it's complex, suggest list comp
                                pass
        
        return issues
    
    def _check_global_usage(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Check for global variable usage in functions."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Global):
                        issues.append({
                            "type": "global_variable",
                            "file": file_path,
                            "line": child.lineno,
                            "description": f"Global variable usage in function '{node.name}' - consider passing as parameter",
                            "severity": "warning"
                        })
        
        return issues
    
    def _check_string_concat(self, tree: ast.AST, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check for string concatenation in loops."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # Look for += operations on strings
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign):
                        if isinstance(child.op, ast.Add):
                            # Check if it's a string operation (heuristic)
                            try:
                                line_content = content.split('\n')[child.lineno - 1]
                                if '+=' in line_content and ('"' in line_content or "'" in line_content):
                                    issues.append({
                                        "type": "string_concatenation",
                                        "file": file_path,
                                        "line": child.lineno,
                                        "description": "String concatenation in loop - consider using list and join()",
                                        "severity": "warning"
                                    })
                            except:
                                pass
        
        return issues
    
    def _count_by_type(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by type."""
        counts = {}
        for issue in issues:
            issue_type = issue.get('type', 'unknown')
            counts[issue_type] = counts.get(issue_type, 0) + 1
        return counts
