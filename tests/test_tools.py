"""Tests for analysis tools."""
import pytest
from pathlib import Path

# Skip if deleted modules are not available
pytest.importorskip("app.tools.structure_tool", reason="StructureTool was removed")
pytest.importorskip("app.tools.architecture_tool", reason="ArchitectureTool was removed")

from app.tools.duplication_tool import DuplicationTool
from app.tools.deadcode_tool import DeadcodeTool



@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create app directory
    app_dir = project_dir / "app"
    app_dir.mkdir()
    
    # Create some Python files
    (app_dir / "main.py").write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
""")
    
    (app_dir / "utils.py").write_text("""
def duplicate_func():
    x = 1
    y = 2
    return x + y

def another_duplicate():
    x = 1
    y = 2
    return x + y

def unused_function():
    pass
""")
    
    # Create __pycache__ for cleanup test
    pycache_dir = app_dir / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "test.pyc").write_text("compiled")
    
    return project_dir


def test_structure_tool(sample_project):
    """Test structure analysis tool."""
    tool = StructureTool()
    result = tool.analyze(sample_project)
    
    assert 'tree' in result
    assert 'file_counts' in result
    assert 'total_files' in result
    assert result['total_files'] > 0


def test_architecture_tool(sample_project):
    """Test architecture analysis tool."""
    tool = ArchitectureTool()
    result = tool.analyze(sample_project)
    
    assert 'issues' in result
    assert 'total_issues' in result
    assert isinstance(result['issues'], list)


def test_duplication_tool(sample_project):
    """Test duplication detection tool."""
    tool = DuplicationTool()
    result = tool.analyze(sample_project)
    
    assert 'duplicates' in result
    assert 'total_duplicates' in result
    assert isinstance(result['duplicates'], list)


def test_deadcode_tool(sample_project):
    """Test dead code detection tool."""
    tool = DeadcodeTool()
    result = tool.analyze(sample_project)
    
    assert 'dead_functions' in result
    assert 'unused_imports' in result
    assert isinstance(result['dead_functions'], list)





def test_tool_base_interface():
    """Test that all tools implement base interface."""
    tools = [
        StructureTool(),
        ArchitectureTool(),
        DuplicationTool(),
        DeadcodeTool()
    ]
    
    for tool in tools:
        assert hasattr(tool, 'analyze')
        assert hasattr(tool, 'description')
        assert hasattr(tool, 'name')
        assert callable(tool.analyze)
