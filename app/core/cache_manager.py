"""Cache Manager for Audit Tools.

Provides intelligent caching to speed up repeated audits by:
- Storing tool results with file hashes
- Validating cache based on file changes and age
- Invalidating cache when relevant files change
"""

import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for audit tool results."""

    def __init__(self, project_path: str, max_age_hours: int = 1):
        """Initialize cache manager.

        Args:
            project_path: Path to the project being audited
            max_age_hours: Maximum age of cache in hours (default: 1)

        """
        self.project_path = Path(project_path).resolve()
        self.cache_dir = self.project_path / ".audit_cache"
        self.max_age_seconds = max_age_hours * 3600

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)

        # Add to .gitignore if it exists
        self._update_gitignore()

        logger.debug(f"CacheManager initialized: {self.cache_dir}")

    def _update_gitignore(self):
        """Add .audit_cache to .gitignore if not already present."""
        gitignore_path = self.project_path / ".gitignore"

        try:
            if gitignore_path.exists():
                content = gitignore_path.read_text(encoding="utf-8")
                if ".audit_cache" not in content:
                    with open(gitignore_path, "a", encoding="utf-8") as f:
                        f.write("\n# Audit cache\n.audit_cache/\n")
                    logger.debug("Added .audit_cache to .gitignore")
        except Exception as e:
            logger.debug(f"Could not update .gitignore: {e}")

    def _get_cache_path(self, tool_name: str) -> Path:
        """Get cache file path for a specific tool."""
        return self.cache_dir / f"{tool_name}_cache.json"

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            MD5 hash as hex string

        """
        try:
            md5 = hashlib.md5()  # nosec
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.debug(f"Error hashing {file_path}: {e}")
            return ""

    def _get_files_hash(self, file_patterns: list[str]) -> dict[str, str]:
        """Get hash of all files matching the patterns.

        Optimized to walk the directory tree once and prune ignored directories early.
        """
        import os

        file_hashes = {}
        ignored_dirs = {"node_modules", ".venv", "venv", ".git", "__pycache__", ".pytest_cache", "dist", "build", ".audit_cache", ".idea", ".vscode"}

        # Windows reserved filenames that should never be hashed
        windows_reserved = {"nul", "con", "prn", "aux", "com1", "com2", "com3", "com4", "lpt1", "lpt2", "lpt3", "nul.", "con.", "prn.", "aux."}

        # Normalize patterns
        # Separate exact files from glob patterns to optimize finding specific files
        exact_files = [p for p in file_patterns if "*" not in p and "?" not in p]
        glob_patterns = [p for p in file_patterns if "*" in p or "?" in p]

        # 1. Handle exact files first (fastest)
        for rel_path_str in exact_files:
            file_path = self.project_path / rel_path_str
            if file_path.exists() and file_path.is_file():
                file_hashes[rel_path_str] = self._compute_file_hash(file_path)

        # 2. If we have glob patterns, walk the tree once
        if glob_patterns:
            base_path = str(self.project_path)

            for root, dirs, files in os.walk(base_path, topdown=True):
                # Modify dirs in-place to skip ignored directories
                # This prevents os.walk from entering them
                dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

                for filename in files:
                    # Skip Windows reserved filenames
                    if filename.lower() in windows_reserved:
                        continue

                    # Construct relative path
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, base_path)

                    # Check if file matches any pattern
                    # Convert path to forward slashes for matching if needed, but fnmatch usually handles OS specific
                    # For recursive globs like **/*.py, we need special handling if using simple fnmatch
                    # But simpler approach: check if it matches any pattern

                    matched = False
                    for pattern in glob_patterns:
                        # Handle recursive globs manually or assume simple patterns?
                        # fnmatch doesn't handle **/ correctly in all versions/platforms the way glob does.
                        # However, audit patterns are usually simple or recursive.

                        # Use Path.match logic which is robust
                        if Path(rel_path).match(pattern):
                            matched = True
                            break

                    if matched:
                        file_hashes[rel_path] = self._compute_file_hash(Path(full_path))

        return file_hashes

    def get_cached_result(self, tool_name: str, file_patterns: list[str]) -> dict[str, Any] | None:
        """Get cached result if valid.

        Args:
            tool_name: Name of the tool
            file_patterns: List of glob patterns for files this tool depends on

        Returns:
            Cached result dictionary if valid, None otherwise

        """
        cache_path = self._get_cache_path(tool_name)

        # Check if cache file exists
        if not cache_path.exists():
            logger.debug(f"No cache found for {tool_name}")
            return None

        try:
            # Load cache
            with open(cache_path, encoding="utf-8") as f:
                cache_data = json.load(f)

            # Validate cache structure
            required_keys = ["timestamp", "file_hashes", "result"]
            if not all(key in cache_data for key in required_keys):
                logger.warning(f"Invalid cache structure for {tool_name}")
                return None

            # Check age
            cache_age = time.time() - cache_data["timestamp"]
            if cache_age > self.max_age_seconds:
                logger.debug(f"Cache expired for {tool_name} (age: {cache_age:.0f}s)")
                return None

            # Check if files changed
            current_hashes = self._get_files_hash(file_patterns)
            cached_hashes = cache_data["file_hashes"]

            # Compare hashes
            if current_hashes != cached_hashes:
                logger.debug(f"Files changed for {tool_name}, cache invalid")
                # Log what changed for debugging
                changed_files = set(current_hashes.keys()) ^ set(cached_hashes.keys())
                if changed_files:
                    logger.debug(f"Changed files: {list(changed_files)[:5]}")
                return None

            # Cache is valid!
            logger.info(f"[CACHE] Using cached result for {tool_name} (age: {cache_age:.0f}s)")
            return cache_data["result"]

        except json.JSONDecodeError:
            logger.warning(f"Corrupted cache file for {tool_name}")
            return None
        except Exception as e:
            logger.debug(f"Error reading cache for {tool_name}: {e}")
            return None

    def save_result(self, tool_name: str, result: dict[str, Any], file_patterns: list[str]):
        """Save tool result to cache.

        Args:
            tool_name: Name of the tool
            result: Tool result dictionary
            file_patterns: List of glob patterns for files this tool depends on

        """
        cache_path = self._get_cache_path(tool_name)

        try:
            # Compute file hashes
            file_hashes = self._get_files_hash(file_patterns)

            # Create cache data
            cache_data = {
                "timestamp": time.time(),
                "file_hashes": file_hashes,
                "result": result,
                "tool_name": tool_name,
                "created_at": datetime.now().isoformat(),
            }

            # Save to file
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Saved cache for {tool_name} ({len(file_hashes)} files tracked)")

        except Exception as e:
            logger.warning(f"Failed to save cache for {tool_name}: {e}")

    def invalidate_tool(self, tool_name: str):
        """Invalidate specific tool cache.

        Args:
            tool_name: Name of the tool to invalidate

        """
        cache_path = self._get_cache_path(tool_name)

        try:
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Invalidated cache for {tool_name}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {tool_name}: {e}")

    def clear_all(self):
        """Clear all cached results."""
        try:
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*_cache.json"):
                    cache_file.unlink()
                logger.info("Cleared all audit caches")
        except Exception as e:
            logger.warning(f"Failed to clear caches: {e}")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about cached tools.

        Returns:
            Dictionary with cache statistics

        """
        stats = {
            "cache_dir": str(self.cache_dir),
            "max_age_hours": self.max_age_seconds / 3600,
            "cached_tools": [],
        }

        try:
            for cache_file in self.cache_dir.glob("*_cache.json"):
                try:
                    with open(cache_file, encoding="utf-8") as f:
                        cache_data = json.load(f)

                    age_seconds = time.time() - cache_data["timestamp"]
                    stats["cached_tools"].append(
                        {
                            "tool": cache_data.get("tool_name", cache_file.stem.replace("_cache", "")),
                            "age_seconds": age_seconds,
                            "age_minutes": age_seconds / 60,
                            "files_tracked": len(cache_data.get("file_hashes", {})),
                            "created_at": cache_data.get("created_at", "unknown"),
                            "valid": age_seconds <= self.max_age_seconds,
                        }
                    )
                except Exception as e:
                    logger.debug(f"Error reading cache stats for {cache_file}: {e}")
        except Exception as e:
            logger.debug(f"Error getting cache stats: {e}")

        return stats
