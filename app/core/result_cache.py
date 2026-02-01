"""Result Cache - Per-tool result caching for incremental audits.

Stores and merges tool results to enable incremental analysis.
Each tool has its own cache file in .audit_index/ directory.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CachedResult:
    """Represents a cached tool result."""

    tool_name: str
    timestamp: str
    file_results: dict[str, Any]  # file_path -> result for that file
    aggregated: dict[str, Any]  # Aggregated metrics (totals, etc.)

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "file_results": self.file_results,
            "aggregated": self.aggregated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CachedResult":
        return cls(
            tool_name=data.get("tool_name", ""),
            timestamp=data.get("timestamp", ""),
            file_results=data.get("file_results", {}),
            aggregated=data.get("aggregated", {}),
        )


class ResultCache:
    """Manages per-tool result caching for incremental audits.

    Cache structure:
    .audit_index/
    ├── file_index.json      # File hashes (managed by FileTracker)
    ├── bandit_results.json  # Bandit findings per file
    ├── ruff_results.json    # Ruff findings per file
    ├── deadcode_results.json
    ├── duplication_results.json
    └── efficiency_results.json
    """

    INDEX_DIR = ".audit_index"

    # Tools that support incremental analysis (results per file)
    INCREMENTAL_TOOLS = {"bandit", "ruff", "secrets", "deadcode", "efficiency", "typing"}

    # Tools that always need full re-run
    FULL_RUN_TOOLS = {"structure", "architecture", "git", "tests", "duplication", "cleanup"}

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.cache_dir = self.project_path / self.INDEX_DIR
        self._caches: dict[str, CachedResult] = {}

    def _cache_file(self, tool_name: str) -> Path:
        """Get cache file path for a tool."""
        return self.cache_dir / f"{tool_name}_results.json"

    def load_cache(self, tool_name: str) -> CachedResult | None:
        """Load cached results for a tool."""
        if tool_name in self._caches:
            return self._caches[tool_name]

        cache_file = self._cache_file(tool_name)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)
                result = CachedResult.from_dict(data)
                self._caches[tool_name] = result
                logger.info(f"Loaded {tool_name} cache ({len(result.file_results)} files)")
                return result
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load {tool_name} cache: {e}")
            return None

    def save_cache(self, tool_name: str, result: CachedResult) -> None:
        """Save tool results to cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_file(tool_name)

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
            self._caches[tool_name] = result
            logger.info(f"Saved {tool_name} cache ({len(result.file_results)} files)")
        except OSError as e:
            logger.error(f"Failed to save {tool_name} cache: {e}")

    def merge_results(
        self,
        tool_name: str,
        new_results: dict[str, Any],
        changed_files: list[str],
        deleted_files: list[str],
    ) -> dict[str, Any]:
        """Merge new results with cached results.

        Args:
            tool_name: Name of the tool
            new_results: Results from analyzing changed files
            changed_files: Files that were re-analyzed
            deleted_files: Files that were deleted

        Returns:
            Merged results combining cached + new

        """
        cached = self.load_cache(tool_name)

        if cached is None:
            # No cache, return new results as-is
            return new_results

        # Start with cached file results
        merged_file_results = dict(cached.file_results)

        # Remove deleted files
        for file_path in deleted_files:
            merged_file_results.pop(file_path, None)

        # Update with new results for changed files
        new_file_results = self._extract_file_results(tool_name, new_results)
        for file_path in changed_files:
            if file_path in new_file_results:
                merged_file_results[file_path] = new_file_results[file_path]

        # Re-aggregate metrics
        merged = self._aggregate_results(tool_name, merged_file_results)

        # Save updated cache
        self.save_cache(
            tool_name,
            CachedResult(
                tool_name=tool_name,
                timestamp=datetime.now().isoformat(),
                file_results=merged_file_results,
                aggregated=merged,
            ),
        )

        return merged

    def _normalize_path(self, file_path: str) -> str:
        """Normalize file path to relative path from project root."""
        if not file_path:
            return ""
        try:
            return str(Path(file_path).relative_to(self.project_path))
        except ValueError:
            return file_path

    def _group_items_by_file(self, items: list, file_keys: tuple[str, ...] = ("file",)) -> dict[str, list]:
        """Group items by their file path.

        Args:
            items: List of items with file path info
            file_keys: Keys to try for extracting file path (in order)

        Returns:
            Dict mapping relative file paths to lists of items

        """
        file_results: dict[str, list] = {}

        for item in items:
            # Try each key to find file path
            file_path = ""
            for key in file_keys:
                if file_path := item.get(key, ""):
                    break

            if rel_path := self._normalize_path(file_path):
                if rel_path not in file_results:
                    file_results[rel_path] = []
                file_results[rel_path].append(item)

        return file_results

    def _extract_file_results(self, tool_name: str, results: dict[str, Any]) -> dict[str, Any]:
        """Extract per-file results from tool output."""
        # Configuration: tool_name -> (result_keys, file_keys)
        tool_config = {
            "bandit": (["issues"], ("filename", "file")),
            "deadcode": (["dead_code"], ("file",)),
            "efficiency": (["high_complexity_functions"], ("file",)),
            "secrets": (["findings"], ("filename", "file")),
            "ruff": (
                ["quality", "style", "imports", "performance", "security", "complexity"],
                ("file",),
            ),
        }

        if tool_name not in tool_config:
            return {}

        result_keys, file_keys = tool_config[tool_name]
        file_results: dict[str, list] = {}

        # Collect all items from configured result keys
        for key in result_keys:
            items = results.get(key, [])
            grouped = self._group_items_by_file(items, file_keys)

            # Merge into file_results
            for path, path_items in grouped.items():
                if path not in file_results:
                    file_results[path] = []
                file_results[path].extend(path_items)

        return file_results

    def _flatten_items(self, file_results: dict[str, Any]) -> list[Any]:
        """Flatten file_results dict values into a single list."""
        all_items = []
        for items in file_results.values():
            all_items.extend(items)
        return all_items

    def _aggregate_simple(
        self,
        file_results: dict[str, Any],
        tool: str,
        count_key: str,
        items_key: str,
        status_found: str = "issues_found",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Aggregate results for simple tools (bandit, deadcode, secrets)."""
        all_items = self._flatten_items(file_results)
        result = {
            "tool": tool,
            "status": status_found if all_items else "clean",
            count_key: len(all_items),
            items_key: all_items[:limit] if limit else all_items,
        }
        return result

    def _aggregate_ruff(self, file_results: dict[str, Any]) -> dict[str, Any]:
        """Aggregate ruff results by category."""
        categories = ["quality", "style", "imports", "performance", "security", "complexity"]
        all_issues: dict[str, list] = {cat: [] for cat in categories}

        for issues in file_results.values():
            for issue in issues:
                category = issue.get("category", "quality")
                if category in all_issues:
                    all_issues[category].append(issue)

        total = sum(len(v) for v in all_issues.values())
        return {
            "tool": "ruff",
            "status": "issues_found" if total > 0 else "clean",
            "total_issues": total,
            **all_issues,
        }

    def _aggregate_efficiency(self, file_results: dict[str, Any]) -> dict[str, Any]:
        """Aggregate efficiency results."""
        all_funcs = self._flatten_items(file_results)
        return {
            "status": "analyzed",
            "total_high_complexity": len(all_funcs),
            "high_complexity_functions": all_funcs,
        }

    def _aggregate_results(self, tool_name: str, file_results: dict[str, Any]) -> dict[str, Any]:
        """Re-aggregate results from per-file data."""
        # Dispatch to tool-specific aggregators
        aggregators = {
            "bandit": lambda: self._aggregate_simple(file_results, "bandit", "total_issues", "issues", limit=50),
            "ruff": lambda: self._aggregate_ruff(file_results),
            "deadcode": lambda: self._aggregate_simple(file_results, "vulture", "total_dead", "dead_code", limit=30),
            "efficiency": lambda: self._aggregate_efficiency(file_results),
            "secrets": lambda: self._aggregate_simple(
                file_results,
                "detect-secrets",
                "total_secrets",
                "findings",
                status_found="secrets_found",
            ),
        }

        if tool_name in aggregators:
            return aggregators[tool_name]()

        # Default: return file results as-is
        return {"file_results": file_results}

    def invalidate_files(self, tool_name: str, file_paths: list[str]) -> None:
        """Remove specific files from a tool's cache."""
        cached = self.load_cache(tool_name)
        if cached is None:
            return

        for file_path in file_paths:
            cached.file_results.pop(file_path, None)

        self.save_cache(tool_name, cached)

    def clear_tool_cache(self, tool_name: str) -> bool:
        """Clear cache for a specific tool."""
        cache_file = self._cache_file(tool_name)
        if cache_file.exists():
            cache_file.unlink()
            self._caches.pop(tool_name, None)
            logger.info(f"Cleared {tool_name} cache")
            return True
        return False

    def clear_all_caches(self) -> int:
        """Clear all tool caches. Returns count of cleared files."""
        cleared = 0
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*_results.json"):
                cache_file.unlink()
                cleared += 1
            self._caches.clear()
        logger.info(f"Cleared {cleared} cache files")
        return cleared

    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about all caches."""
        stats = {
            "cache_dir": str(self.cache_dir),
            "cache_exists": self.cache_dir.exists(),
            "tools": {},
        }

        for tool in self.INCREMENTAL_TOOLS:
            cache_file = self._cache_file(tool)
            if cache_file.exists():
                cached = self.load_cache(tool)
                if cached:
                    stats["tools"][tool] = {
                        "files_cached": len(cached.file_results),
                        "timestamp": cached.timestamp,
                        "size_kb": round(cache_file.stat().st_size / 1024, 1),
                    }
            else:
                stats["tools"][tool] = {"cached": False}

        return stats

    def is_tool_incremental(self, tool_name: str) -> bool:
        """Check if a tool supports incremental analysis."""
        return tool_name in self.INCREMENTAL_TOOLS
