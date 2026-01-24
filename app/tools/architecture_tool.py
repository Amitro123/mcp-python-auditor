"""Architecture analysis tool - FastAPI/Python best practices via AST."""
import ast
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)

# Standard library modules (for filtering imports in dependency graphs)
STDLIB_MODULES = {
    'os', 'sys', 'json', 'time', 'datetime', 'logging', 'pathlib', 're',
    'typing', 'collections', 'functools', 'itertools', 'copy', 'io',
    'abc', 'dataclasses', 'asyncio', 'concurrent', 'threading', 'multiprocessing',
    'subprocess', 'hashlib', 'uuid', 'base64', 'math', 'random', 'decimal',
    'fractions', 'statistics', 'array', 'bisect', 'heapq', 'queue',
    'enum', 'contextlib', 'warnings', 'traceback', 'inspect', 'shutil',
    'tempfile', 'glob', 'fnmatch', 'stat', 'struct', 'codecs', 'csv',
    'configparser', 'argparse', 'getopt', 'optparse', 'unittest', 'doctest',
    'pdb', 'profile', 'timeit', 'gc', 'platform', 'socket', 'http',
    'urllib', 'email', 'html', 'xml', 'ssl', 'ftplib', 'smtplib',
    'pickle', 'shelve', 'sqlite3', 'zlib', 'gzip', 'zipfile', 'tarfile',
    'textwrap', 'string', 'difflib', 'ctypes', 'types', 'operator',
    '__future__', 'builtins', 'importlib', 'pkgutil', 'pprint', 'secrets'
}


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
        # Use centralized file walker from BaseTool
        for py_file in self.walk_project_files(path):
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
        # Use centralized file walker from BaseTool
        for py_file in self.walk_project_files(path):
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
        
        # Use centralized file walker from BaseTool
        for py_file in self.walk_project_files(path):
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
        except Exception as e:
            logger.debug(f"Failed to extract imports from {file_path}: {e}")
        
        return imports
    
    def _count_by_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {"error": 0, "warning": 0, "info": 0}
        for issue in issues:
            severity = issue.get("severity", "info")
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def generate_dependency_graph(self, project_path: Path) -> Dict[str, Any]:
        """
        Generate a Mermaid.js dependency graph by parsing Python imports.
        Groups nodes into subgraphs by directory.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with mermaid_graph, total_files, total_dependencies, nodes
        """
        if not self.validate_path(project_path):
            return {"tool": "architecture", "status": "error", "error": "Invalid path"}

        try:
            # Collect Python files using base class walker
            py_files = list(self.walk_project_files(project_path))

            file_nodes, dependencies, nodes_by_group = self._parse_imports_for_graph(py_files, project_path)
            mermaid_graph = self._generate_mermaid_graph(nodes_by_group, dependencies)

            return {
                "tool": "architecture",
                "status": "analyzed",
                "total_files": len(py_files),
                "total_dependencies": len(dependencies),
                "mermaid_graph": mermaid_graph,
                "nodes": list(file_nodes)[:30]
            }
        except Exception as e:
            logger.error(f"Dependency graph generation failed: {e}")
            return {"tool": "architecture", "status": "error", "error": str(e)}

    def _parse_imports_for_graph(
        self, py_files: List[Path], root_path: Path
    ) -> Tuple[Set[str], List[Tuple[str, str]], Dict[str, Set[str]]]:
        """Parse imports from Python files for dependency graph visualization."""
        dependencies = []
        file_nodes: Set[str] = set()
        nodes_by_group: Dict[str, Set[str]] = defaultdict(set)

        for py_file in py_files[:50]:  # Limit to avoid huge graphs
            try:
                source_code = py_file.read_text(encoding='utf-8', errors='ignore')
                tree = ast.parse(source_code)

                try:
                    rel_path = py_file.relative_to(root_path)
                except ValueError:
                    rel_path = py_file.name

                source_name = str(rel_path).replace('\\', '/').replace('.py', '')
                file_nodes.add(source_name)

                parts = source_name.split('/')
                group = parts[0] if len(parts) > 1 else "root"
                nodes_by_group[group].add(source_name)

                for node in ast.walk(tree):
                    target_module = None
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            target_module = alias.name.split('.')[0]
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            target_module = node.module.split('.')[0]

                    if target_module and target_module not in STDLIB_MODULES:
                        if target_module in [f.stem for f in py_files] or '.' not in target_module:
                            dependencies.append((source_name, target_module))
            except (SyntaxError, UnicodeDecodeError):
                continue

        return file_nodes, dependencies, nodes_by_group

    def _generate_mermaid_graph(
        self, nodes_by_group: Dict[str, Set[str]], dependencies: List[Tuple[str, str]]
    ) -> str:
        """Generate a Mermaid graph string from nodes and dependencies."""
        mermaid_lines = ["graph TD"]

        for group_name, nodes in sorted(nodes_by_group.items()):
            if not nodes:
                continue
            display_name = group_name.replace('_', ' ').title()
            mermaid_lines.append(f"    subgraph {display_name}")
            for node in sorted(nodes):
                clean_node = node.replace('/', '_').replace('-', '_')
                mermaid_lines.append(f"        {clean_node}[{node}]")
            mermaid_lines.append("    end")

        seen_edges: Set[str] = set()
        for source, target in dependencies[:100]:
            edge = f"{source}-->{target}"
            if edge not in seen_edges and source != target:
                seen_edges.add(edge)
                clean_source = source.replace('/', '_').replace('-', '_')
                clean_target = target.replace('/', '_').replace('-', '_')
                mermaid_lines.append(f"    {clean_source} --> {clean_target}")

        if len(mermaid_lines) > 1:
            return "\n".join(mermaid_lines)
        return "graph TD\n    Note[No internal dependencies found]"
