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
            
            # Run tests and coverage
            test_results = self._run_tests_and_coverage(project_path, venv_python)
            
            # Collect test names
            test_list = self._collect_test_names(project_path, venv_python)
            
            result = {
                "test_files": [str(f.relative_to(project_path)) for f in test_files],
                "total_test_files": len(test_files),
                "has_unit_tests": has_unit,
                "has_integration_tests": has_integration,
                "has_e2e_tests": has_e2e,
                "coverage_percent": test_results["coverage_percent"],
                "coverage_report": test_results["coverage_report"],
                "tests_passed": test_results["tests_passed"],
                "tests_failed": test_results["tests_failed"],
                "tests_skipped": test_results["tests_skipped"],
                "test_list": test_list,  # List of test names
            }
            
            # Add warning if present
            if test_results.get("warning"):
                result["warning"] = test_results["warning"]
            
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
            cmd = [
                python_cmd, '-m', 'pytest', '--collect-only', '-q', '--color=no',
                '--ignore=node_modules', '--ignore=venv', '--ignore=.venv',
                '--ignore=dist', '--ignore=build', '--ignore=.git',
                '--ignore=frontend', '--ignore=playwright-report', '--ignore=test-results'
            ]
            
            logger.info(f"Collecting tests with command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # Increased from 30s to handle larger test suites (140+ tests)
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
    
    def _run_tests_and_coverage(self, project_path: Path, venv_python: Path) -> Dict[str, Any]:
        """
        Run tests and coverage analysis.
        
        FIXED: Robust coverage parsing that handles multiple formats and edge cases.
        """
        result_dict = {
            "coverage_percent": 0,
            "coverage_report": "",
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "warning": None
        }

        # Skip coverage/execution in test mode to avoid hanging
        if os.environ.get('PYTEST_CURRENT_TEST'):
            logger.debug("Skipping test execution during pytest run")
            return result_dict

        try:
            # Quick check: if no test files found, return immediately
            test_files = self._find_test_files(project_path)
            if not test_files:
                logger.debug("No test files found, skipping execution")
                return result_dict

            # Set PYTHONPATH
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_path)

            python_cmd = str(venv_python)

            # Command to run tests AND coverage
            cmd = [
                python_cmd,
                '-m', 'pytest',
                str(project_path),
                '--cov=.',
                '--cov-report=term-missing',
                '-q',
                '--color=no',
                '--ignore=node_modules',
                '--ignore=venv',
                '--ignore=.venv',
                '--ignore=dist',
                '--ignore=build',
                '--ignore=.git',
                '--ignore=frontend',
                '--ignore=playwright-report',
                '--ignore=test-results',
                '--ignore=test_results.txt'
            ]

            logger.info(f"Running test & coverage command: {' '.join(cmd)}")

            run_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=project_path,
                env=env
            )

            output = run_result.stdout + "\n" + run_result.stderr

            # ============================================================
            # 1. Parse Test Results (Passed/Failed/Skipped)
            # ============================================================
            lines = run_result.stdout.strip().splitlines()
            summary_found = False

            for line in reversed(lines[-20:]):
                if (
                    line.startswith('=') and line.endswith('=') and
                    ('passed' in line or 'failed' in line or 'skipped' in line or 'no tests ran' in line)
                ):
                    p = re.search(r'(\d+) passed', line)
                    f = re.search(r'(\d+) failed', line)
                    s = re.search(r'(\d+) skipped', line)

                    if p:
                        result_dict["tests_passed"] = int(p.group(1))
                    if f:
                        result_dict["tests_failed"] = int(f.group(1))
                    if s:
                        result_dict["tests_skipped"] = int(s.group(1))

                    summary_found = True
                    logger.debug(f"Found test summary line: {line}")
                    break

            if not summary_found:
                logger.debug("Summary line not found in stdout tail, searching combined output")
                lines = output.strip().splitlines()
                for line in reversed(lines[-20:]):
                    if (
                        line.startswith('=') and line.endswith('=') and
                        ('passed' in line or 'failed' in line or 'skipped' in line)
                    ):
                        p = re.search(r'(\d+) passed', line)
                        f = re.search(r'(\d+) failed', line)
                        s = re.search(r'(\d+) skipped', line)

                        if p:
                            result_dict["tests_passed"] = int(p.group(1))
                        if f:
                            result_dict["tests_failed"] = int(f.group(1))
                        if s:
                            result_dict["tests_skipped"] = int(s.group(1))
                        break

            # ============================================================
            # 2. Parse Coverage - ROBUST MULTI-FORMAT DETECTION
            # ============================================================
            
            # Check for common errors first
            if "No module named" in run_result.stderr:
                if "pytest_cov" in run_result.stderr or "coverage" in run_result.stderr:
                    error_msg = (
                        "⚠️ MISSING PREREQUISITE: 'pytest-cov' is not installed in the "
                        "target project. Coverage cannot be calculated."
                    )
                    logger.warning(error_msg)
                    result_dict["warning"] = error_msg

            # Try multiple regex patterns for coverage percentage
            coverage_patterns = [
                r"TOTAL\s+\d+\s+\d+\s+(\d+)%",           # Standard format
                r"TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)%",  # With branches
                r"TOTAL.*?(\d+)%",                       # Flexible format
                r"coverage:\s*(\d+)%",                   # Alternative format
                r"(\d+)%\s+coverage",                    # Reversed format
            ]
            
            coverage_percent = None
            for pattern in coverage_patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    coverage_percent = int(match.group(1))
                    logger.info(f"Found coverage {coverage_percent}% using pattern: {pattern}")
                    break
            
            # If still no match, try to find ANY percentage near "TOTAL" or "coverage"
            if coverage_percent is None:
                # Look for lines containing both a percentage and keywords
                for line in output.splitlines():
                    line_lower = line.lower()
                    if ('total' in line_lower or 'coverage' in line_lower):
                        percent_match = re.search(r'(\d+)%', line)
                        if percent_match:
                            coverage_percent = int(percent_match.group(1))
                            logger.info(f"Found coverage {coverage_percent}% in line: {line.strip()}")
                            break
            
            result_dict["coverage_percent"] = coverage_percent if coverage_percent is not None else 0
            
            if coverage_percent is None:
                logger.warning(f"Could not parse coverage from output. First 500 chars:\n{output[:500]}")

            # Extract full coverage report table
            coverage_match = re.search(
                r'(Name\s+Stmts\s+Miss.*?TOTAL.*?\d+%)',
                output,
                re.DOTALL
            )
            if coverage_match:
                result_dict["coverage_report"] = coverage_match.group(1).strip()
            elif result_dict["coverage_percent"] == 0:
                result_dict["coverage_report"] = output[-300:]

            return result_dict

        except subprocess.TimeoutExpired:
            logger.warning("Test analysis timed out (300s limit)")
            result_dict["warning"] = "Warning: Test analysis timed out"
            return result_dict

        except Exception as e:
            logger.error(f"Test analysis failed: {e}", exc_info=True)
            result_dict["warning"] = f"Warning: Test analysis failed - {str(e)}"
            return result_dict
