"""Architecture analysis tool - FastAPI/Python best practices via AST."""
import ast
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class ArchitectureTool(BaseTool):
    """Analyze project architecture and best practices."""
    
    @property
    def description(self) -> str:
        return "Analyzes FastAPI/Python architecture and best practices using AST"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project architecture.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with architecture issues and recommendations
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            issues = []
            
            # Check for standard Python project structure
            issues.extend(self._check_project_structure(project_path))
            
            # Check for FastAPI-specific structure
            issues.extend(self._check_fastapi_structure(project_path))
            
            # Check for circular imports
            issues.extend(self._check_circular_imports(project_path))
            
            # Check for proper separation of concerns
            issues.extend(self._check_separation_of_concerns(project_path))
            
            return {
                "issues": issues,
                "total_issues": len(issues),
                "severity_counts": self._count_by_severity(issues)
            }
        except Exception as e:
            logger.error(f"Architecture analysis failed: {e}")
            return {"error": str(e)}
    
    def _check_project_structure(self, path: Path) -> List[Dict[str, Any]]:
        """Check for standard Python project structure."""
        issues = []
        
        # Check for src/ or app/ layout
        has_src = (path / "src").exists()
        has_app = (path / "app").exists()
        
        if not has_src and not has_app:
            issues.append({
                "severity": "warning",
                "title": "No src/ or app/ layout detected",
                "description": "Consider organizing code in src/ or app/ directory",
                "category": "structure"
            })
        
        # Check for tests directory
        has_tests = (path / "tests").exists() or (path / "test").exists()
        if not has_tests:
            issues.append({
                "severity": "error",
                "title": "No tests/ directory found",
                "description": "Missing tests directory - testing is essential",
                "category": "structure"
            })
        
        # Check for requirements.txt or pyproject.toml
        # Simple, unbreakable check - no glob needed
        req_file = path / "requirements.txt"
        toml_file = path / "pyproject.toml"
        
        has_requirements = req_file.exists()
        has_pyproject = toml_file.exists()
        
        if not has_requirements and not has_pyproject:
            issues.append({
                "severity": "error",
                "title": "No dependency file found",
                "description": "Missing requirements.txt or pyproject.toml",
                "category": "structure"
            })
        
        return issues
    
    def _check_fastapi_structure(self, path: Path) -> List[Dict[str, Any]]:
        """Check for FastAPI-specific structure."""
        issues = []
        
        # Look for FastAPI imports in Python files
        has_fastapi = False
        for py_file in path.rglob("*.py"):
            if self._file_contains_fastapi(py_file):
                has_fastapi = True
                break
        
        if not has_fastapi:
            return issues  # Not a FastAPI project
        
        # Check for routers/ directory
        app_dir = path / "app" if (path / "app").exists() else path / "src"
        if app_dir.exists():
            if not (app_dir / "routers").exists() and not (app_dir / "routes").exists():
                issues.append({
                    "severity": "warning",
                    "title": "No routers/ directory in FastAPI app",
                    "description": "Consider organizing endpoints in routers/",
                    "category": "fastapi"
                })
            
            # Check for models/ or schemas/
            if not (app_dir / "models").exists() and not (app_dir / "schemas").exists():
                issues.append({
                    "severity": "warning",
                    "title": "No models/ or schemas/ directory",
                    "description": "Consider separating Pydantic models",
                    "category": "fastapi"
                })
            
            # Check for services/ or core/
            if not (app_dir / "services").exists() and not (app_dir / "core").exists():
                issues.append({
                    "severity": "info",
                    "title": "No services/ or core/ directory",
                    "description": "Consider separating business logic",
                    "category": "fastapi"
                })
        
        return issues
    
    def _check_circular_imports(self, path: Path) -> List[Dict[str, Any]]:
        """Check for potential circular imports."""
        issues = []
        import_graph = {}
        
        # Build import graph
        for py_file in path.rglob("*.py"):
            if any(p in py_file.parts for p in ['__pycache__', '.venv', 'venv']):
                continue
            
            try:
                imports = self._extract_imports(py_file)
                relative_path = str(py_file.relative_to(path))
                import_graph[relative_path] = imports
            except Exception as e:
                logger.debug(f"Failed to parse {py_file}: {e}")
        
        # Simple circular import detection (A imports B, B imports A)
        for file, imports in import_graph.items():
            for imported in imports:
                if imported in import_graph:
                    if file in import_graph[imported]:
                        issues.append({
                            "severity": "error",
                            "title": "Circular import detected",
                            "description": f"{file} ↔ {imported}",
                            "category": "imports",
                            "file": file
                        })
        
        return issues
    
    def _check_separation_of_concerns(self, path: Path) -> List[Dict[str, Any]]:
        """Check for proper separation of concerns."""
        issues = []
        
        for py_file in path.rglob("*.py"):
            if any(p in py_file.parts for p in ['__pycache__', '.venv', 'test']):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                # Check if file has both FastAPI routes and database logic
                has_routes = False
                has_db_logic = False
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check for route decorators
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Attribute):
                                if decorator.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                    has_routes = True
                        
                        # Check for database operations in function body
                        for child in ast.walk(node):
                            if isinstance(child, ast.Name):
                                if child.id in ['session', 'db', 'query', 'execute']:
                                    has_db_logic = True
                
                if has_routes and has_db_logic:
                    issues.append({
                        "severity": "warning",
                        "title": "Mixed concerns in route handler",
                        "description": "Route handler contains database logic - consider using services",
                        "category": "separation",
                        "file": str(py_file.relative_to(path))
                    })
            
            except Exception as e:
                logger.debug(f"Failed to analyze {py_file}: {e}")
        
        return issues
    
    def _file_contains_fastapi(self, file_path: Path) -> bool:
        """Check if file imports FastAPI."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return 'from fastapi' in content or 'import fastapi' in content
        except:
            return False
    
    def _extract_imports(self, file_path: Path) -> List[str]:
        """Extract import statements from a Python file."""
        imports = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except:
            pass
        
        return imports
    
    def _count_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {"error": 0, "warning": 0, "info": 0}
        for issue in issues:
            severity = issue.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
        return counts
