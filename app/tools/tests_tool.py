"""Tests analysis tool - Coverage and test organization."""
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import re
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
            
            # Try to get coverage if pytest is available
            coverage_percent = self._get_coverage(project_path)
            
            return {
                "test_files": [str(f.relative_to(project_path)) for f in test_files],
                "total_test_files": len(test_files),
                "has_unit_tests": has_unit,
                "has_integration_tests": has_integration,
                "has_e2e_tests": has_e2e,
                "coverage_percent": coverage_percent
            }
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
    
    def _get_coverage(self, project_path: Path) -> int:
        """Try to get test coverage percentage."""
        try:
            # Try running coverage
            result = subprocess.run(
                ['coverage', 'run', '-m', 'pytest', '--tb=no', '-q'],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=project_path
            )
            
            # Get coverage report
            if result.returncode == 0 or result.returncode == 5:  # 5 = no tests collected
                report_result = subprocess.run(
                    ['coverage', 'report', '--precision=0'],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=project_path
                )
                
                # Parse coverage percentage from output
                # Look for "TOTAL" line
                for line in report_result.stdout.split('\n'):
                    if 'TOTAL' in line:
                        # Extract percentage (last column)
                        match = re.search(r'(\d+)%', line)
                        if match:
                            return int(match.group(1))
        
        except subprocess.TimeoutExpired:
            logger.warning("Coverage analysis timed out")
        except FileNotFoundError:
            logger.debug("coverage or pytest not available")
        except Exception as e:
            logger.debug(f"Coverage analysis failed: {e}")
        
        return 0
