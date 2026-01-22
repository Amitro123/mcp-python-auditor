"""
Smart file filtering to skip irrelevant files and directories.
Speeds up tools by 50-80% by avoiding node_modules, venvs, etc.
"""
from pathlib import Path
from typing import List, Set
import logging

logger = logging.getLogger(__name__)


class FileFilter:
    """Filter files based on tool requirements and exclusion patterns."""
    
    # Universal excludes for ALL tools
    UNIVERSAL_EXCLUDES = {
        'node_modules', '.venv', 'venv', 'env', '.git',
        'dist', 'build', '__pycache__', '.pytest_cache',
        '.mypy_cache', '.ruff_cache', '.tox', '.eggs',
        'frontend', 'static', 'public', 'htmlcov',
        'playwright-report', 'test-results', '.next',
        'coverage_html_report', '.coverage', '.audit_cache'
    }
    
    # Tool-specific configurations
    TOOL_CONFIGS = {
        'bandit': {
            'include': ['**/*.py'],
            'exclude': ['**/test_*.py', '**/*_test.py', '**/conftest.py', '**/setup.py'],
            'description': 'Security checks on production code only (skip tests)'
        },
        'ruff': {
            'include': ['**/*.py'],
            'exclude': [],
            'description': 'Lint all Python files'
        },
        'tests': {
            'include': ['**/test_*.py', '**/*_test.py', '**/conftest.py'],
            'exclude': [],
            'description': 'Only test files'
        },
        'pip-audit': {
            'include': ['requirements.txt', 'requirements-*.txt', 'pyproject.toml', 'setup.py', 'Pipfile', 'Pipfile.lock'],
            'exclude': [],
            'description': 'Only dependency files'
        },
        'deadcode': {
            'include': ['**/*.py'],
            'exclude': ['**/test_*.py', '**/*_test.py', '**/conftest.py'],
            'description': 'Production code only (tests can have unused code)'
        },
        'duplication': {
            'include': ['**/*.py'],
            'exclude': [],
            'description': 'All Python files for duplication detection'
        },
        'structure': {
            'include': ['**/*.py'],
            'exclude': [],
            'description': 'All Python files for structure analysis'
        },
        'architecture': {
            'include': ['**/*.py'],
            'exclude': [],
            'description': 'All Python files for dependency analysis'
        },
        'efficiency': {
            'include': ['**/*.py'],
            'exclude': [],
            'description': 'All Python files for complexity analysis'
        }
    }
    
    def __init__(self, project_path: Path):
        """
        Initialize file filter.
        
        Args:
            project_path: Path to the project root
        """
        self.project_path = Path(project_path).resolve()
        
    def get_filtered_files(self, tool_name: str) -> List[Path]:
        """
        Get filtered list of files for a specific tool.
        
        Args:
            tool_name: Name of the tool (e.g., 'bandit', 'ruff')
            
        Returns:
            List of Path objects for relevant files
        """
        config = self.TOOL_CONFIGS.get(tool_name, {'include': ['**/*.py'], 'exclude': []})
        
        files = []
        total_found = 0
        total_excluded = 0
        
        for pattern in config['include']:
            for file in self.project_path.rglob(pattern):
                if not file.is_file():
                    continue
                    
                total_found += 1
                
                # Skip if in excluded directory
                if self._is_in_excluded_dir(file):
                    total_excluded += 1
                    continue
                
                # Skip if matches exclude pattern
                if any(file.match(exc) for exc in config['exclude']):
                    total_excluded += 1
                    continue
                
                files.append(file)
        
        logger.info(
            f"FileFilter[{tool_name}]: Found {total_found} files, "
            f"filtered to {len(files)} ({total_excluded} excluded)"
        )
        
        return files
    
    def _is_in_excluded_dir(self, file: Path) -> bool:
        """
        Check if file is inside an excluded directory.
        
        Args:
            file: Path to check
            
        Returns:
            True if file is in an excluded directory
        """
        return any(excluded in file.parts for excluded in self.UNIVERSAL_EXCLUDES)
    
    def get_stats(self, tool_name: str) -> dict:
        """
        Get filtering statistics for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Dictionary with filtering statistics
        """
        files = self.get_filtered_files(tool_name)
        config = self.TOOL_CONFIGS.get(tool_name, {})
        
        return {
            'total_files': len(files),
            'tool': tool_name,
            'config': config,
            'sample_files': [str(f.relative_to(self.project_path)) for f in files[:5]],
            'description': config.get('description', 'No description')
        }
    
    def get_all_stats(self) -> dict:
        """
        Get filtering statistics for all tools.
        
        Returns:
            Dictionary mapping tool names to their stats
        """
        return {
            tool_name: self.get_stats(tool_name)
            for tool_name in self.TOOL_CONFIGS.keys()
        }
