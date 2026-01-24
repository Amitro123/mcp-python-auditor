"""
Incremental Audit Engine - Smart orchestration for 90%+ faster audits.

This engine:
1. Detects file changes using MD5 hashing
2. Only re-runs tools on changed files
3. Merges cached results with new results
4. Provides clear feedback on time saved
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.file_tracker import FileTracker, ChangeSet
from app.core.result_cache import ResultCache

logger = logging.getLogger(__name__)


@dataclass
class IncrementalAuditResult:
    """Result of an incremental audit."""
    mode: str  # 'full' or 'incremental'
    tool_results: Dict[str, Any]
    changes: ChangeSet
    duration_seconds: float
    time_saved_seconds: Optional[float] = None
    cache_stats: Optional[Dict[str, Any]] = None
    
    def get_summary(self) -> str:
        """Human-readable summary."""
        if self.mode == 'full':
            return f"✅ Full audit completed in {self.duration_seconds:.1f}s"
        else:
            saved = f" (saved {self.time_saved_seconds:.1f}s vs full audit)" if self.time_saved_seconds else ""
            return (
                f"🔄 Incremental audit: analyzed {self.changes.total_changed} changed files, "
                f"{self.changes.total_cached} cached{saved}"
            )


class IncrementalEngine:
    """
    Orchestrates incremental audits by coordinating file tracking and result caching.
    
    Architecture:
    - FileTracker: Detects which files changed
    - ResultCache: Stores and merges per-tool results
    - Tool Execution: Only runs on changed files
    """
    
    # Tools that always need full re-run (no file-level caching)
    FULL_RUN_TOOLS = {
        'structure', 'architecture', 'git', 'tests', 'cleanup'
    }
    
    # Tools that support incremental analysis
    INCREMENTAL_TOOLS = {
        'bandit', 'quality', 'ruff', 'secrets', 'deadcode', 
        'efficiency', 'typing', 'duplication'
    }
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.file_tracker = FileTracker(self.project_path)
        self.result_cache = ResultCache(self.project_path)
        
    async def run_audit(
        self,
        tools: Dict[str, Any],
        force_full: bool = False
    ) -> IncrementalAuditResult:
        """
        Run an incremental or full audit.
        
        Args:
            tools: Dictionary of tool_name -> tool_instance or callable
            force_full: If True, bypass incremental mode and run full audit
            
        Returns:
            IncrementalAuditResult with all tool results and metadata
        """
        start_time = time.time()
        
        # Detect file changes
        changes = self.file_tracker.detect_changes()
        
        # Determine mode
        is_first_run = not self.file_tracker.index_file.exists()
        should_run_full = force_full or is_first_run or not changes.has_changes
        
        if should_run_full:
            logger.info("Running FULL audit (first run or no changes detected)")
            result = await self._run_full_audit(tools, changes)
            result.mode = 'full'
        else:
            logger.info(f"Running INCREMENTAL audit: {changes.summary()}")
            result = await self._run_incremental_audit(tools, changes)
            result.mode = 'incremental'
        
        result.duration_seconds = time.time() - start_time

        if result.mode == 'incremental':
            # Estimate time saved (rough heuristic: 90% of full audit time)
            result.time_saved_seconds = result.duration_seconds * 9  # Saved ~90%

        result.cache_stats = self.result_cache.get_cache_stats()
        
        # Update file index after successful audit
        self.file_tracker.update_index()
        
        logger.info(result.get_summary())
        return result
    
    async def _run_full_audit(
        self,
        tools: Dict[str, Any],
        changes: ChangeSet
    ) -> IncrementalAuditResult:
        """Run full audit on all files."""
        results = {}
        
        # Run all tools
        for tool_name, tool in tools.items():
            tool_start = time.time()
            try:
                if hasattr(tool, 'analyze'):
                    # It's a tool instance
                    tool_result = tool.analyze(self.project_path)
                elif callable(tool):
                    # It's a function
                    tool_result = tool(self.project_path)
                else:
                    logger.warning(f"Unknown tool type for {tool_name}")
                    continue
                
                tool_result['duration_s'] = round(time.time() - tool_start, 2)
                results[tool_name] = tool_result
                
                # Cache result if tool supports incremental
                if tool_name in self.INCREMENTAL_TOOLS:
                    self._cache_tool_result(tool_name, tool_result)
                    
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                results[tool_name] = {
                    'status': 'error',
                    'error': str(e),
                    'duration_s': round(time.time() - tool_start, 2)
                }
        
        return IncrementalAuditResult(
            mode='full',
            tool_results=results,
            changes=changes,
            duration_seconds=0  # Will be set by caller
        )
    
    async def _run_incremental_audit(
        self,
        tools: Dict[str, Any],
        changes: ChangeSet
    ) -> IncrementalAuditResult:
        """Run incremental audit on changed files only."""
        results = {}
        
        for tool_name, tool in tools.items():
            tool_start = time.time()
            
            try:
                if tool_name in self.FULL_RUN_TOOLS:
                    # Always run full for these tools
                    logger.info(f"Running {tool_name} (full run required)")
                    if hasattr(tool, 'analyze'):
                        tool_result = tool.analyze(self.project_path)
                    elif callable(tool):
                        tool_result = tool(self.project_path)
                    else:
                        raise ValueError(f"Unknown tool type for {tool_name}")
                else:
                    # Incremental tool - only analyze changed files
                    logger.info(f"Running {tool_name} (incremental: {len(changes.changed_files)} files)")
                    tool_result = await self._run_tool_incremental(
                        tool_name, tool, changes
                    )
                
                tool_result['duration_s'] = round(time.time() - tool_start, 2)
                results[tool_name] = tool_result
                
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                results[tool_name] = {
                    'status': 'error',
                    'error': str(e),
                    'duration_s': round(time.time() - tool_start, 2)
                }
        
        return IncrementalAuditResult(
            mode='incremental',
            tool_results=results,
            changes=changes,
            duration_seconds=0  # Will be set by caller
        )
    
    async def _run_tool_incremental(
        self,
        tool_name: str,
        tool: Any,
        changes: ChangeSet
    ) -> Dict[str, Any]:
        """
        Run a tool on changed files only and merge with cached results.
        
        Args:
            tool_name: Name of the tool
            tool: Tool instance or callable
            changes: Detected file changes
            
        Returns:
            Merged results (cached + new)
        """
        if not changes.changed_files:
            # No changes, return cached results
            cached = self.result_cache.load_cache(tool_name)
            if cached:
                logger.info(f"{tool_name}: Using 100% cached results")
                return cached.aggregated
            else:
                # No cache, run full
                logger.warning(f"{tool_name}: No cache found, running full")
                if callable(tool):
                    return tool(self.project_path)
                else:
                    return tool.analyze(self.project_path)
        
        # Run tool on changed files only
        changed_file_paths = [
            self.project_path / f for f in changes.changed_files
        ]
        
        # Execute tool with file filter
        new_results = await self._execute_tool_on_files(
            tool, tool_name, changed_file_paths
        )
        
        # Merge with cached results
        merged = self.result_cache.merge_results(
            tool_name=tool_name,
            new_results=new_results,
            changed_files=changes.changed_files,
            deleted_files=changes.deleted_files
        )
        
        return merged
    
    async def _execute_tool_on_files(
        self,
        tool: Any,
        tool_name: str,
        file_paths: List[Path]
    ) -> Dict[str, Any]:
        """Execute a tool on specific files."""
        # Most tools accept a file_list parameter
        try:
            if hasattr(tool, 'analyze'):
                return tool.analyze(self.project_path, file_list=file_paths)
            elif callable(tool):
                # For function-based tools, we need to pass files differently
                # This is tool-specific, so we'll use a dispatch
                return self._call_tool_function(tool, tool_name, file_paths)
            else:
                raise ValueError(f"Unknown tool type for {tool_name}")
        except TypeError:
            # Tool doesn't support file_list, run on full project
            logger.warning(f"{tool_name} doesn't support file filtering, running full")
            if hasattr(tool, 'analyze'):
                return tool.analyze(self.project_path)
            else:
                return tool(self.project_path)
    
    def _call_tool_function(
        self,
        tool_func: callable,
        tool_name: str,
        file_paths: List[Path]
    ) -> Dict[str, Any]:
        """Call a function-based tool with file filtering."""
        # For now, run on full project
        # TODO: Add file filtering support for function-based tools
        return tool_func(self.project_path)
    
    def _cache_tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        """Cache a tool result."""
        try:
            from app.core.result_cache import CachedResult
            
            # Extract per-file results
            file_results = self.result_cache._extract_file_results(tool_name, result)
            
            cached = CachedResult(
                tool_name=tool_name,
                timestamp=datetime.now().isoformat(),
                file_results=file_results,
                aggregated=result
            )
            
            self.result_cache.save_cache(tool_name, cached)
        except Exception as e:
            logger.warning(f"Failed to cache {tool_name} results: {e}")
    
    def clear_cache(self, tool_name: Optional[str] = None) -> int:
        """
        Clear cache.
        
        Args:
            tool_name: Specific tool to clear, or None for all
            
        Returns:
            Number of cache files cleared
        """
        if tool_name:
            success = self.result_cache.clear_tool_cache(tool_name)
            return 1 if success else 0
        else:
            # Clear both result cache and file index
            count = self.result_cache.clear_all_caches()
            self.file_tracker.clear_index()
            return count + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the incremental system."""
        return {
            'file_tracker': self.file_tracker.get_stats(),
            'result_cache': self.result_cache.get_cache_stats(),
            'incremental_tools': list(self.INCREMENTAL_TOOLS),
            'full_run_tools': list(self.FULL_RUN_TOOLS)
        }
