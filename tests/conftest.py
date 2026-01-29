"""Pytest configuration and fixtures."""
import pytest
from pathlib import Path
from app.core.tool_registry import registry
from app.agents.analyzer_agent import AnalyzerAgent


@pytest.fixture
def analyzer(tmp_path):
    """Create analyzer instance with temp reports dir. Shared across tests."""
    reports_dir = tmp_path / "reports"
    return AnalyzerAgent(reports_dir)


@pytest.fixture(scope="session", autouse=True)
def setup_tools():
    """Discover and load tools before running tests."""
    registry.discover_tools()
    yield
    # Cleanup if needed


@pytest.fixture(scope="module", autouse=True)
def setup_app_state():
    """Initialize app state for API tests."""
    from app.main import app, REPORTS_DIR
    
    # Initialize analyzer in app state (normally done by lifespan)
    app.state.analyzer = AnalyzerAgent(REPORTS_DIR)
    
    yield
    
    # Cleanup
    if hasattr(app.state, 'analyzer'):
        delattr(app.state, 'analyzer')

