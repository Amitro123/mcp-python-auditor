"""Tests analysis tool - Coverage and test organization."""
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import re
import os
import sys
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class TestsTool(BaseTool):
    """Analyze test coverage and organization."""
    
    @property
    def description(self) -> str:
        return "Analyzes test coverage, test organization, and test types (unit/integration/e2e)"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project tests.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with test analysis results
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            # Find test directories and files
            test_files = self._find_test_files(project_path)
            
            # Check for different test types
            has_unit = self._has_test_type(test_files, 'unit')
            has_integration = self._has_test_type(test_files, 'integration')
            has_e2e = self._has_test_type(test_files, 'e2e')
            
            # Detect virtual environment
            venv_python = self._detect_venv_python(project_path)
            
            # Try to get coverage if pytest is available
            coverage_percent, coverage_warning, coverage_table = self._get_coverage(project_path, venv_python)
            
            # Collect test names
            test_list = self._collect_test_names(project_path, venv_python)
            
            result = {
                "test_files": [str(f.relative_to(project_path)) for f in test_files],
                "total_test_files": len(test_files),
                "has_unit_tests": has_unit,
                "has_integration_tests": has_integration,
                "has_e2e_tests": has_e2e,
                "coverage_percent": coverage_percent,
                "test_list": test_list,  # List of test names
                "coverage_report": coverage_table  # NEW: Detailed coverage table
            }
            
            # Add warning if venv not found
            if coverage_warning:
                result["warning"] = coverage_warning
            
            return result
        except Exception as e:
            logger.error(f"Tests analysis failed: {e}")
            return {"error": str(e)}
    
    def _find_test_files(self, path: Path) -> List[Path]:
        """Find all test files (excluding __init__.py and conftest.py)."""
        test_files = []
        
        # Look for test_*.py and *_test.py files
        for pattern in ['test_*.py', '*_test.py']:
            for file in path.rglob(pattern):
                # Exclude non-test files
                if file.name not in ['__init__.py', 'conftest.py']:
                    test_files.append(file)
        
        # Remove duplicates
        return list(set(test_files))
    
    def _has_test_type(self, test_files: List[Path], test_type: str) -> bool:
        """Check if project has specific test type.
        
        With fallback: If no subdirectories for unit/integration/e2e exist,
        classify all root tests/ files as unit tests.
        """
        # First check if any files match the type in their path
        matching_files = [f for f in test_files if test_type in str(f).lower()]
        
        if matching_files:
            return True
        
        # Fallback for flat structure: if checking for 'unit' and NO type-specific
        # subdirectories exist, treat root tests/ as unit tests
        if test_type == 'unit':
            has_type_dirs = any(
                subtype in str(f).lower() 
                for f in test_files 
                for subtype in ['unit', 'integration', 'e2e']
            )
            
            if not has_type_dirs and test_files:
                # Flat structure detected - classify as unit tests
                return True
        
        return False
    
    def _detect_venv_python(self, project_path: Path) -> Path:
        """Detect virtual environment Python interpreter.
        
        Checks for venv in project directory and parent directory.
        Falls back to current interpreter if no venv found.
        """
        # Check both project directory and parent directory
        search_paths = [
            project_path,
            project_path.parent
        ]
        
        venv_dirs = ['.venv', 'venv', 'env']
        
        for base_path in search_paths:
            for venv_name in venv_dirs:
                venv_path = base_path / venv_name
                if not venv_path.exists():
                    continue
                
                # Check OS-specific Python executable location
                if sys.platform == 'win32':
                    python_exe = venv_path / 'Scripts' / 'python.exe'
                else:
                    python_exe = venv_path / 'bin' / 'python'
                
                if python_exe.exists():
                    logger.info(f"Found venv Python: {python_exe}")
                    return python_exe
        
        # Fallback to current interpreter
        logger.debug("No virtual environment found, using current interpreter")
        return Path(sys.executable)
    
    def _collect_test_names(self, project_path: Path, venv_python: Path) -> List[str]:
        """Collect all test names using pytest --collect-only.
        
        Returns:
            List of test IDs (e.g., 'tests/test_api.py::test_root')
        """
        try:
            python_cmd = str(venv_python)
            cmd = [python_cmd, '-m', 'pytest', '--collect-only', '-q', '--color=no']
            
            logger.info(f"Collecting tests with command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_path,
                errors='replace'
            )
            
            logger.debug(f"pytest collect output:\n{result.stdout}")
            
            # Parse test IDs from tree structure
            # Format: <Module test_api.py> followed by <Function test_name> or <Coroutine test_name>
            test_list = []
            current_module = None
            
            for line in result.stdout.splitlines():
                line = line.strip()
                
                # Extract module name
                if '<Module ' in line and '.py>' in line:
                    # Format: <Module test_api.py>
                    module_match = line.split('<Module ')[1].split('>')[0]
                    current_module = module_match
                
                # Extract test functions/coroutines
                elif current_module and ('<Function ' in line or '<Coroutine ' in line):
                    # Format: <Function test_name> or <Coroutine test_name>
                    if '<Function ' in line:
                        test_name = line.split('<Function ')[1].split('>')[0]
                    else:
                        test_name = line.split('<Coroutine ')[1].split('>')[0]
                    
                    # Build full test ID: tests/test_api.py::test_root_endpoint
                    test_id = f"tests/{current_module}::{test_name}"
                    test_list.append(test_id)
            
            logger.info(f"Collected {len(test_list)} tests")
            return test_list
            
        except Exception as e:
            logger.warning(f"Failed to collect test names: {e}")
            return []
    
    def _get_coverage(self, project_path: Path, venv_python: Path) -> tuple[int, Optional[str], str]:
        """Try to get test coverage percentage and detailed table.
        
        Returns:
            Tuple of (coverage_percent, warning_message, coverage_table)
        """
        # Skip coverage in test mode to avoid hanging
        if os.environ.get('PYTEST_CURRENT_TEST'):
            logger.debug("Skipping coverage during pytest run")
            return 0, None, ""
        
        try:
            # Quick check: if no test files found, return 0 immediately
            test_files = self._find_test_files(project_path)
            if not test_files:
                logger.debug("No test files found, skipping coverage")
                return 0, None, ""
            
            # Set PYTHONPATH to ensure coverage can find modules
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_path)
            
            # Use the provided Python interpreter (venv_python is now always set)
            python_cmd = str(venv_python)
            
            # Check if using current interpreter
            warning = None
            if python_cmd == sys.executable:
                logger.info("Using current interpreter for tests.")
            else:
                logger.info(f"Using venv Python: {python_cmd}")
            
            # Always include coverage flags
            cmd = [python_cmd, '-m', 'pytest', '--cov=.', '--cov-report=term-missing', '--tb=no', '-q', '--color=no']
            
            # Try running coverage with 3-minute timeout for heavy E2E tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=project_path,
                env=env
            )
            
            # Check for common errors
            if "No module named" in result.stderr:
                # Check specifically for pytest-cov missing
                if "pytest_cov" in result.stderr or "coverage" in result.stderr:
                    error_msg = "⚠️ MISSING PREREQUISITE: 'pytest-cov' is not installed in the target project. Coverage cannot be calculated."
                    logger.warning(error_msg)
                    return 0, error_msg, ""
                else:
                    error_msg = "Could not run coverage. Make sure 'pytest-cov' is installed in your project environment."
                    logger.warning(error_msg)
                    return 0, error_msg, ""
            
            # Allow exit code 0 (Success), 1 (Tests Failed), 2 (Collection Errors), 5 (No Tests Collected)
            if result.returncode in [0, 1, 2, 5]:
                # Combine stdout and stderr as coverage might be in either
                combined_output = result.stdout + "\n" + result.stderr
                
                # Extract the coverage table using regex (more robust)
                coverage_table = ""
                coverage_match = re.search(r'(Name\s+Stmts\s+Miss.*?TOTAL.*?\d+%)', combined_output, re.DOTALL)
                
                if coverage_match:
                    coverage_table = coverage_match.group(1).strip()
                else:
                    # Fallback: try line-by-line extraction
                    in_table = False
                    table_lines = []
                    
                    for line in combined_output.splitlines():
                        # Start capturing when we see the coverage table header
                        if line.strip().startswith('Name') and 'Stmts' in line:
                            in_table = True
                        
                        if in_table:
                            table_lines.append(line)
                            
                            # Stop after TOTAL line
                            if 'TOTAL' in line:
                                break
                    
                    if table_lines:
                        coverage_table = '\n'.join(table_lines)
                
                # Parse coverage percentage from combined output
                # Look for "TOTAL" line and extract percentage (robust to warnings/spacing)
                for line in result.stdout.splitlines():
                    if 'TOTAL' in line:
                        # Match TOTAL followed by any content, then capture final percentage
                        # This handles cases like: "TOTAL  2371  1923  19%"
                        match = re.search(r'TOTAL\s+.*?\s+(\d+)%', line)
                        if match:
                            coverage_pct = int(match.group(1))
                            logger.info(f"Coverage: {coverage_pct}%")
                            return coverage_pct, warning, coverage_table
        
        except subprocess.TimeoutExpired:
            logger.warning("Coverage analysis timed out (180s limit)")
            return 0, "Warning: Coverage analysis timed out (180s limit)", ""
        except FileNotFoundError:
            logger.debug("coverage or pytest not available")
            return 0, "Warning: coverage or pytest not available", ""
        except Exception as e:
            logger.debug(f"Coverage analysis failed: {e}")
            return 0, f"Warning: Coverage analysis failed - {str(e)}", ""
        
        return 0, "Warning: Coverage analysis failed", ""

