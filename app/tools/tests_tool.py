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
            coverage_percent, coverage_warning = self._get_coverage(project_path, venv_python)
            
            result = {
                "test_files": [str(f.relative_to(project_path)) for f in test_files],
                "total_test_files": len(test_files),
                "has_unit_tests": has_unit,
                "has_integration_tests": has_integration,
                "has_e2e_tests": has_e2e,
                "coverage_percent": coverage_percent
            }
            
            # Add warning if venv not found
            if coverage_warning:
                result["warning"] = coverage_warning
            
            return result
        except Exception as e:
            logger.error(f"Tests analysis failed: {e}")
            return {"error": str(e)}
    
    def _find_test_files(self, path: Path) -> List[Path]:
        """Find all test files."""
        test_files = []
        
        # Look for test_*.py and *_test.py files
        for pattern in ['test_*.py', '*_test.py']:
            test_files.extend(path.rglob(pattern))
        
        # Also look in tests/ directories
        for test_dir in path.rglob('tests'):
            if test_dir.is_dir():
                test_files.extend(test_dir.rglob('*.py'))
        
        # Remove duplicates
        return list(set(test_files))
    
    def _has_test_type(self, test_files: List[Path], test_type: str) -> bool:
        """Check if project has specific test type."""
        for test_file in test_files:
            if test_type in str(test_file).lower():
                return True
        return False
    
    def _detect_venv_python(self, project_path: Path) -> Optional[Path]:
        """Detect virtual environment Python interpreter."""
        venv_dirs = ['.venv', 'venv', 'env']
        
        for venv_name in venv_dirs:
            venv_path = project_path / venv_name
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
        
        logger.debug("No virtual environment found")
        return None
    
    def _get_coverage(self, project_path: Path, venv_python: Optional[Path] = None) -> tuple[int, Optional[str]]:
        """Try to get test coverage percentage.
        
        Returns:
            Tuple of (coverage_percent, warning_message)
        """
        # Skip coverage in test mode to avoid hanging
        if os.environ.get('PYTEST_CURRENT_TEST'):
            logger.debug("Skipping coverage during pytest run")
            return 0, None
        
        try:
            # Quick check: if no test files found, return 0 immediately
            test_files = self._find_test_files(project_path)
            if not test_files:
                logger.debug("No test files found, skipping coverage")
                return 0, None
            
            # Set PYTHONPATH to ensure coverage can find modules
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_path)
            
            # Determine which Python to use
            warning = None
            if venv_python:
                # Use project's venv Python
                python_cmd = str(venv_python)
                logger.info(f"Using venv Python: {python_cmd}")
                
                # Verify pytest is available in venv
                check_result = subprocess.run(
                    [python_cmd, '-m', 'pytest', '--version'],
                    capture_output=True,
                    timeout=5,
                    cwd=project_path
                )
                if check_result.returncode != 0:
                    logger.warning("pytest not found in venv, falling back to system pytest")
                    python_cmd = 'coverage'
                    warning = "Warning: pytest not found in project venv"
            else:
                # Fall back to system coverage
                python_cmd = 'coverage'
                warning = "Warning: No virtual environment found. Coverage may be inaccurate."
            
            # Try running coverage with shorter timeout
            if venv_python and python_cmd != 'coverage':
                # Use venv Python with coverage module
                cmd = [python_cmd, '-m', 'coverage', 'run', '-m', 'pytest', '--tb=no', '-q']
            else:
                # Use system coverage command
                cmd = ['coverage', 'run', '-m', 'pytest', '--tb=no', '-q']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # Reduced from 120s to 30s
                cwd=project_path,
                env=env
            )
            
            # Get coverage report
            if result.returncode == 0 or result.returncode == 5:  # 5 = no tests collected
                if venv_python and python_cmd != 'coverage':
                    report_cmd = [python_cmd, '-m', 'coverage', 'report', '--precision=0']
                else:
                    report_cmd = ['coverage', 'report', '--precision=0']
                
                report_result = subprocess.run(
                    report_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,  # Reduced from 30s to 10s
                    cwd=project_path,
                    env=env
                )
                
                # Parse coverage percentage from output
                # Look for "TOTAL" line
                for line in report_result.stdout.split('\n'):
                    if 'TOTAL' in line:
                        # Extract percentage (last column)
                        match = re.search(r'(\d+)%', line)
                        if match:
                            return int(match.group(1)), warning
        
        except subprocess.TimeoutExpired:
            logger.warning("Coverage analysis timed out (30s limit)")
        except FileNotFoundError:
            logger.debug("coverage or pytest not available")
        except Exception as e:
            logger.debug(f"Coverage analysis failed: {e}")
        
        return 0, "Warning: Coverage analysis failed"

