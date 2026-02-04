"""Cleanup analysis tool - Find cache directories and reclaimable space."""

import contextlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class CleanupTool(BaseTool):
    """Scan for cleanup opportunities (cache dirs, temp files, old reports)."""

    # Cache directories to scan for
    CACHE_TARGETS = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".coverage",
        "htmlcov",
        "*.egg-info",
    }

    # Temporary/debug file patterns
    TEMP_FILE_PATTERNS = {
        "test_*.py": "Test scripts",
        "debug_*.py": "Debug scripts",
        "verify_*.py": "Verification scripts",
        "analyze_*.py": "Analysis scripts",
        "test_*.json": "Test JSON files",
        "test_*.env": "Test environment files",
        "*.log": "Log files",
        "*.bak": "Backup files",
        "*.tmp": "Temporary files",
        "*.old": "Old files",
    }

    # Directories containing generated files
    GENERATED_DIRS = {
        "reports": "Audit reports",
        "htmlcov": "Coverage reports",
    }

    @property
    def description(self) -> str:
        return "Scans for cache directories, temporary files, and reclaimable disk space"

    def analyze(self, project_path: Path) -> dict[str, Any]:
        """Scan for cleanup opportunities.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with cleanup targets and total reclaimable size

        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}

        try:
            # Track different categories
            cache_items = []
            temp_files = []
            old_reports = []
            total_size_bytes = 0

            # Use case-insensitive exclusions for Windows compatibility
            exclude_lower = {d.lower() for d in self.IGNORED_DIRECTORIES}

            # 1. Scan for cache directories
            for pattern in self.CACHE_TARGETS:
                for item in project_path.glob(f"**/{pattern}"):
                    # Skip if path contains excluded directories
                    item_str = str(item).lower()
                    if any(excl in item_str for excl in exclude_lower):
                        continue

                    if item.is_dir():
                        size = self._get_dir_size(item)
                        total_size_bytes += size
                        try:
                            rel_path = str(item.relative_to(project_path))
                            cache_items.append(
                                {
                                    "path": rel_path,
                                    "type": "cache_dir",
                                    "size_mb": round(size / (1024 * 1024), 2),
                                }
                            )
                        except ValueError:
                            pass
                    elif item.is_file():
                        try:
                            size = item.stat().st_size
                            total_size_bytes += size
                            cache_items.append(
                                {
                                    "path": str(item.relative_to(project_path)),
                                    "type": "cache_file",
                                    "size_mb": round(size / (1024 * 1024), 2),
                                }
                            )
                        except (OSError, ValueError):
                            pass

            # 2. Scan for temporary/debug files
            for pattern, description in self.TEMP_FILE_PATTERNS.items():
                for item in project_path.glob(f"**/{pattern}"):
                    # Skip excluded directories and the tests/ directory for test_*.py
                    item_str = str(item).lower()
                    if any(excl in item_str for excl in exclude_lower):
                        continue

                    # Skip legitimate test files in tests/ directory
                    # Normalize path separators and check for tests directory
                    normalized_path = str(item).replace("\\", "/").lower()
                    if pattern == "test_*.py" and ("/tests/" in normalized_path or normalized_path.startswith("tests/")):
                        continue

                    # Also check relative path for tests directory
                    try:
                        rel_path = str(item.relative_to(project_path)).replace("\\", "/").lower()
                        if pattern == "test_*.py" and (rel_path.startswith("tests/") or "/tests/" in rel_path):
                            continue
                    except ValueError:
                        pass

                    if item.is_file():
                        try:
                            size = item.stat().st_size
                            total_size_bytes += size
                            temp_files.append(
                                {
                                    "path": str(item.relative_to(project_path)),
                                    "type": description,
                                    "size_mb": round(size / (1024 * 1024), 2),
                                }
                            )
                        except (OSError, ValueError):
                            pass

            # 3. Scan for old reports (older than 7 days)
            reports_dir = project_path / "reports"
            if reports_dir.exists() and reports_dir.is_dir():
                cutoff_date = datetime.now() - timedelta(days=7)
                for report_file in reports_dir.glob("*.md"):
                    try:
                        mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                        if mtime < cutoff_date:
                            size = report_file.stat().st_size
                            total_size_bytes += size
                            age_days = (datetime.now() - mtime).days
                            old_reports.append(
                                {
                                    "path": str(report_file.relative_to(project_path)),
                                    "type": "old_report",
                                    "age_days": age_days,
                                    "size_mb": round(size / (1024 * 1024), 2),
                                }
                            )
                    except (OSError, ValueError):
                        pass

            # Combine all items
            all_items = cache_items + temp_files + old_reports

            return {
                "tool": "cleanup",
                "status": "cleanup_available" if total_size_bytes > 0 else "clean",
                "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                "total_size_bytes": total_size_bytes,
                "cache_items": cache_items[:10],  # Top 10 cache items
                "temp_files": temp_files[:10],  # Top 10 temp files
                "old_reports": old_reports[:10],  # Top 10 old reports
                "summary": {
                    "cache_count": len(cache_items),
                    "temp_file_count": len(temp_files),
                    "old_report_count": len(old_reports),
                    "total_items": len(all_items),
                },
                "items": [item["path"] for item in all_items[:20]],  # For backward compatibility
                "total_items": len(all_items),
            }
        except Exception as e:
            logger.exception(f"Cleanup scan failed: {e}")
            return {"tool": "cleanup", "status": "error", "error": str(e)}

    def _get_dir_size(self, path: Path) -> int:
        """Calculate total size of a directory."""
        total = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    with contextlib.suppress(OSError):
                        total += item.stat().st_size
        except (OSError, PermissionError):
            pass
        return total
