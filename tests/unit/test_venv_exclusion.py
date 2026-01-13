"""
Regression test for virtual environment exclusion.
This test would have caught the case-sensitivity bug.
"""
import pytest
from pathlib import Path
import tempfile
import shutil


class TestVirtualEnvironmentExclusion:
    """Test that .venv and other ignored directories are properly excluded."""
    
    @pytest.fixture
    def project_with_venv(self):
        """Create a realistic project structure with a .venv directory."""
        tmpdir = tempfile.mkdtemp()
        project = Path(tmpdir)
        
        # Create main project code
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("def hello(): pass")
        (project / "src" / "utils.py").write_text("def util(): pass")
        
        # Create .venv with fake packages (simulating the bug scenario)
        venv_dir = project / ".venv"
        venv_dir.mkdir()
        (venv_dir / "Lib").mkdir(parents=True)
        site_packages = venv_dir / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)
        
        # Add fake package files (these should be EXCLUDED)
        fastapi_dir = site_packages / "fastapi"
        fastapi_dir.mkdir()
        (fastapi_dir / "applications.py").write_text("""
def duplicate_function():
    # This exact code appears 100 times in FastAPI
    pass
""" * 100)  # Create artificial duplicates
        
        # Add more venv noise
        (site_packages / "pydantic.py").write_text("# Large pydantic file" * 1000)
        (site_packages / "requests.py").write_text("# Large requests file" * 1000)
        
        yield project
        shutil.rmtree(tmpdir)
    
    def test_structure_excludes_venv(self, project_with_venv):
        """Structure tool should only count project files, not .venv files."""
        from mcp_fastmcp_server import run_structure
        
        result = run_structure(project_with_venv)
        
        # Should only count 2 Python files (main.py, utils.py)
        # NOT the 3+ files in .venv
        assert result["status"] == "analyzed"
        assert result["total_py_files"] <= 3, f"Found {result['total_py_files']} files, expected <=3 (excluding .venv)"
        
        # Verify .venv is not in the tree
        tree_str = result.get("directory_tree", "")
        assert ".venv" not in tree_str, ".venv should not appear in directory tree"
    
    def test_duplication_excludes_venv(self, project_with_venv):
        """Duplication tool should not scan .venv files."""
        from mcp_fastmcp_server import run_duplication
        
        result = run_duplication(project_with_venv)
        
        # Should find 0 duplicates (not the 100+ fake ones in .venv)
        assert result["status"] in ["clean", "issues_found"]
        assert result["total_duplicates"] < 10, \
            f"Found {result['total_duplicates']} duplicates, expected <10 (excluding .venv)"
    
    def test_base_tool_walk_excludes_venv(self, project_with_venv):
        """BaseTool.walk_project_files should skip .venv directories."""
        from app.core.base_tool import BaseTool
        
        # Create a mock tool
        class MockTool(BaseTool):
            @property
            def description(self):
                return "Test"
            
            def analyze(self, project_path):
                return {}
        
        tool = MockTool()
        
        # Walk project files
        files = list(tool.walk_project_files(project_with_venv))
        
        # Should only find 2 files
        assert len(files) <= 3, f"Found {len(files)} files, expected <=3"
        
        # Verify no .venv paths
        for file in files:
            assert ".venv" not in str(file).lower(), f"File in .venv found: {file}"
            assert "site-packages" not in str(file).lower(), f"site-packages file found: {file}"
    
    @pytest.mark.parametrize("venv_name", [".venv", "venv", ".Venv", "VENV", "env", ".env"])
    def test_case_insensitive_exclusion(self, venv_name):
        """Test that exclusion works regardless of case (Windows compatibility)."""
        tmpdir = tempfile.mkdtemp()
        project = Path(tmpdir)
        
        try:
            # Create project file
            (project / "main.py").write_text("def main(): pass")
            
            # Create venv with various casings
            venv_dir = project / venv_name
            venv_dir.mkdir()
            (venv_dir / "package.py").write_text("# Should be excluded")
            
            from mcp_fastmcp_server import run_structure
            result = run_structure(project)
            
            # Should only count main.py, not package.py in venv
            assert result["total_py_files"] == 1, \
                f"venv '{venv_name}' not excluded, found {result['total_py_files']} files"
        
        finally:
            shutil.rmtree(tmpdir)


class TestOtherIgnoredDirectories:
    """Test that all IGNORED_DIRECTORIES are properly excluded."""
    
    @pytest.mark.parametrize("ignored_dir", [
        "node_modules",
        "__pycache__",
        ".git",
        ".pytest_cache",
        "build",
        "dist",
        ".mypy_cache"
    ])
    def test_ignored_directories_excluded(self, ignored_dir):
        """Each ignored directory should be skipped during scanning."""
        tmpdir = tempfile.mkdtemp()
        project = Path(tmpdir)
        
        try:
            # Create project file
            (project / "main.py").write_text("def main(): pass")
            
            # Create ignored directory with file
            ignored_path = project / ignored_dir
            ignored_path.mkdir(parents=True)
            (ignored_path / "noise.py").write_text("# Should be excluded")
            
            from mcp_fastmcp_server import run_structure
            result = run_structure(project)
            
            # Should only count main.py
            assert result["total_py_files"] == 1, \
                f"Directory '{ignored_dir}' not excluded, found {result['total_py_files']} files"
        
        finally:
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
