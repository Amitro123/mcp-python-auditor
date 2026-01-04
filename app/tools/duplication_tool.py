"""Code duplication detection tool."""
import ast
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict
from rapidfuzz import fuzz
from app.core.base_tool import BaseTool
from app.core.config import ANALYSIS_EXCLUDES
import logging

logger = logging.getLogger(__name__)


class DuplicationTool(BaseTool):
    """Detect duplicate code patterns in Python files."""
    
    @property
    def description(self) -> str:
        return "Detects duplicate functions and code patterns using AST and fuzzy matching"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze code for duplicates.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with duplicate code information
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            # Extract all functions from the project
            functions = self._extract_functions(project_path)
            
            # Find duplicates
            duplicates = self._find_duplicates(functions)
            
            return {
                "duplicates": duplicates,
                "total_duplicates": len(duplicates),
                "total_functions_analyzed": len(functions)
            }
        except Exception as e:
            logger.error(f"Duplication analysis failed: {e}")
            return {"error": str(e)}
    
    def _extract_functions(self, path: Path) -> List[Dict[str, Any]]:
        """Extract all functions from Python files."""
        functions = []
        
        for py_file in path.rglob("*.py"):
            # Use centralized exclusion config
            if any(p in py_file.parts for p in ANALYSIS_EXCLUDES):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_info = self._extract_function_info(node, py_file, path, content)
                        if func_info:
                            functions.append(func_info)
            
            except Exception as e:
                logger.debug(f"Failed to parse {py_file}: {e}")
        
        return functions
    
    def _extract_function_info(
        self,
        node: ast.FunctionDef,
        file_path: Path,
        project_path: Path,
        file_content: str
    ) -> Dict[str, Any]:
        """Extract information about a function."""
        try:
            # Get function source code
            func_lines = file_content.split('\n')[node.lineno - 1:node.end_lineno]
            func_source = '\n'.join(func_lines)
            
            # Normalize the source (remove comments, docstrings, whitespace)
            normalized = self._normalize_code(func_source)
            
            # Create hash of normalized code
            code_hash = hashlib.md5(normalized.encode()).hexdigest()
            
            return {
                "name": node.name,
                "file": str(file_path.relative_to(project_path)),
                "line": node.lineno,
                "source": func_source,
                "normalized": normalized,
                "hash": code_hash,
                "length": len(func_lines)
            }
        except Exception as e:
            logger.debug(f"Failed to extract function info: {e}")
            return None
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code by removing comments, docstrings, and extra whitespace."""
        try:
            tree = ast.parse(code)
            
            # Remove docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                    if (ast.get_docstring(node)):
                        node.body = node.body[1:] if len(node.body) > 1 else node.body
            
            # Convert back to code (this removes comments automatically)
            import astor
            normalized = astor.to_source(tree)
            
            # Remove extra whitespace
            normalized = ' '.join(normalized.split())
            
            return normalized
        except:
            # Fallback: simple normalization
            lines = [line.strip() for line in code.split('\n')]
            lines = [line for line in lines if line and not line.startswith('#')]
            return ' '.join(lines)
    
    def _find_duplicates(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find duplicate functions."""
        duplicates = []
        
        # Group by hash for exact duplicates
        hash_groups = defaultdict(list)
        for func in functions:
            if func['length'] >= 3:  # Only consider functions with 3+ lines
                hash_groups[func['hash']].append(func)
        
        # Find exact duplicates
        for code_hash, funcs in hash_groups.items():
            if len(funcs) > 1:
                duplicates.append({
                    "function_name": funcs[0]['name'],
                    "similarity": 100,
                    "type": "exact",
                    "locations": [f"{f['file']}:{f['line']}" for f in funcs],
                    "count": len(funcs)
                })
        
        # Find similar functions (fuzzy matching)
        # Only check functions not already marked as exact duplicates
        processed_hashes = set(h for h, funcs in hash_groups.items() if len(funcs) > 1)
        remaining_functions = [f for f in functions if f['hash'] not in processed_hashes and f['length'] >= 5]
        
        # Compare pairs of functions
        for i, func1 in enumerate(remaining_functions):
            for func2 in remaining_functions[i + 1:]:
                # Skip if same file and similar names (likely overloads)
                if func1['file'] == func2['file'] and func1['name'] == func2['name']:
                    continue
                
                # Calculate similarity
                similarity = fuzz.ratio(func1['normalized'], func2['normalized'])
                
                if similarity >= 80:  # 80% similarity threshold
                    duplicates.append({
                        "function_name": f"{func1['name']} / {func2['name']}",
                        "similarity": similarity,
                        "type": "similar",
                        "locations": [
                            f"{func1['file']}:{func1['line']}",
                            f"{func2['file']}:{func2['line']}"
                        ],
                        "count": 2
                    })
        
        # Sort by similarity (highest first)
        duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        
        return duplicates
