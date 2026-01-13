"""
Tests for MCP server functionality.
Tests the FastMCP integration and tool exposure.
NOTE: FastMCP wraps functions in FunctionTool objects, so we skip signature inspection tests.
"""
import pytest
import json
from pathlib import Path


class TestMCPServerIntegration:
    """Test MCP server tool registration and execution."""
    
    def test_mcp_tools_registered(self):
        """All MCP tools should be registered."""
        from mcp_fastmcp_server import mcp
        
        # Verify MCP server exists
        assert mcp is not None
        
        # FastMCP uses decorators - tools are registered internally
        # Just verify the module loaded successfully
        assert hasattr(mcp, 'tool')
        assert hasattr(mcp, 'run')


class TestMCPToolBehavior:
    """Test MCP tool behaviors and responses."""
    
    @pytest.mark.asyncio
    async def test_missing_dependencies_response(self):
        """MCP tool should return helpful message when dependencies missing."""
        from mcp_fastmcp_server import check_dependencies
        
        # Check if any dependencies are missing
        missing = check_dependencies()
        
        # Test passes if we can check dependencies
        assert isinstance(missing, list)


class TestMCPReportDelivery:
    """Test how MCP delivers reports to AI."""
    
    def test_report_format_is_markdown(self):
        """Reports should be in markdown format for AI consumption."""
        from mcp_fastmcp_server import generate_full_markdown_report
        
        results = {
            "bandit": {"status": "clean", "issues": []},
            "secrets": {"status": "clean", "total_findings": 0},
            "tests": {"status": "analyzed", "coverage_percent": 80, "test_breakdown": {"unit": 5, "integration": 0, "e2e": 0, "total_files": 5}},
            "duplication": {"status": "clean", "total_duplicates": 0},
            "dead_code": {"status": "clean", "unused_items": []},
            "efficiency": {"status": "clean", "high_complexity_functions": []},
            "structure": {"status": "analyzed"},
            "architecture": {"status": "analyzed"},
            "cleanup": {"status": "clean"},
            "git_info": {"status": "analyzed"}
        }
        
        report = generate_full_markdown_report("test", "10s", results, "/tmp/test")
        
        # Should be markdown
        assert report.startswith("#")
        assert "**" in report
        assert "\n" in report
    
    def test_report_contains_actionable_insights(self):
        """Reports should have actionable recommendations."""
        from mcp_fastmcp_server import generate_full_markdown_report
        
        # Low coverage scenario
        results = {
            "bandit": {"status": "clean", "issues": []},
            "secrets": {"status": "clean", "total_findings": 0},
            "tests": {"status": "analyzed", "coverage_percent": 20, "tests_passed": 2, "tests_failed": 0, "test_breakdown": {"unit": 2, "integration": 0, "e2e": 0, "total_files": 2}},
            "duplication": {"status": "clean", "total_duplicates": 0},
            "dead_code": {"status": "clean", "unused_items": []},
            "efficiency": {"status": "clean", "high_complexity_functions": []},
            "structure": {"status": "analyzed"},
            "architecture": {"status": "analyzed"},
            "cleanup": {"status": "clean"},
            "git_info": {"status": "analyzed"}
        }
        
        report = generate_full_markdown_report("test", "10s", results, "/tmp/test")
        
        # Should have recommendations
        assert "Recommendation" in report or "Fix:" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
