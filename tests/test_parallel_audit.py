"""Tests for parallel execution and smart skipping in analyzer agent."""
import pytest
import time
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.schemas import ToolResult

# Note: 'analyzer' fixture is defined in conftest.py


@pytest.fixture
def large_sample_project(tmp_path):
    """Create a project with more than 300 python files."""
    project_dir = tmp_path / "large_project"
    project_dir.mkdir()
    
    # Create 301 Python files
    for i in range(301):
        (project_dir / f"file_{i}.py").write_text(f"# File {i}\ndef function_{i}(): pass\n")
        
    return project_dir

@pytest.mark.asyncio
async def test_smart_skipping(analyzer, large_sample_project):
    """Test that heavy tools are skipped in large projects."""
    # Mock registry to return heavy tools
    with patch('app.agents.analyzer_agent.registry') as mock_registry:
        mock_tool = MagicMock()
        mock_tool.analyze.return_value = {'success': True}
        
        mock_registry.get_enabled_tools.return_value = {
            'structure': mock_tool,
            'complexity': mock_tool,
            'deadcode': mock_tool,
            'duplication': mock_tool
        }
        
        result = await analyzer.analyze_project(
            project_path=str(large_sample_project),
            dry_run=True
        )
        
        # Check that heavy tools were skipped
        assert 'structure' in result.tool_results
        assert 'complexity' not in result.tool_results
        assert 'deadcode' not in result.tool_results
        assert 'duplication' not in result.tool_results
        
        # Check summary warning
        assert "Heavy tools skipped" in result.summary
        assert "complexity, deadcode, duplication" in result.summary

@pytest.mark.asyncio
async def test_parallel_execution_timing(analyzer, tmp_path):
    """Test that tools run in parallel (approximately)."""
    project_dir = tmp_path / "parallel_project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')")
    
    class SlowTool:
        def analyze(self, path):
            time.sleep(1)  # Simulate blocking work
            return {'status': 'ok'}
            
    with patch('app.agents.analyzer_agent.registry') as mock_registry:
        tool1 = SlowTool()
        tool2 = SlowTool()
        
        mock_registry.get_enabled_tools.return_value = {
            'tool1': tool1,
            'tool2': tool2
        }
        
        start_time = time.time()
        result = await analyzer.analyze_project(
            project_path=str(project_dir),
            dry_run=True
        )
        end_time = time.time()
        
        total_duration = end_time - start_time
        
        # If sequential, it would take at least 2 seconds.
        # If parallel, it should take slightly more than 1 second.
        # We check if it's less than 1.8 seconds to be safe (CI might be slow).
        assert total_duration < 1.8
        assert 'tool1' in result.tool_results
        assert 'tool2' in result.tool_results

@pytest.mark.asyncio
async def test_tool_failure_safety(analyzer, tmp_path):
    """Test that one failing tool doesn't stop others."""
    project_dir = tmp_path / "failure_project"
    project_dir.mkdir()
    (project_dir / "main.py").write_text("print('hello')")
    
    class FailingTool:
        def analyze(self, path):
            raise ValueError("Something went wrong")
            
    class SuccessTool:
        def analyze(self, path):
            return {'status': 'ok'}
            
    with patch('app.agents.analyzer_agent.registry') as mock_registry:
        mock_registry.get_enabled_tools.return_value = {
            'fail': FailingTool(),
            'success': SuccessTool()
        }
        
        result = await analyzer.analyze_project(
            project_path=str(project_dir),
            dry_run=True
        )
        
        assert result.tool_results['fail'].success is False
        assert "Something went wrong" in result.tool_results['fail'].errors[0]
        assert result.tool_results['success'].success is True
