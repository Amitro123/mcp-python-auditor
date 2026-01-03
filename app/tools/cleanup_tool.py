"""Cleanup detection tool - Find cache and temporary files."""
from pathlib import Path
from typing import Dict, Any, List
import os
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class CleanupTool(BaseTool):
    """Detect cache files and directories that can be cleaned up."""
    
    @property
    def description(self) -> str:
        return "Detects cache files, temporary directories, and other cleanable items"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project for cleanup opportunities.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with cleanup recommendations
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            # Patterns that should be grouped (cache directories)
            cache_patterns = [
                '__pycache__',
                '.pytest_cache',
                '.mypy_cache',
                '.ruff_cache',
                '.coverage',
                'htmlcov',
                '.tox',
                '.nox'
            ]
            
            # Patterns that should be listed individually
            individual_patterns = [
                'node_modules',
                '.next',
                'dist',
                'build',
                '*.egg-info',
                'venv',
                '.venv',
                'env',
                '.env.local',
                '*.pyc',
                '*.pyo',
                '*.pyd',
                '.DS_Store',
                'Thumbs.db',
                '*.log',
                'npm-debug.log*',
                'yarn-debug.log*',
                'yarn-error.log*'
            ]
            
            items = []
            total_size = 0
            
            # Process cache directories (grouped) using os.walk to prevent recursion
            cache_found = {pattern: {'files': 0, 'size': 0} for pattern in cache_patterns}
            
            for root, dirs, files in os.walk(project_path):
                # Check if current directory matches any cache pattern
                root_name = Path(root).name
                
                for pattern in cache_patterns:
                    if pattern in dirs:
                        # Found a cache directory - calculate its size
                        cache_path = Path(root) / pattern
                        size_bytes = self._get_dir_size(cache_path)
                        file_count = sum(1 for _ in cache_path.rglob('*') if _.is_file())
                        
                        cache_found[pattern]['files'] += file_count
                        cache_found[pattern]['size'] += size_bytes
                        
                        # CRITICAL: Remove from dirs to prevent recursion
                        dirs.remove(pattern)
            
            # Add grouped cache summaries
            for pattern, data in cache_found.items():
                if data['files'] > 0:
                    size_mb = data['size'] / (1024 * 1024)
                    items.append({
                        "path": f"{pattern} (Found {data['files']} files, {size_mb:.1f}MB)",
                        "type": "cache_group",
                        "size_mb": size_mb,
                        "recommendation": "Run pyclean . or remove manually"
                    })
                    total_size += size_mb
            
            # Process individual patterns
            for pattern in individual_patterns:
                if pattern.startswith('*.'):
                    # File pattern
                    ext = pattern[1:]
                    for file in project_path.rglob(f'*{ext}'):
                        if file.is_file():
                            size_mb = file.stat().st_size / (1024 * 1024)
                            items.append({
                                "path": str(file.relative_to(project_path)),
                                "type": "file",
                                "size_mb": size_mb
                            })
                            total_size += size_mb
                else:
                    # Directory pattern
                    for dir_path in project_path.rglob(pattern):
                        if dir_path.is_dir():
                            size_mb = self._get_dir_size(dir_path) / (1024 * 1024)
                            items.append({
                                "path": str(dir_path.relative_to(project_path)),
                                "type": "directory",
                                "size_mb": size_mb
                            })
                            total_size += size_mb
            
            # Sort by size (largest first)
            items.sort(key=lambda x: x['size_mb'], reverse=True)
            
            return {
                "items": items,
                "total_items": len(items),
                "total_size_mb": total_size
            }
        except Exception as e:
            logger.error(f"Cleanup analysis failed: {e}")
            return {"error": str(e)}
    
    def _get_dir_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes."""
        total = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except:
                        pass
        except:
            pass
        return total
