"""
Tests for Remote Repository Auditing functionality.

Tests the audit_remote_repo tool.
"""

import pytest
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call


class TestRemoteAuditValidation:
    """Test URL validation and error handling."""
    
    def test_invalid_url_format(self):
        """Test rejection of invalid URL formats."""
        from mcp_fastmcp_server import audit_remote_repo
        
        result_json = audit_remote_repo("invalid-url", "main")
        result = json.loads(result_json)
        
        assert result["status"] == "error"
        assert "Invalid repository URL" in result["error"]
    
    def test_valid_https_url(self):
        """Test acceptance of HTTPS URLs."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            with patch('subprocess.run') as mock_run:
                # Mock successful clone
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                # Mock temp directory
                mock_temp.return_value.__enter__.return_value = tempfile.mkdtemp()
                
                from mcp_fastmcp_server import audit_remote_repo
                
                # Should not error on URL validation
                result_json = audit_remote_repo("https://github.com/user/repo.git", "main")
                result = json.loads(result_json)
                
                # May fail on other steps, but not URL validation
                assert "Invalid repository URL" not in result.get("error", "")
    
    def test_valid_ssh_url(self):
        """Test acceptance of SSH URLs."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                mock_temp.return_value.__enter__.return_value = tempfile.mkdtemp()
                
                from mcp_fastmcp_server import audit_remote_repo
                
                result_json = audit_remote_repo("git@github.com:user/repo.git", "main")
                result = json.loads(result_json)
                
                assert "Invalid repository URL" not in result.get("error", "")


class TestRemoteAuditCloning:
    """Test git clone functionality."""
    
    def test_repository_not_found(self):
        """Test handling of non-existent repository."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp_path = tempfile.mkdtemp()
            mock_temp.return_value.__enter__.return_value = mock_temp_path
            
            with patch('subprocess.run') as mock_run:
                # Mock git clone failure
                mock_run.return_value = Mock(
                    returncode=128,
                    stdout="",
                    stderr="fatal: repository not found"
                )
                
                from mcp_fastmcp_server import audit_remote_repo
                
                result_json = audit_remote_repo("https://github.com/user/nonexistent.git", "main")
                result = json.loads(result_json)
                
                assert result["status"] == "error"
                assert "not found" in result["error"].lower()
                assert "suggestion" in result
    
    def test_private_repository_auth_failure(self):
        """Test handling of private repository."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp_path = tempfile.mkdtemp()
            mock_temp.return_value.__enter__.return_value = mock_temp_path
            
            with patch('subprocess.run') as mock_run:
                # Mock authentication failure
                mock_run.return_value = Mock(
                    returncode=128,
                    stdout="",
                    stderr="fatal: Authentication failed"
                )
                
                from mcp_fastmcp_server import audit_remote_repo
                
                result_json = audit_remote_repo("https://github.com/user/private.git", "main")
                result = json.loads(result_json)
                
                assert result["status"] == "error"
                assert "authentication" in result["error"].lower() or "private" in result["error"].lower()
                assert "suggestion" in result
    
    def test_branch_not_found(self):
        """Test handling of non-existent branch."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp_path = tempfile.mkdtemp()
            mock_temp.return_value.__enter__.return_value = mock_temp_path
            
            with patch('subprocess.run') as mock_run:
                # Mock branch not found
                mock_run.return_value = Mock(
                    returncode=128,
                    stdout="",
                    stderr="fatal: Remote branch 'nonexistent' not found"
                )
                
                from mcp_fastmcp_server import audit_remote_repo
                
                result_json = audit_remote_repo("https://github.com/user/repo.git", "nonexistent")
                result = json.loads(result_json)
                
                assert result["status"] == "error"
                assert "branch" in result["error"].lower()
                assert "suggestion" in result
    
    def test_clone_timeout(self):
        """Test handling of clone timeout."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp_path = tempfile.mkdtemp()
            mock_temp.return_value.__enter__.return_value = mock_temp_path
            
            with patch('subprocess.run') as mock_run:
                # Mock timeout
                mock_run.side_effect = subprocess.TimeoutExpired("git", 300)
                
                from mcp_fastmcp_server import audit_remote_repo
                
                result_json = audit_remote_repo("https://github.com/user/huge-repo.git", "main")
                result = json.loads(result_json)
                
                assert result["status"] == "error"
                assert "timeout" in result["error"].lower()
                assert "suggestion" in result
    
    def test_git_not_installed(self):
        """Test handling when git is not installed."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp_path = tempfile.mkdtemp()
            mock_temp.return_value.__enter__.return_value = mock_temp_path
            
            with patch('subprocess.run') as mock_run:
                # Mock FileNotFoundError (git not found)
                mock_run.side_effect = FileNotFoundError("git not found")
                
                from mcp_fastmcp_server import audit_remote_repo
                
                result_json = audit_remote_repo("https://github.com/user/repo.git", "main")
                result = json.loads(result_json)
                
                assert result["status"] == "error"
                assert "git" in result["error"].lower()
                assert "install" in result["suggestion"].lower()


class TestRemoteAuditExecution:
    """Test audit execution on cloned repository."""
    
    def test_no_python_files(self, tmp_path):
        """Test handling of repository with no Python files."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            # Use real temp directory for file operations
            mock_temp.return_value.__enter__.return_value = str(tmp_path)
            
            with patch('subprocess.run') as mock_run:
                # Mock successful clone
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                # Create non-Python file
                (tmp_path / "README.md").write_text("# Test")
                
                from mcp_fastmcp_server import audit_remote_repo
                
                result_json = audit_remote_repo("https://github.com/user/repo.git", "main")
                result = json.loads(result_json)
                
                assert result["status"] == "warning"
                assert "no Python files" in result["message"].lower()
    
    def test_successful_audit(self, tmp_path):
        """Test successful audit of repository."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp.return_value.__enter__.return_value = str(tmp_path)
            
            # Create Python files
            (tmp_path / "app").mkdir()
            (tmp_path / "app" / "main.py").write_text("""
def hello():
    '''Say hello.'''
    return "Hello, World!"
""")
            (tmp_path / "tests").mkdir()
            (tmp_path / "tests" / "test_main.py").write_text("""
def test_hello():
    from app.main import hello
    assert hello() == "Hello, World!"
""")
            
            with patch('subprocess.run') as mock_run:
                # Mock successful clone
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                # Mock tool classes
                with patch('mcp_fastmcp_server.StructureTool') as mock_struct:
                    with patch('mcp_fastmcp_server.SecurityTool') as mock_sec:
                        # Mock tool results
                        mock_struct.return_value.analyze.return_value = {
                            "status": "analyzed",
                            "total_py_files": 2
                        }
                        mock_sec.return_value.analyze.return_value = {
                            "status": "clean",
                            "total_issues": 0
                        }
                        
                        from mcp_fastmcp_server import audit_remote_repo
                        
                        result_json = audit_remote_repo("https://github.com/user/repo.git", "main")
                        result = json.loads(result_json)
                        
                        assert result["status"] == "success"
                        assert "score" in result
                        assert "report" in result
                        assert "summary" in result
                        assert result["files_analyzed"] >= 2


class TestRemoteAuditCleanup:
    """Test temporary directory cleanup."""
    
    def test_cleanup_on_success(self, tmp_path):
        """Test that temp directory is cleaned up on success."""
        temp_dirs_created = []
        
        def track_temp_dir(*args, **kwargs):
            temp_dir = tempfile.mkdtemp()
            temp_dirs_created.append(temp_dir)
            
            class MockContext:
                def __enter__(self):
                    return temp_dir
                def __exit__(self, *args):
                    # Simulate cleanup
                    import shutil
                    if Path(temp_dir).exists():
                        shutil.rmtree(temp_dir)
            
            return MockContext()
        
        with patch('tempfile.TemporaryDirectory', side_effect=track_temp_dir):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                # Create a Python file in the temp dir
                with patch('pathlib.Path.glob') as mock_glob:
                    mock_glob.return_value = [Path("test.py")]
                    
                    with patch('mcp_fastmcp_server.StructureTool'):
                        from mcp_fastmcp_server import audit_remote_repo
                        
                        audit_remote_repo("https://github.com/user/repo.git", "main")
                        
                        # Verify temp directory was cleaned up
                        for temp_dir in temp_dirs_created:
                            assert not Path(temp_dir).exists(), "Temp directory should be cleaned up"
    
    def test_cleanup_on_error(self):
        """Test that temp directory is cleaned up even on error."""
        temp_dirs_created = []
        
        def track_temp_dir(*args, **kwargs):
            temp_dir = tempfile.mkdtemp()
            temp_dirs_created.append(temp_dir)
            
            class MockContext:
                def __enter__(self):
                    return temp_dir
                def __exit__(self, *args):
                    import shutil
                    if Path(temp_dir).exists():
                        shutil.rmtree(temp_dir)
            
            return MockContext()
        
        with patch('tempfile.TemporaryDirectory', side_effect=track_temp_dir):
            with patch('subprocess.run') as mock_run:
                # Simulate clone failure
                mock_run.return_value = Mock(
                    returncode=128,
                    stdout="",
                    stderr="fatal: repository not found"
                )
                
                from mcp_fastmcp_server import audit_remote_repo
                
                audit_remote_repo("https://github.com/user/nonexistent.git", "main")
                
                # Verify cleanup happened even though clone failed
                for temp_dir in temp_dirs_created:
                    assert not Path(temp_dir).exists(), "Temp directory should be cleaned up on error"


class TestRemoteAuditIntegration:
    """Integration tests for remote audit."""
    
    def test_full_remote_audit_workflow(self, tmp_path):
        """Test complete remote audit workflow."""
        with patch('tempfile.TemporaryDirectory') as mock_temp:
            mock_temp.return_value.__enter__.return_value = str(tmp_path)
            
            # Create realistic Python project
            (tmp_path / "src").mkdir()
            (tmp_path / "src" / "__init__.py").touch()
            (tmp_path / "src" / "main.py").write_text("""
'''Main module.'''

def process_data(data):
    '''Process data.'''
    return [x * 2 for x in data]

def main():
    '''Entry point.'''
    result = process_data([1, 2, 3])
    print(result)

if __name__ == '__main__':
    main()
""")
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
                
                # Mock all tool classes to avoid actual execution
                tools_to_mock = [
                    'StructureTool', 'ArchitectureTool', 'TypingTool',
                    'ComplexityTool', 'DuplicationTool', 'DeadcodeTool',
                    'CleanupTool', 'SecurityTool', 'SecretsTool',
                    'TestsTool', 'GitTool'
                ]
                
                patches = []
                for tool in tools_to_mock:
                    p = patch(f'mcp_fastmcp_server.{tool}')
                    mock_tool = p.start()
                    mock_tool.return_value.analyze.return_value = {"status": "clean"}
                    patches.append(p)
                
                try:
                    from mcp_fastmcp_server import audit_remote_repo
                    
                    result_json = audit_remote_repo("https://github.com/user/repo.git", "main")
                    result = json.loads(result_json)
                    
                    # Verify complete response structure
                    assert result["status"] == "success"
                    assert isinstance(result["score"], int)
                    assert 0 <= result["score"] <= 100
                    assert "repo_url" in result
                    assert "branch" in result
                    assert "duration" in result
                    assert "files_analyzed" in result
                    assert "report" in result
                    assert "summary" in result
                    
                    # Verify summary structure
                    summary = result["summary"]
                    assert "security_issues" in summary
                    assert "secrets_found" in summary
                    assert "test_coverage" in summary
                    assert "duplicates" in summary
                    assert "dead_code" in summary
                    assert "high_complexity" in summary
                    
                finally:
                    for p in patches:
                        p.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
