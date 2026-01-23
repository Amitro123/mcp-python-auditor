"""
Tests for Incremental Audit Engine.

Tests cover:
- File change detection
- Result caching and merging
- Full vs incremental mode selection
- Performance tracking
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.incremental_engine import IncrementalEngine, IncrementalAuditResult
from app.core.file_tracker import FileTracker, ChangeSet
from app.core.result_cache import ResultCache


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with Python files."""
    project = tmp_path / "test_project"
    project.mkdir()
    
    # Create some Python files
    (project / "main.py").write_text("def main(): pass")
    (project / "utils.py").write_text("def helper(): pass")
    (project / "config.py").write_text("CONFIG = {}")
    
    return project


@pytest.fixture
def mock_tool():
    """Create a mock tool that returns predictable results."""
    def analyze(project_path, file_list=None):
        return {
            "tool": "mock_tool",
            "status": "clean",
            "total_issues": 0,
            "issues": []
        }
    
    tool = Mock()
    tool.analyze = Mock(side_effect=analyze)
    return tool


class TestIncrementalEngine:
    """Test suite for IncrementalEngine."""
    
    def test_initialization(self, temp_project):
        """Test engine initialization."""
        engine = IncrementalEngine(temp_project)
        
        assert engine.project_path == temp_project.resolve()
        assert isinstance(engine.file_tracker, FileTracker)
        assert isinstance(engine.result_cache, ResultCache)
    
    @pytest.mark.asyncio
    async def test_first_run_is_full_audit(self, temp_project, mock_tool):
        """First run should always be a full audit."""
        engine = IncrementalEngine(temp_project)
        
        tools = {"mock_tool": mock_tool}
        result = await engine.run_audit(tools)
        
        assert result.mode == "full"
        assert "mock_tool" in result.tool_results
        assert mock_tool.analyze.called
    
    @pytest.mark.asyncio
    async def test_force_full_bypasses_incremental(self, temp_project, mock_tool):
        """force_full=True should always run full audit."""
        engine = IncrementalEngine(temp_project)
        
        # First run to create cache
        tools = {"mock_tool": mock_tool}
        await engine.run_audit(tools)
        
        # Second run with force_full
        mock_tool.analyze.reset_mock()
        result = await engine.run_audit(tools, force_full=True)
        
        assert result.mode == "full"
        assert mock_tool.analyze.called
    
    @pytest.mark.asyncio
    async def test_incremental_mode_with_changes(self, temp_project, mock_tool):
        """Incremental mode should only analyze changed files."""
        engine = IncrementalEngine(temp_project)
        
        # First run (full)
        tools = {"mock_tool": mock_tool}
        await engine.run_audit(tools)
        
        # Modify a file
        (temp_project / "main.py").write_text("def main(): return 42")
        
        # Second run (incremental)
        mock_tool.analyze.reset_mock()
        result = await engine.run_audit(tools)
        
        assert result.mode == "incremental"
        assert result.changes.total_changed > 0
        assert result.time_saved_seconds is not None
    
    @pytest.mark.asyncio
    async def test_full_run_tools_always_execute(self, temp_project):
        """Full-run tools should always execute fully."""
        engine = IncrementalEngine(temp_project)
        
        structure_tool = Mock()
        structure_tool.analyze = Mock(return_value={
            "tool": "structure",
            "status": "analyzed",
            "total_py_files": 3
        })
        
        # First run
        tools = {"structure": structure_tool}
        await engine.run_audit(tools)
        
        # Modify a file
        (temp_project / "main.py").write_text("def main(): return 42")
        
        # Second run - structure should still run fully
        structure_tool.analyze.reset_mock()
        result = await engine.run_audit(tools)
        
        assert structure_tool.analyze.called
        # Should be called with full project path, not file list
        call_args = structure_tool.analyze.call_args
        assert call_args[0][0] == temp_project.resolve()
    
    @pytest.mark.asyncio
    async def test_result_duration_tracking(self, temp_project, mock_tool):
        """Test that duration is tracked correctly."""
        engine = IncrementalEngine(temp_project)
        
        tools = {"mock_tool": mock_tool}
        result = await engine.run_audit(tools)
        
        assert result.duration_seconds > 0
        assert "duration_s" in result.tool_results["mock_tool"]
    
    @pytest.mark.asyncio
    async def test_cache_stats_included(self, temp_project, mock_tool):
        """Test that cache stats are included in result."""
        engine = IncrementalEngine(temp_project)
        
        tools = {"mock_tool": mock_tool}
        result = await engine.run_audit(tools)
        
        assert result.cache_stats is not None
        assert "cache_dir" in result.cache_stats
    
    def test_clear_cache_all(self, temp_project, mock_tool):
        """Test clearing all caches."""
        engine = IncrementalEngine(temp_project)
        
        # Create some cache
        engine.file_tracker.update_index()
        
        # Clear all
        cleared = engine.clear_cache()
        
        assert cleared >= 0  # Should clear at least the file index
    
    def test_clear_cache_specific_tool(self, temp_project):
        """Test clearing specific tool cache."""
        engine = IncrementalEngine(temp_project)
        
        # Create a cache file
        from app.core.result_cache import CachedResult
        cached = CachedResult(
            tool_name="bandit",
            timestamp="2026-01-23T09:00:00",
            file_results={},
            aggregated={"status": "clean"}
        )
        engine.result_cache.save_cache("bandit", cached)
        
        # Clear specific tool
        cleared = engine.clear_cache(tool_name="bandit")
        
        assert cleared == 1
    
    def test_get_stats(self, temp_project):
        """Test getting engine statistics."""
        engine = IncrementalEngine(temp_project)
        
        stats = engine.get_stats()
        
        assert "file_tracker" in stats
        assert "result_cache" in stats
        assert "incremental_tools" in stats
        assert "full_run_tools" in stats
        
        # Check tool categorization
        assert "bandit" in stats["incremental_tools"]
        assert "structure" in stats["full_run_tools"]
    
    @pytest.mark.asyncio
    async def test_error_handling_in_tools(self, temp_project):
        """Test that tool errors are handled gracefully."""
        engine = IncrementalEngine(temp_project)
        
        # Create a tool that raises an error
        error_tool = Mock()
        error_tool.analyze = Mock(side_effect=Exception("Tool failed"))
        
        tools = {"error_tool": error_tool}
        result = await engine.run_audit(tools)
        
        assert "error_tool" in result.tool_results
        assert result.tool_results["error_tool"]["status"] == "error"
        assert "Tool failed" in result.tool_results["error_tool"]["error"]
    
    @pytest.mark.asyncio
    async def test_new_file_detection(self, temp_project, mock_tool):
        """Test that new files are detected and analyzed."""
        engine = IncrementalEngine(temp_project)
        
        # First run
        tools = {"mock_tool": mock_tool}
        await engine.run_audit(tools)
        
        # Add a new file
        (temp_project / "new_module.py").write_text("def new_func(): pass")
        
        # Second run
        result = await engine.run_audit(tools)
        
        assert result.changes.new_files
        assert "new_module.py" in result.changes.new_files[0]
    
    @pytest.mark.asyncio
    async def test_deleted_file_detection(self, temp_project, mock_tool):
        """Test that deleted files are detected."""
        engine = IncrementalEngine(temp_project)
        
        # First run
        tools = {"mock_tool": mock_tool}
        await engine.run_audit(tools)
        
        # Delete a file
        (temp_project / "config.py").unlink()
        
        # Second run
        result = await engine.run_audit(tools)
        
        assert result.changes.deleted_files
        assert "config.py" in result.changes.deleted_files[0]
    
    def test_incremental_audit_result_summary(self):
        """Test IncrementalAuditResult summary generation."""
        changes = ChangeSet(
            new_files=["a.py"],
            modified_files=["b.py", "c.py"],
            deleted_files=[],
            unchanged_files=["d.py"] * 97
        )
        
        # Full mode
        result = IncrementalAuditResult(
            mode="full",
            tool_results={},
            changes=changes,
            duration_seconds=60.0
        )
        assert "Full audit completed" in result.get_summary()
        
        # Incremental mode
        result = IncrementalAuditResult(
            mode="incremental",
            tool_results={},
            changes=changes,
            duration_seconds=5.0,
            time_saved_seconds=55.0
        )
        summary = result.get_summary()
        assert "Incremental audit" in summary
        assert "3 changed files" in summary
        assert "97 cached" in summary


class TestIncrementalEngineIntegration:
    """Integration tests with real file operations."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_project):
        """Test complete incremental audit workflow."""
        engine = IncrementalEngine(temp_project)
        
        # Create a simple tool
        def simple_tool(project_path, file_list=None):
            files = file_list if file_list else list(project_path.glob("*.py"))
            return {
                "tool": "simple",
                "status": "clean",
                "files_analyzed": len(files)
            }
        
        tool = Mock()
        tool.analyze = Mock(side_effect=simple_tool)
        
        # Run 1: Full audit
        result1 = await engine.run_audit({"simple": tool})
        assert result1.mode == "full"
        assert result1.tool_results["simple"]["files_analyzed"] == 3
        
        # Modify one file
        (temp_project / "main.py").write_text("def main(): return 'modified'")
        
        # Run 2: Incremental audit
        tool.analyze.reset_mock()
        result2 = await engine.run_audit({"simple": tool})
        assert result2.mode == "incremental"
        assert result2.changes.total_changed == 1
        assert result2.time_saved_seconds > 0
        
        # Run 3: No changes
        tool.analyze.reset_mock()
        result3 = await engine.run_audit({"simple": tool})
        # Should still be incremental but with 0 changes
        assert result3.mode == "full"  # No changes = full mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
