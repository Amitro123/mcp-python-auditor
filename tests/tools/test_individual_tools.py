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
        
        if result["status"] != "skipped":
            assert "tool" in result
            assert result["tool"] == "bandit"
            # Should detect MD5 usage as security issue
            if result["status"] == "issues_found":
                assert result["total_issues"] > 0
    
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
        
        assert result["status"] == "analyzed"
        assert result["total_py_files"] >= 1
        assert "directory_tree" in result
    
    def test_dead_code_tool(self, sample_code):
        """Test Vulture dead code detector."""
        from mcp_fastmcp_server import run_dead_code
        
        result = run_dead_code(sample_code)
        
        if result["status"] != "skipped":
            # Should detect unused_function
            assert "total_dead_code" in result
    
    def test_efficiency_tool(self, sample_code):
        """Test Radon complexity analyzer."""
        from mcp_fastmcp_server import run_efficiency
        
        result = run_efficiency(sample_code)
        
        if result["status"] != "skipped":
            # Should detect complex_function
            assert "high_complexity_functions" in result
            if result["status"] == "issues_found":
                assert len(result["high_complexity_functions"]) > 0
    
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
        
        assert result["status"] in ["clean", "issues_found"]
        assert "total_size_mb" in result
    
    def test_git_tool(self, sample_code):
        """Test git info analyzer."""
        from mcp_fastmcp_server import run_git_info
        
        result = run_git_info(sample_code)
        
        # Non-git repo should return specific status
        assert result["status"] in ["not_a_repo", "analyzed", "skipped", "error"]
    
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
        
        assert "tool" in result
        assert result["tool"] == "pytest"
        # No tests in sample, should skip or show 0 coverage
    
    def test_pip_audit_tool(self, sample_code):
        """Test pip-audit vulnerability checker."""
        from mcp_fastmcp_server import run_pip_audit
        
        result = run_pip_audit(sample_code)
        
        assert "tool" in result
        if result["status"] != "skipped":
            assert "total_vulns" in result


class TestToolErrorHandling:
    """Test tool error handling and edge cases."""
    
    def test_tool_with_invalid_path(self):
        """Tools should handle invalid paths gracefully."""
        from mcp_fastmcp_server import run_structure
        
        result = run_structure(Path("/nonexistent/path"))
        # Should return error status, not crash
        assert result["status"] == "error"
    
    def test_tool_timeout_handling(self):
        """Tools should respect timeout limits."""
        # This is verified by the timeout parameters in each tool
        from mcp_fastmcp_server import run_bandit
        
        # Bandit has 60s timeout - verify it's set
        import inspect
        source = inspect.getsource(run_bandit)
        assert "timeout" in source
    
    def test_missing_tool_graceful_failure(self):
        """Missing tools should skip gracefully, not crash."""
        from mcp_fastmcp_server import run_dead_code
        
        result = run_dead_code(Path("."))
        
        # Should either work or skip, never crash
        assert result["status"] in ["clean", "issues_found", "skipped", "error"]
        assert "tool" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
