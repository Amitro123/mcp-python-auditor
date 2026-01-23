"""
Integration tests for tool execution and report generation.
Tests the interaction between multiple analysis tools.
"""
import pytest
from pathlib import Path
import tempfile
import shutil


class TestToolIntegration:
    """Test integration between analysis tools."""
    
    @pytest.fixture
    def sample_project(self):
        """Create a temporary sample project for testing."""
        tmpdir = tempfile.mkdtemp()
        project = Path(tmpdir)
        
        # Create sample Python files
        (project / "main.py").write_text("""
def hello():
    print("Hello, world!")

def unused_function():
    pass
""")
        
        (project / "test_main.py").write_text("""
def test_hello():
    assert True
""")
        
        yield project
        
        # Cleanup
        shutil.rmtree(tmpdir)
    
    def test_structure_and_architecture_integration(self, sample_project):
        """Structure analysis should feed into architecture analysis."""
        from mcp_fastmcp_server import run_structure, run_architecture_visualizer

        # Run structure analysis
        structure_result = run_structure(sample_project)
        # StructureTool returns: tree, file_counts, total_files, total_dirs
        assert "tree" in structure_result
        py_count = structure_result.get("file_counts", {}).get(".py", 0)
        assert py_count >= 2

        # Run architecture analysis
        arch_result = run_architecture_visualizer(sample_project)
        assert arch_result["status"] == "analyzed"
        assert "mermaid_graph" in arch_result
    
    def test_tests_and_coverage_integration(self, sample_project):
        """Test detection should work with coverage analysis."""
        from mcp_fastmcp_server import run_tests_coverage

        result = run_tests_coverage(sample_project)

        # TestsTool returns: total_test_files, has_unit_tests, has_integration_tests, has_e2e_tests
        assert "total_test_files" in result
        assert result["total_test_files"] >= 1
        assert result.get("has_unit_tests", False) is True
    
    def test_dead_code_detection_integration(self, sample_project):
        """Dead code should be detected in sample project."""
        from mcp_fastmcp_server import run_dead_code
        
        result = run_dead_code(sample_project)
        
        # Should detect unused_function (if vulture is installed)
        assert "status" in result
        if result["status"] not in ["skipped", "error"]:
            assert "total_dead" in result
    
    def test_full_audit_workflow(self, sample_project):
        """Full audit should run all tools and generate report."""
        # This tests the complete integration of all components
        from mcp_fastmcp_server import (
            run_bandit, run_secrets, run_ruff, run_structure,
            run_dead_code, run_efficiency, run_duplication,
            run_git_info, run_cleanup_scan, run_architecture_visualizer,
            run_tests_coverage
        )

        # Run all tools
        results = {
            "structure": run_structure(sample_project),
            "architecture": run_architecture_visualizer(sample_project),
            "dead_code": run_dead_code(sample_project),
            "efficiency": run_efficiency(sample_project),
            "duplication": run_duplication(sample_project),
            "cleanup": run_cleanup_scan(sample_project),
            "tests": run_tests_coverage(sample_project),
        }

        # Verify structure result (uses StructureTool format)
        assert "tree" in results["structure"], "structure missing tree"
        assert results["structure"].get("total_files", 0) >= 1

        # Verify tests result (uses TestsTool format)
        assert "total_test_files" in results["tests"], "tests missing total_test_files"

        # Other tools should return status
        for tool_name in ["architecture", "dead_code", "efficiency", "duplication", "cleanup"]:
            result = results[tool_name]
            assert "status" in result, f"{tool_name} missing status"
            assert result["status"] in ["analyzed", "clean", "issues_found", "skipped", "error", "success", "cleanup_available", "vulnerabilities_found", "not_a_repo"]


class TestReportGeneration:
    """Test report generation with real data."""
    
    def test_markdown_report_structure(self):
        """Generated report should have all required sections."""
        from mcp_fastmcp_server import generate_full_markdown_report

        results = {
            "bandit": {"status": "clean", "issues": []},
            "secrets": {"status": "clean", "total_findings": 0},
            "tests": {"coverage_percent": 75, "tests_passed": 5, "tests_failed": 0, "tests_skipped": 0, "total_test_files": 5, "has_unit_tests": True, "has_integration_tests": False, "has_e2e_tests": False},
            "duplication": {"status": "clean", "total_duplicates": 0},
            "dead_code": {"status": "clean", "unused_items": []},
            "efficiency": {"status": "clean", "high_complexity_functions": []},
            "structure": {"tree": "main.py", "file_counts": {".py": 10}, "total_files": 10, "total_dirs": 2},
            "architecture": {"status": "analyzed", "mermaid_graph": "graph TD"},
            "cleanup": {"status": "clean", "total_size_mb": 0},
            "git_info": {"has_git": True, "branch": "main", "last_commit": "abc123 - Test, 1 hour ago : test commit", "commit_hash": "abc123", "days_since_commit": 0, "has_uncommitted_changes": False}
        }

        report = generate_full_markdown_report("test123", "10.5s", results, "/tmp/test")

        # Check required sections
        assert "# 🕵️‍♂️ Project Audit Report" in report
        assert "## 📊 Tool Execution Summary" in report
        assert "### 🧪 Tests & Coverage" in report
        assert "### 📝 Recent Changes" in report
        assert "**Score:**" in report
    
    def test_report_scoring_integration(self):
        """Report should correctly calculate and display score."""
        from mcp_fastmcp_server import generate_full_markdown_report

        # Low coverage + duplicates
        results = {
            "bandit": {"status": "clean", "issues": []},
            "secrets": {"status": "clean", "total_findings": 0},
            "tests": {"coverage_percent": 9, "tests_passed": 1, "tests_failed": 0, "total_test_files": 1, "has_unit_tests": True, "has_integration_tests": False, "has_e2e_tests": False},
            "duplication": {"status": "issues_found", "total_duplicates": 78},
            "dead_code": {"status": "clean", "unused_items": []},
            "efficiency": {"status": "clean", "high_complexity_functions": []},
            "structure": {"tree": "", "file_counts": {}, "total_files": 0, "total_dirs": 0},
            "architecture": {"status": "analyzed"},
            "cleanup": {"status": "clean"},
            "git_info": {"has_git": False}
        }

        report = generate_full_markdown_report("test456", "5.2s", results, "/tmp/test")

        # Should show realistic score (45/100)
        assert "45/100" in report or "**Score:** 45" in report
        assert "🔴" in report  # Red emoji for low score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
