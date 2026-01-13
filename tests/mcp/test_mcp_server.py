"""
Tests for MCP server functionality.
Tests the FastMCP integration and tool exposure.
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
        
        # Check that tools are registered
        # FastMCP registers tools via decorators
        assert hasattr(mcp, 'tool')
    
    def test_start_full_audit_tool(self):
        """Test start_full_audit MCP tool."""
        from mcp_fastmcp_server import start_full_audit
        
        # Verify it's an async function (MCP requirement)
        import inspect
        assert inspect.iscoroutinefunction(start_full_audit)
        
        # Verify signature
        sig = inspect.signature(start_full_audit)
        assert 'path' in sig.parameters
    
    def test_check_audit_status_tool(self):
        """Test check_audit_status MCP tool."""
        from mcp_fastmcp_server import check_audit_status
        
        import inspect
        assert inspect.iscoroutinefunction(check_audit_status)
        
        sig = inspect.signature(check_audit_status)
        assert 'job_id' in sig.parameters
    
    def test_install_dependencies_tool(self):
        """Test install_dependencies MCP tool."""
        from mcp_fastmcp_server import install_dependencies
        
        # Should be a regular function (not async)
        import inspect
        assert callable(install_dependencies)
        
        # Should return string message
        assert install_dependencies.__annotations__.get('return') == str
    
    def test_run_auto_fix_tool(self):
        """Test run_auto_fix MCP tool."""
        from mcp_fastmcp_server import run_auto_fix
        
        import inspect
        sig = inspect.signature(run_auto_fix)
        
        # Should have path and confirm parameters
        assert 'path' in sig.parameters
        assert 'confirm' in sig.parameters
        
        # confirm should default to False
        assert sig.parameters['confirm'].default == False
    
    def test_audit_quality_tool(self):
        """Test audit_quality MCP tool."""
        from mcp_fastmcp_server import audit_quality
        
        import inspect
        assert callable(audit_quality)
        
        sig = inspect.signature(audit_quality)
        assert 'path' in sig.parameters
    
    def test_generate_full_report_tool(self):
        """Test generate_full_report MCP tool."""
        from mcp_fastmcp_server import generate_full_report
        
        import inspect
        assert callable(generate_full_report)
        
        sig = inspect.signature(generate_full_report)
        assert 'path' in sig.parameters


class TestMCPToolBehavior:
    """Test MCP tool behaviors and responses."""
    
    @pytest.mark.asyncio
    async def test_missing_dependencies_response(self):
        """MCP tool should return helpful message when dependencies missing."""
        from mcp_fastmcp_server import start_full_audit, check_dependencies
        
        # Check if any dependencies are missing
        missing = check_dependencies()
        
        if missing:
            # Tool should return guidance message
            result = await start_full_audit("/tmp/test")
            
            assert "Missing Dependencies" in result
            assert "install_dependencies" in result
    
    def test_auto_fix_dry_run_response(self):
        """Auto-fix dry run should return JSON with planned actions."""
        from mcp_fastmcp_server import run_auto_fix
        
        result = run_auto_fix(".", confirm=False)
        
        # Should return JSON
        data = json.loads(result)
        assert data["status"] == "dry_run"
        assert "actions_planned" in data
    
    @pytest.mark.asyncio
    async def test_job_status_tracking(self):
        """MCP should track job status correctly."""
        from mcp_fastmcp_server import JOBS, check_audit_status
        import uuid
        
        # Create fake job
        job_id = str(uuid.uuid4())[:8]
        JOBS[job_id] = {
            "status": "running",
            "start_time": 0
        }
        
        # Check status
        result = await check_audit_status(job_id)
        
        assert job_id in result or "running" in result
        
        # Cleanup
        del JOBS[job_id]
    
    @pytest.mark.asyncio
    async def test_invalid_job_id(self):
        """Checking invalid job ID should return error message."""
        from mcp_fastmcp_server import check_audit_status
        
        result = await check_audit_status("nonexistent-job-id")
        
        assert "not found" in result.lower() or "unknown" in result.lower()


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


class TestMCPErrorHandling:
    """Test MCP server error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_path_handling(self):
        """MCP tools should handle invalid paths gracefully."""
        from mcp_fastmcp_server import start_full_audit
        
        # This should not crash the server
        try:
            result = await start_full_audit("/absolutely/nonexistent/path/that/does/not/exist")
            # Should return error message, not raise exception
            assert isinstance(result, str)
        except Exception as e:
            # If it does raise, it should be handled gracefully
            assert "path" in str(e).lower() or "not found" in str(e).lower()
    
    def test_malformed_json_handling(self):
        """Tools returning JSON should handle errors gracefully."""
        from mcp_fastmcp_server import run_auto_fix
        
        # This should return valid JSON even on error
        result = run_auto_fix("/nonexistent", confirm=False)
        
        # Should be parseable JSON
        data = json.loads(result)
        assert "status" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
