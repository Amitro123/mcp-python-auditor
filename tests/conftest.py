"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample Python project for testing."""
    # Create a simple Python file
    (tmp_path / "main.py").write_text("def hello(): return 'world'")
    (tmp_path / "test_main.py").write_text("def test_hello(): assert True")
    return tmp_path


@pytest.fixture
def project_path():
    """Return the actual project path for integration tests."""
    return Path(__file__).parent.parent
