"""
Result Cache - Per-tool result caching for incremental audits.

Stores and merges tool results to enable incremental analysis.
Each tool has its own cache file in .audit_index/ directory.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class CachedResult:
    """Represents a cached tool result."""
    tool_name: str
    timestamp: str
    file_results: Dict[str, Any]  # file_path -> result for that file
    aggregated: Dict[str, Any]  # Aggregated metrics (totals, etc.)

    def to_dict(self) -> dict:
        return {
            'tool_name': self.tool_name,
            'timestamp': self.timestamp,
            'file_results': self.file_results,
            'aggregated': self.aggregated
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CachedResult':
        return cls(
            tool_name=data.get('tool_name', ''),
            timestamp=data.get('timestamp', ''),
            file_results=data.get('file_results', {}),
            aggregated=data.get('aggregated', {})
        )


class ResultCache:
    """
    Manages per-tool result caching for incremental audits.

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
    INCREMENTAL_TOOLS = {
        'bandit', 'ruff', 'secrets', 'deadcode', 'efficiency', 'typing'
    }

    # Tools that always need full re-run
    FULL_RUN_TOOLS = {
        'structure', 'architecture', 'git', 'tests', 'duplication', 'cleanup'
    }

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.cache_dir = self.project_path / self.INDEX_DIR
        self._caches: Dict[str, CachedResult] = {}

    def _cache_file(self, tool_name: str) -> Path:
        """Get cache file path for a tool."""
        return self.cache_dir / f"{tool_name}_results.json"

    def load_cache(self, tool_name: str) -> Optional[CachedResult]:
        """Load cached results for a tool."""
        if tool_name in self._caches:
            return self._caches[tool_name]

        cache_file = self._cache_file(tool_name)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                result = CachedResult.from_dict(data)
                self._caches[tool_name] = result
                logger.info(f"Loaded {tool_name} cache ({len(result.file_results)} files)")
                return result
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load {tool_name} cache: {e}")
            return None

    def save_cache(self, tool_name: str, result: CachedResult) -> None:
        """Save tool results to cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_file(tool_name)

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2)
            self._caches[tool_name] = result
            logger.info(f"Saved {tool_name} cache ({len(result.file_results)} files)")
        except IOError as e:
            logger.error(f"Failed to save {tool_name} cache: {e}")

    def merge_results(
        self,
        tool_name: str,
        new_results: Dict[str, Any],
        changed_files: List[str],
        deleted_files: List[str]
    ) -> Dict[str, Any]:
        """
        Merge new results with cached results.

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
        self.save_cache(tool_name, CachedResult(
            tool_name=tool_name,
            timestamp=datetime.now().isoformat(),
            file_results=merged_file_results,
            aggregated=merged
        ))

        return merged

    def _extract_file_results(self, tool_name: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract per-file results from tool output."""
        file_results = {}

        if tool_name == 'bandit':
            # Bandit returns issues list with file paths
            for issue in results.get('issues', []):
                file_path = issue.get('filename', issue.get('file', ''))
                if file_path:
                    # Normalize to relative path
                    try:
                        rel_path = str(Path(file_path).relative_to(self.project_path))
                    except ValueError:
                        rel_path = file_path
                    if rel_path not in file_results:
                        file_results[rel_path] = []
                    file_results[rel_path].append(issue)

        elif tool_name == 'ruff':
            # Ruff returns issues with filename
            for category in ['quality', 'style', 'imports', 'performance', 'security', 'complexity']:
                for issue in results.get(category, []):
                    file_path = issue.get('file', '')
                    if file_path:
                        try:
                            rel_path = str(Path(file_path).relative_to(self.project_path))
                        except ValueError:
                            rel_path = file_path
                        if rel_path not in file_results:
                            file_results[rel_path] = []
                        file_results[rel_path].append(issue)

        elif tool_name == 'deadcode':
            # Dead code has items with file paths
            for item in results.get('dead_code', []):
                file_path = item.get('file', '')
                if file_path:
                    try:
                        rel_path = str(Path(file_path).relative_to(self.project_path))
                    except ValueError:
                        rel_path = file_path
                    if rel_path not in file_results:
                        file_results[rel_path] = []
                    file_results[rel_path].append(item)

        elif tool_name == 'efficiency':
            # Efficiency has high_complexity_functions
            for func in results.get('high_complexity_functions', []):
                file_path = func.get('file', '')
                if file_path:
                    try:
                        rel_path = str(Path(file_path).relative_to(self.project_path))
                    except ValueError:
                        rel_path = file_path
                    if rel_path not in file_results:
                        file_results[rel_path] = []
                    file_results[rel_path].append(func)

        elif tool_name == 'secrets':
            # Secrets has findings per file
            for finding in results.get('findings', []):
                file_path = finding.get('filename', finding.get('file', ''))
                if file_path:
                    try:
                        rel_path = str(Path(file_path).relative_to(self.project_path))
                    except ValueError:
                        rel_path = file_path
                    if rel_path not in file_results:
                        file_results[rel_path] = []
                    file_results[rel_path].append(finding)

        return file_results

    def _aggregate_results(self, tool_name: str, file_results: Dict[str, Any]) -> Dict[str, Any]:
        """Re-aggregate results from per-file data."""

        if tool_name == 'bandit':
            all_issues = []
            for issues in file_results.values():
                all_issues.extend(issues)
            return {
                'tool': 'bandit',
                'status': 'issues_found' if all_issues else 'clean',
                'total_issues': len(all_issues),
                'issues': all_issues[:50]  # Limit for report
            }

        elif tool_name == 'ruff':
            all_issues = {'quality': [], 'style': [], 'imports': [], 'performance': [], 'security': [], 'complexity': []}
            for issues in file_results.values():
                for issue in issues:
                    category = issue.get('category', 'quality')
                    if category in all_issues:
                        all_issues[category].append(issue)
            total = sum(len(v) for v in all_issues.values())
            return {
                'tool': 'ruff',
                'status': 'issues_found' if total > 0 else 'clean',
                'total_issues': total,
                **all_issues
            }

        elif tool_name == 'deadcode':
            all_items = []
            for items in file_results.values():
                all_items.extend(items)
            return {
                'tool': 'vulture',
                'status': 'issues_found' if all_items else 'clean',
                'total_dead': len(all_items),
                'dead_code': all_items[:30]
            }

        elif tool_name == 'efficiency':
            all_funcs = []
            for funcs in file_results.values():
                all_funcs.extend(funcs)
            return {
                'status': 'analyzed',
                'total_high_complexity': len(all_funcs),
                'high_complexity_functions': all_funcs
            }

        elif tool_name == 'secrets':
            all_findings = []
            for findings in file_results.values():
                all_findings.extend(findings)
            return {
                'tool': 'detect-secrets',
                'status': 'secrets_found' if all_findings else 'clean',
                'total_secrets': len(all_findings),
                'findings': all_findings
            }

        # Default: return file results as-is
        return {'file_results': file_results}

    def invalidate_files(self, tool_name: str, file_paths: List[str]) -> None:
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
            for cache_file in self.cache_dir.glob('*_results.json'):
                cache_file.unlink()
                cleared += 1
            self._caches.clear()
        logger.info(f"Cleared {cleared} cache files")
        return cleared

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about all caches."""
        stats = {
            'cache_dir': str(self.cache_dir),
            'cache_exists': self.cache_dir.exists(),
            'tools': {}
        }

        for tool in self.INCREMENTAL_TOOLS:
            cache_file = self._cache_file(tool)
            if cache_file.exists():
                cached = self.load_cache(tool)
                if cached:
                    stats['tools'][tool] = {
                        'files_cached': len(cached.file_results),
                        'timestamp': cached.timestamp,
                        'size_kb': round(cache_file.stat().st_size / 1024, 1)
                    }
            else:
                stats['tools'][tool] = {'cached': False}

        return stats

    def is_tool_incremental(self, tool_name: str) -> bool:
        """Check if a tool supports incremental analysis."""
        return tool_name in self.INCREMENTAL_TOOLS
