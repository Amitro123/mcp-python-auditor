"""Cleanup analysis tool - Find cache directories and reclaimable space."""
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class CleanupTool(BaseTool):
    """Scan for cleanup opportunities (cache dirs, temp files)."""

    # Cache directories to scan for
    CLEANUP_TARGETS = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".coverage",
        "htmlcov",
        "*.egg-info",
    }

    @property
    def description(self) -> str:
        return "Scans for cache directories and reclaimable disk space"

    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Scan for cleanup opportunities.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with cleanup targets and total reclaimable size
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}

        try:
            cleanup_counts = {target: 0 for target in self.CLEANUP_TARGETS if '*' not in target}
            total_size_bytes = 0
            items_found: List[str] = []

            # Use case-insensitive exclusions for Windows compatibility
            exclude_lower = {d.lower() for d in self.IGNORED_DIRECTORIES}

            for pattern in self.CLEANUP_TARGETS:
                for item in project_path.glob(f"**/{pattern}"):
                    # Skip if path contains excluded directories
                    item_str = str(item).lower()
                    if any(excl in item_str for excl in exclude_lower):
                        continue

                    if item.is_dir():
                        size = self._get_dir_size(item)
                        if pattern in cleanup_counts:
                            cleanup_counts[pattern] += 1
                        total_size_bytes += size
                        try:
                            items_found.append(str(item.relative_to(project_path)))
                        except ValueError:
                            items_found.append(str(item))
                    elif item.is_file():
                        try:
                            total_size_bytes += item.stat().st_size
                            items_found.append(str(item.relative_to(project_path)))
                        except (OSError, ValueError):
                            pass

            return {
                "tool": "cleanup",
                "status": "cleanup_available" if total_size_bytes > 0 else "clean",
                "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                "total_size_bytes": total_size_bytes,
                "cleanup_targets": {k: v for k, v in cleanup_counts.items() if v > 0},
                "items": items_found[:20],
                "total_items": len(items_found)
            }
        except Exception as e:
            logger.error(f"Cleanup scan failed: {e}")
            return {"tool": "cleanup", "status": "error", "error": str(e)}

    def _get_dir_size(self, path: Path) -> int:
        """Calculate total size of a directory."""
        total = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    try:
                        total += item.stat().st_size
                    except OSError:
                        pass
        except (OSError, PermissionError):
            pass
        return total
