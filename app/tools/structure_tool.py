"""Structure analysis tool - Directory tree and file statistics."""
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class StructureTool(BaseTool):
    """Analyze project directory structure and file organization."""
    
    @property
    def description(self) -> str:
        return "Analyzes project directory structure and generates file statistics"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project structure.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with tree structure and file counts
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            tree = self._generate_tree(project_path, max_depth=4)
            file_counts = self._count_files_by_extension(project_path)
            total_files = sum(file_counts.values())
            
            return {
                "tree": tree,
                "file_counts": file_counts,
                "total_files": total_files,
                "total_dirs": self._count_directories(project_path)
            }
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            return {"error": str(e)}
    
    def _generate_tree(self, path: Path, prefix: str = "", max_depth: int = 4, current_depth: int = 0) -> str:
        """Generate directory tree string."""
        if current_depth >= max_depth:
            return ""
        
        tree_lines = []
        
        try:
            # Get all items, sorted (directories first, then files)
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            
            # Filter using centralized blacklist from BaseTool
            items = [
                item for item in items
                if item.name not in self.IGNORED_DIRECTORIES and not item.name.startswith('.')
            ]
            
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                
                if item.is_dir():
                    tree_lines.append(f"{prefix}{current_prefix}📁 {item.name}/")
                    
                    # Recursively add subdirectory contents
                    extension = "    " if is_last else "│   "
                    subtree = self._generate_tree(
                        item,
                        prefix + extension,
                        max_depth,
                        current_depth + 1
                    )
                    if subtree:
                        tree_lines.append(subtree)
                else:
                    icon = self._get_file_icon(item.suffix)
                    tree_lines.append(f"{prefix}{current_prefix}{icon} {item.name}")
        
        except PermissionError:
            tree_lines.append(f"{prefix}[Permission Denied]")
        
        return "\n".join(tree_lines)
    
    def _get_file_icon(self, extension: str) -> str:
        """Get emoji icon for file type."""
        icon_map = {
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.json': '📋',
            '.md': '📝',
            '.txt': '📄',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.toml': '⚙️',
            '.ini': '⚙️',
            '.env': '🔐',
            '.sh': '🔧',
            '.dockerfile': '🐳',
        }
        return icon_map.get(extension.lower(), '📄')
    
    def _count_files_by_extension(self, path: Path) -> Dict[str, int]:
        """Count files by extension."""
        counts = defaultdict(int)
        
        for item in path.rglob('*'):
            if item.is_file():
                # Use centralized blacklist from BaseTool
                if any(p in item.parts for p in self.IGNORED_DIRECTORIES):
                    continue
                
                ext = item.suffix if item.suffix else '[no extension]'
                counts[ext] += 1
        
        return dict(counts)
    
    def _count_directories(self, path: Path) -> int:
        """Count total directories."""
        count = 0
        for item in path.rglob('*'):
            if item.is_dir():
                # Use centralized blacklist from BaseTool
                if any(p in item.parts for p in self.IGNORED_DIRECTORIES):
                    continue
                count += 1
        return count
