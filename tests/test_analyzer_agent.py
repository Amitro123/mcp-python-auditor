"""Tests for the analyzer agent."""
import pytest
from pathlib import Path
from app.agents.analyzer_agent import AnalyzerAgent
from app.core.tool_registry import registry


@pytest.fixture
def analyzer(tmp_path):
    """Create analyzer instance with temp reports dir."""
    reports_dir = tmp_path / "reports"
    return AnalyzerAgent(reports_dir)


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project for testing."""
    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()
    
    # Create some Python files
    (project_dir / "main.py").write_text("""
def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
""")
    
    (project_dir / "utils.py").write_text("""
def add(a, b):
    return a + b

def unused_function():
    pass
""")
    
    # Create requirements.txt
    (project_dir / "requirements.txt").write_text("fastapi==0.100.0\n")
    
    return project_dir


@pytest.mark.asyncio
async def test_analyze_project(analyzer, sample_project):
    """Test basic project analysis."""
    # Only run fast tools to avoid hanging
    result = await analyzer.analyze_project(
        project_path=str(sample_project),
        dry_run=False,
        specific_tools=['structure', 'architecture']  # Skip slow tools like duplication, deadcode
    )
    
    assert result.report_id is not None
    assert result.score >= 0 and result.score <= 100
    assert result.project_path == str(sample_project)
    assert result.report_path is not None
    assert Path(result.report_path).exists()


@pytest.mark.asyncio
async def test_analyze_project_dry_run(analyzer, sample_project):
    """Test dry run analysis (no report generation)."""
    result = await analyzer.analyze_project(
        project_path=str(sample_project),
        dry_run=True,
        specific_tools=['structure']  # Fast tool only
    )
    
    assert result.report_id is not None
    assert result.report_path is None


@pytest.mark.asyncio
async def test_analyze_specific_tools(analyzer, sample_project):
    """Test running specific tools only."""
    result = await analyzer.analyze_project(
        project_path=str(sample_project),
        specific_tools=['structure', 'architecture']
    )
    
    assert 'structure' in result.tool_results
    assert 'architecture' in result.tool_results
    assert 'duplication' not in result.tool_results


@pytest.mark.asyncio
async def test_score_calculation(analyzer, sample_project):
    """Test that score is calculated correctly."""
    result = await analyzer.analyze_project(
        project_path=str(sample_project),
        dry_run=True,
        specific_tools=['structure', 'architecture']  # Fast tools only
    )
    
    # Score should be reduced due to no tests
    assert result.score < 100
    
    # Score should be between 0 and 100
    assert 0 <= result.score <= 100


@pytest.mark.asyncio
async def test_summary_generation(analyzer, sample_project):
    """Test summary generation."""
    result = await analyzer.analyze_project(
        project_path=str(sample_project),
        dry_run=True,
        specific_tools=['structure']  # Fast tool only
    )
    
    assert result.summary is not None
    assert len(result.summary) > 0
    assert "score" in result.summary.lower()
