"""Tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from app.main import app, TOOLS_DIR
from app.core.tool_registry import registry


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    # Discover tools before testing
    registry.discover_tools(TOOLS_DIR)
    return TestClient(app)


@pytest.fixture
def sample_project(tmp_path_factory):
    """Create a sample project for testing."""
    project_dir = tmp_path_factory.mktemp("test_project")
    
    (project_dir / "main.py").write_text("""
def hello():
    print("Hello")
""")
    
    (project_dir / "requirements.txt").write_text("fastapi==0.100.0\n")
    
    return project_dir


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "tools_loaded" in data


def test_list_tools(client):
    """Test listing available tools."""
    response = client.get("/tools")
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    assert len(tools) > 0
    
    # Check tool structure
    tool = tools[0]
    assert "name" in tool
    assert "description" in tool
    assert "enabled" in tool


def test_audit_endpoint(client, sample_project):
    """Test project audit endpoint."""
    response = client.post(
        "/audit",
        json={
            "path": str(sample_project),
            "dry_run": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "report_id" in data
    assert "score" in data
    assert "tool_results" in data
    assert 0 <= data["score"] <= 100


def test_audit_invalid_path(client):
    """Test audit with invalid path."""
    response = client.post(
        "/audit",
        json={
            "path": "/nonexistent/path",
            "dry_run": True
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_run_specific_tool(client, sample_project):
    """Test running a specific tool."""
    response = client.post(
        "/tools/structure/run",
        json={"path": str(sample_project)}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "tool_name" in data
    assert data["tool_name"] == "structure"
    assert "success" in data
    assert "data" in data


def test_run_nonexistent_tool(client, sample_project):
    """Test running a tool that doesn't exist."""
    response = client.post(
        "/tools/nonexistent/run",
        json={"path": str(sample_project)}
    )
    
    assert response.status_code == 404


def test_enable_disable_tool(client):
    """Test enabling and disabling tools."""
    # Disable a tool
    response = client.post("/tools/structure/disable")
    assert response.status_code == 200
    
    # Enable it back
    response = client.post("/tools/structure/enable")
    assert response.status_code == 200


def test_get_report(client, sample_project):
    """Test retrieving a generated report."""
    # First create a report
    audit_response = client.post(
        "/audit",
        json={
            "path": str(sample_project),
            "dry_run": False
        }
    )
    
    assert audit_response.status_code == 200
    report_id = audit_response.json()["report_id"]
    
    # Now retrieve it
    report_response = client.get(f"/report/{report_id}")
    assert report_response.status_code == 200
    assert "Project Audit" in report_response.text


def test_get_nonexistent_report(client):
    """Test retrieving a report that doesn't exist."""
    response = client.get("/report/nonexistent")
    assert response.status_code == 404
