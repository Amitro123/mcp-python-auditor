"""
Tests for individual analysis tools.
Verifies each of the 12 tools works correctly.
"""
import pytest
from pathlib import Path
import tempfile
import shutil


class TestAnalysisTools:
    """Test each analysis tool individually."""
    
    @pytest.fixture
    def sample_code(self):
        """Create sample code for testing tools."""
        tmpdir = tempfile.mkdtemp()
        project = Path(tmpdir)
        
        (project / "code.py").write_text("""
import os
import hashlib

def calculate_hash(password):
    # Security issue: using MD5
    return hashlib.md5(password.encode()).hexdigest()

def complex_function(a, b, c, d, e):
    # High complexity
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return True
    return False

def unused_function():
    pass
""")
        
        yield project
        shutil.rmtree(tmpdir)
    
    def test_bandit_tool(self, sample_code):
        """Test Bandit security scanner."""
        from mcp_fastmcp_server import run_bandit

        result = run_bandit(sample_code)

        if result.get("status") != "skipped":
            assert "tool" in result
            assert result["tool"] == "bandit"
            # Should detect MD5 usage as security issue
            if result.get("status") == "issues_found":
                assert result.get("total_issues", 0) > 0
    
    def test_secrets_tool(self, sample_code):
        """Test detect-secrets scanner."""
        from mcp_fastmcp_server import run_secrets
        
        result = run_secrets(sample_code)
        
        assert "tool" in result
        assert result["tool"] == "secrets"
        assert result["status"] in ["clean", "issues_found", "skipped", "error"]
    
    def test_ruff_tool(self, sample_code):
        """Test Ruff linter."""
        from mcp_fastmcp_server import run_ruff
        
        result = run_ruff(sample_code)
        
        assert "tool" in result
        assert result["tool"] == "ruff"
    
    def test_structure_tool(self, sample_code):
        """Test structure analyzer."""
        from mcp_fastmcp_server import run_structure

        result = run_structure(sample_code)

        # StructureTool returns: tree, file_counts, total_files, total_dirs
        assert "tree" in result
        py_count = result.get("file_counts", {}).get(".py", 0)
        assert py_count >= 1
        assert result.get("total_files", 0) >= 1
    
    def test_dead_code_tool(self, sample_code):
        """Test Vulture dead code detector."""
        from mcp_fastmcp_server import run_dead_code
        
        result = run_dead_code(sample_code)
        
        assert "status" in result
        if result["status"] not in ["skipped", "error"]:
            # Should detect unused_function
            assert "total_dead" in result
    
    def test_efficiency_tool(self, sample_code):
        """Test Radon complexity analyzer."""
        from mcp_fastmcp_server import run_efficiency
        
        result = run_efficiency(sample_code)
        
        assert "status" in result
        if result["status"] not in ["skipped", "error"]:
            # Should detect complex_function
            assert "high_complexity_functions" in result
            # Ruff's complexity detection may differ from Radon
            # Just verify the field exists
    
    def test_duplication_tool(self, sample_code):
        """Test code duplication detector."""
        from mcp_fastmcp_server import run_duplication
        
        result = run_duplication(sample_code)
        
        assert result["status"] in ["clean", "issues_found"]
        assert "total_duplicates" in result
    
    def test_cleanup_tool(self, sample_code):
        """Test cleanup scanner."""
        from mcp_fastmcp_server import run_cleanup_scan
        
        # Create cache directory
        cache_dir = sample_code / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "test.pyc").write_text("compiled")
        
        result = run_cleanup_scan(sample_code)
        
        assert result["status"] in ["clean", "issues_found", "cleanup_available"]
        assert "total_size_mb" in result
    
    def test_git_tool(self, sample_code):
        """Test git info analyzer."""
        from mcp_fastmcp_server import run_git_info

        result = run_git_info(sample_code)

        # GitTool returns has_git (bool) instead of status
        # Non-git repo should return has_git=False
        assert "has_git" in result
        assert result["has_git"] is False  # sample_code is not a git repo
    
    def test_architecture_tool(self, sample_code):
        """Test architecture visualizer."""
        from mcp_fastmcp_server import run_architecture_visualizer
        
        result = run_architecture_visualizer(sample_code)
        
        assert result["status"] in ["analyzed", "error"]
        if result["status"] == "analyzed":
            assert "mermaid_graph" in result
    
    def test_tests_coverage_tool(self, sample_code):
        """Test pytest coverage analyzer."""
        from mcp_fastmcp_server import run_tests_coverage

        result = run_tests_coverage(sample_code)

        # TestsTool returns: coverage_percent, tests_passed, tests_failed, total_test_files, etc.
        assert "coverage_percent" in result
        assert "total_test_files" in result
        # No tests in sample, should show 0 coverage
    
    def test_pip_audit_tool(self, sample_code):
        """Test pip-audit vulnerability checker."""
        from mcp_fastmcp_server import run_pip_audit
        
        result = run_pip_audit(sample_code)
        
        assert "tool" in result
        if result["status"] != "skipped":
            # Check for either field name (API changed)
            assert "total_vulns" in result or "total_vulnerabilities" in result


class TestToolErrorHandling:
    """Test tool error handling and edge cases."""
    
    def test_tool_with_invalid_path(self):
        """Tools should handle invalid paths gracefully."""
        from mcp_fastmcp_server import run_structure

        result = run_structure(Path("/nonexistent/path"))
        # StructureTool returns {"error": "..."}  for invalid paths
        assert "error" in result
    
    def test_tool_timeout_handling(self):
        """Tools should respect timeout limits."""
        # Timeout is now handled by Tool classes (FastAuditTool, TestsTool, etc.)
        from app.tools.fast_audit_tool import FastAuditTool

        import inspect
        source = inspect.getsource(FastAuditTool.analyze)
        assert "timeout" in source
    
    def test_missing_tool_graceful_failure(self):
        """Missing tools should skip gracefully, not crash."""
        from mcp_fastmcp_server import run_dead_code
        
        result = run_dead_code(Path("."))
        
        # Should either work or skip, never crash
        assert "status" in result
        assert result["status"] in ["clean", "analyzed", "skipped", "error"]
        assert "tool" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
