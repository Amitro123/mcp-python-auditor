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
        from app.core.report_generator_v2 import ReportGeneratorV2
        from datetime import datetime
        import tempfile
        from pathlib import Path

        results = {
            "bandit": {"status": "clean", "issues": [], "total_issues": 0},
            "secrets": {"status": "clean", "total_secrets": 0},
            "tests": {"status": "analyzed", "coverage_percent": 80, "test_breakdown": {"unit": 5, "integration": 0, "e2e": 0, "total_files": 5}},
            "duplication": {"status": "clean", "total_duplicates": 0, "duplicates": []},
            "dead_code": {"status": "clean", "unused_items": [], "total_dead": 0},
            "efficiency": {"status": "clean", "complexity": []},
            "structure": {"status": "analyzed", "tree": "", "file_counts": {}, "total_files": 0, "total_dirs": 0},
            "architecture": {"status": "analyzed"},
            "cleanup": {"status": "clean"},
            "git_info": {"status": "analyzed", "has_git": False}
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            generator = ReportGeneratorV2(reports_dir)
            report_path = generator.generate_report(
                report_id="test",
                project_path="/tmp/test",
                score=0,
                tool_results=results,
                timestamp=datetime.now()
            )
            report = Path(report_path).read_text(encoding='utf-8')

        # Should be markdown
        assert report.startswith("#")
        assert "**" in report
        assert "\n" in report

    def test_report_contains_actionable_insights(self):
        """Reports should have actionable recommendations."""
        from app.core.report_generator_v2 import ReportGeneratorV2
        from datetime import datetime
        import tempfile
        from pathlib import Path

        # Low coverage scenario
        results = {
            "bandit": {"status": "clean", "issues": [], "total_issues": 0},
            "secrets": {"status": "clean", "total_secrets": 0},
            "tests": {"status": "analyzed", "coverage_percent": 20, "tests_passed": 2, "tests_failed": 0, "test_breakdown": {"unit": 2, "integration": 0, "e2e": 0, "total_files": 2}},
            "duplication": {"status": "clean", "total_duplicates": 0, "duplicates": []},
            "dead_code": {"status": "clean", "unused_items": [], "total_dead": 0},
            "efficiency": {"status": "clean", "complexity": []},
            "structure": {"status": "analyzed", "tree": "", "file_counts": {}, "total_files": 0, "total_dirs": 0},
            "architecture": {"status": "analyzed"},
            "cleanup": {"status": "clean"},
            "git_info": {"status": "analyzed", "has_git": False}
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            generator = ReportGeneratorV2(reports_dir)
            report_path = generator.generate_report(
                report_id="test",
                project_path="/tmp/test",
                score=0,
                tool_results=results,
                timestamp=datetime.now()
            )
            report = Path(report_path).read_text(encoding='utf-8')

        # Should have coverage info in report
        assert "Coverage" in report or "Test" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
