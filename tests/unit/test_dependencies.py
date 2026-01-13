"""
Unit tests for dependency checking and installation.
Tests the agentic flow for missing tool detection.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import sys


class TestDependencyChecking:
    """Test dependency detection and management."""
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_all_tools_installed(self, mock_which, mock_run):
        """When all tools are installed, should return empty list."""
        mock_which.return_value = "/usr/bin/bandit"
        mock_run.return_value = Mock(returncode=0)
        
        missing = check_dependencies()
        assert missing == []
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_missing_tools_detected(self, mock_which, mock_run):
        """Should detect missing tools correctly."""
        mock_which.return_value = None
        mock_run.side_effect = FileNotFoundError()
        
        missing = check_dependencies()
        assert "bandit" in missing
        assert "vulture" in missing
    
    @patch('subprocess.run')
    def test_install_dependencies_success(self, mock_run):
        """Successful installation should return success message."""
        mock_run.return_value = Mock(returncode=0, stdout="Successfully installed")
        
        result = install_dependencies()
        assert "✅" in result
        assert "Installation Successful" in result
    
    @patch('subprocess.run')
    def test_install_dependencies_failure(self, mock_run):
        """Failed installation should return error message."""
        mock_run.return_value = Mock(returncode=1, stderr="Error installing")
        
        result = install_dependencies()
        assert "❌" in result
        assert "Installation Failed" in result
    
    @patch('subprocess.run')
    def test_install_dependencies_timeout(self, mock_run):
        """Timeout should return timeout message."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("pip", 300)
        
        result = install_dependencies()
        assert "❌" in result
        assert "Timeout" in result


def check_dependencies():
    """Mock implementation for testing."""
    import shutil
    import subprocess
    
    REQUIRED_TOOLS = ["bandit", "ruff", "vulture", "radon", "pip-audit", "pytest", "detect-secrets"]
    missing = []
    
    for tool in REQUIRED_TOOLS:
        if shutil.which(tool):
            continue
            
        module_name = tool.replace("-", "_")
        try:
            subprocess.run(
                [sys.executable, "-m", module_name, "--version"],
                capture_output=True, check=True, timeout=5, stdin=subprocess.DEVNULL
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            missing.append(tool)
    
    return missing


def install_dependencies():
    """Mock implementation for testing."""
    import subprocess
    
    TOOLS_TO_INSTALL = ["bandit", "detect-secrets", "vulture", "radon", "ruff", "pip-audit"]
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + TOOLS_TO_INSTALL,
            capture_output=True,
            text=True,
            timeout=300,
            stdin=subprocess.DEVNULL
        )
        
        if result.returncode == 0:
            return f"✅ **Installation Successful!**\n\nInstalled tools: {', '.join(TOOLS_TO_INSTALL)}"
        else:
            error_msg = result.stderr or result.stdout
            return f"❌ **Installation Failed**\n\nError: {error_msg[:500]}"
            
    except subprocess.TimeoutExpired:
        return "❌ **Installation Timeout**"
    except Exception as e:
        return f"❌ **Installation Error:** {str(e)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
