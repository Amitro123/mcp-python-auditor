"""Gitignore recommendations tool."""
from pathlib import Path
from typing import Dict, Any, List, Set
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class GitignoreTool(BaseTool):
    """Generate gitignore recommendations based on project structure."""
    
    @property
    def description(self) -> str:
        return "Generates gitignore recommendations based on detected files and patterns"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project and suggest gitignore patterns.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with gitignore suggestions
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            # Read existing gitignore if present
            existing_patterns = self._read_gitignore(project_path)
            
            # Detect patterns that should be ignored
            suggested_patterns = self._detect_patterns(project_path)
            
            # Find missing patterns
            missing_patterns = suggested_patterns - existing_patterns
            
            return {
                "suggestions": sorted(list(missing_patterns)),
                "existing_patterns": sorted(list(existing_patterns)),
                "total_suggestions": len(missing_patterns)
            }
        except Exception as e:
            logger.error(f"Gitignore analysis failed: {e}")
            return {"error": str(e)}
    
    def _read_gitignore(self, path: Path) -> Set[str]:
        """Read existing gitignore patterns."""
        gitignore_path = path / '.gitignore'
        patterns = set()
        
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.add(line)
            except Exception as e:
                logger.debug(f"Failed to read .gitignore: {e}")
        
        return patterns
    
    def _detect_patterns(self, path: Path) -> Set[str]:
        """Detect patterns that should be in gitignore."""
        patterns = set()
        
        # Python-specific patterns
        if self._has_python_files(path):
            patterns.update([
                '__pycache__/',
                '*.py[cod]',
                '*$py.class',
                '*.so',
                '.Python',
                'build/',
                'develop-eggs/',
                'dist/',
                'downloads/',
                'eggs/',
                '.eggs/',
                'lib/',
                'lib64/',
                'parts/',
                'sdist/',
                'var/',
                'wheels/',
                '*.egg-info/',
                '.installed.cfg',
                '*.egg',
                'MANIFEST',
                '.pytest_cache/',
                '.coverage',
                'htmlcov/',
                '.tox/',
                '.nox/',
                'venv/',
                'env/',
                'ENV/',
                '.venv',
                '.mypy_cache/',
                '.ruff_cache/'
            ])
        
        # Node.js patterns
        if self._has_nodejs_files(path):
            patterns.update([
                'node_modules/',
                'npm-debug.log*',
                'yarn-debug.log*',
                'yarn-error.log*',
                '.npm',
                '.yarn',
                'dist/',
                'build/',
                '.next/',
                'out/'
            ])
        
        # Environment files
        if (path / '.env').exists() or (path / '.env.example').exists():
            patterns.update([
                '.env',
                '.env.local',
                '.env.*.local'
            ])
        
        # IDE patterns
        patterns.update([
            '.vscode/',
            '.idea/',
            '*.swp',
            '*.swo',
            '*~',
            '.DS_Store',
            'Thumbs.db'
        ])
        
        # Docker
        if (path / 'Dockerfile').exists() or (path / 'docker-compose.yml').exists():
            patterns.add('.dockerignore')
        
        # Data directories (common in ML/data projects)
        for data_dir in ['data/', 'datasets/', 'models/', 'checkpoints/']:
            if (path / data_dir.rstrip('/')).exists():
                patterns.add(data_dir)
        
        return patterns
    
    def _has_python_files(self, path: Path) -> bool:
        """Check if project has Python files."""
        for _ in path.rglob('*.py'):
            return True
        return False
    
    def _has_nodejs_files(self, path: Path) -> bool:
        """Check if project has Node.js files."""
        return (path / 'package.json').exists() or (path / 'node_modules').exists()
