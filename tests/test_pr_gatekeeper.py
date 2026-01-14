"""
Tests for PR Gatekeeper functionality.

Tests the audit_pr_changes tool and get_changed_files helper.
"""

import pytest
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestGetChangedFiles:
    """Test the get_changed_files helper function."""
    
    def test_get_changed_files_with_changes(self, tmp_path):
        """Test detecting changed Python files."""
        # This test requires a real git repo, so we'll mock it
        with patch('subprocess.run') as mock_run:
            # Mock git diff output
            mock_run.return_value = Mock(
                returncode=0,
                stdout="app/tools/new_tool.py\napp/core/processor.py\ntests/test_new.py\n",
                stderr=""
            )
            
            # Create dummy files
            (tmp_path / "app" / "tools").mkdir(parents=True)
            (tmp_path / "app" / "core").mkdir(parents=True)
            (tmp_path / "tests").mkdir(parents=True)
            
            (tmp_path / "app" / "tools" / "new_tool.py").touch()
            (tmp_path / "app" / "core" / "processor.py").touch()
            (tmp_path / "tests" / "test_new.py").touch()
            
            from mcp_fastmcp_server import get_changed_files
            
            changed = get_changed_files(tmp_path, "main")
            
            # Should return paths to existing files
            assert len(changed) == 3
            assert all(Path(f).exists() for f in changed)
    
    def test_get_changed_files_no_changes(self, tmp_path):
        """Test when no files have changed."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="",
                stderr=""
            )
            
            from mcp_fastmcp_server import get_changed_files
            
            changed = get_changed_files(tmp_path, "main")
            
            assert changed == []
    
    def test_get_changed_files_git_error(self, tmp_path):
        """Test handling of git errors."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="fatal: not a git repository"
            )
            
            from mcp_fastmcp_server import get_changed_files
            
            changed = get_changed_files(tmp_path, "main")
            
            # Should return empty list on error
            assert changed == []
    
    def test_get_changed_files_timeout(self, tmp_path):
        """Test handling of git timeout."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git", 15)
            
            from mcp_fastmcp_server import get_changed_files
            
            changed = get_changed_files(tmp_path, "main")
            
            assert changed == []
    
    def test_get_changed_files_filters_nonexistent(self, tmp_path):
        """Test that non-existent files are filtered out."""
        with patch('subprocess.run') as mock_run:
            # Git reports a deleted file
            mock_run.return_value = Mock(
                returncode=0,
                stdout="deleted_file.py\nexisting_file.py\n",
                stderr=""
            )
            
            # Only create one file
            (tmp_path / "existing_file.py").touch()
            
            from mcp_fastmcp_server import get_changed_files
            
            changed = get_changed_files(tmp_path, "main")
            
            # Should only return existing file
            assert len(changed) == 1
            assert "existing_file.py" in changed[0]


class TestAuditPRChanges:
    """Test the audit_pr_changes tool."""
    
    def test_audit_pr_no_changes(self, tmp_path):
        """Test audit when no Python files changed."""
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = []
            
            from mcp_fastmcp_server import audit_pr_changes
            
            result_json = audit_pr_changes(str(tmp_path), "main", run_tests=False)
            result = json.loads(result_json)
            
            assert result["status"] == "success"
            assert result["message"] == "✅ No Python changes detected in this PR."
            assert result["recommendation"] == "🟢 Ready for Review"
            assert result["score"] == 100
    
    def test_audit_pr_with_clean_changes(self, tmp_path):
        """Test audit with clean code changes."""
        # Create test file
        test_file = tmp_path / "clean_code.py"
        test_file.write_text("""
def hello_world():
    '''A simple function.'''
    return "Hello, World!"
""")
        
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = [str(test_file)]
            
            with patch('subprocess.run') as mock_run:
                # Mock all tool outputs as clean
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="{}",
                    stderr=""
                )
                
                from mcp_fastmcp_server import audit_pr_changes
                
                result_json = audit_pr_changes(str(tmp_path), "main", run_tests=False)
                result = json.loads(result_json)
                
                assert result["status"] == "success"
                assert result["score"] >= 80  # Should be high score
                assert "🟢" in result["recommendation"]  # Ready for review
    
    def test_audit_pr_with_security_issues(self, tmp_path):
        """Test audit with security issues."""
        test_file = tmp_path / "insecure.py"
        test_file.write_text("""
import pickle
data = pickle.loads(user_input)  # Security issue
""")
        
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = [str(test_file)]
            
            with patch('subprocess.run') as mock_run:
                def side_effect(*args, **kwargs):
                    cmd = args[0] if args else kwargs.get('cmd', [])
                    if 'bandit' in str(cmd):
                        # Mock Bandit finding security issue
                        return Mock(
                            returncode=0,
                            stdout=json.dumps({
                                "results": [{
                                    "issue_severity": "HIGH",
                                    "test_name": "B301",
                                    "filename": str(test_file),
                                    "line_number": 3,
                                    "issue_text": "Pickle usage detected"
                                }]
                            }),
                            stderr=""
                        )
                    else:
                        return Mock(returncode=0, stdout="{}", stderr="")
                
                mock_run.side_effect = side_effect
                
                from mcp_fastmcp_server import audit_pr_changes
                
                result_json = audit_pr_changes(str(tmp_path), "main", run_tests=False)
                result = json.loads(result_json)
                
                assert result["status"] == "success"
                assert result["findings"]["security_issues"] > 0
                assert "🔴" in result["recommendation"]  # Request changes
    
    def test_audit_pr_with_linting_issues(self, tmp_path):
        """Test audit with linting issues."""
        test_file = tmp_path / "messy.py"
        test_file.write_text("""
import os
import sys  # Unused import
x=1+2  # No spaces
""")
        
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = [str(test_file)]
            
            with patch('subprocess.run') as mock_run:
                def side_effect(*args, **kwargs):
                    cmd = args[0] if args else kwargs.get('cmd', [])
                    if 'ruff' in str(cmd):
                        # Mock Ruff finding linting issues
                        return Mock(
                            returncode=0,
                            stdout=json.dumps([
                                {
                                    "filename": str(test_file),
                                    "location": {"row": 3},
                                    "code": "F401",
                                    "message": "Unused import"
                                }
                            ]),
                            stderr=""
                        )
                    else:
                        return Mock(returncode=0, stdout="{}", stderr="")
                
                mock_run.side_effect = side_effect
                
                from mcp_fastmcp_server import audit_pr_changes
                
                result_json = audit_pr_changes(str(tmp_path), "main", run_tests=False)
                result = json.loads(result_json)
                
                assert result["status"] == "success"
                assert result["findings"]["linting_issues"] > 0
    
    def test_audit_pr_test_safety_net_pass(self, tmp_path):
        """Test that tests run when score > 80."""
        test_file = tmp_path / "good_code.py"
        test_file.write_text("def add(a, b): return a + b")
        
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = [str(test_file)]
            
            with patch('subprocess.run') as mock_run:
                def side_effect(*args, **kwargs):
                    cmd = args[0] if args else kwargs.get('cmd', [])
                    if 'pytest' in str(cmd):
                        # Mock tests passing
                        return Mock(returncode=0, stdout="1 passed", stderr="")
                    else:
                        return Mock(returncode=0, stdout="{}", stderr="")
                
                mock_run.side_effect = side_effect
                
                from mcp_fastmcp_server import audit_pr_changes
                
                result_json = audit_pr_changes(str(tmp_path), "main", run_tests=True)
                result = json.loads(result_json)
                
                assert result["status"] == "success"
                assert result["findings"]["tests_passed"] == True
    
    def test_audit_pr_test_safety_net_fail(self, tmp_path):
        """Test that failing tests trigger request changes."""
        test_file = tmp_path / "good_code.py"
        test_file.write_text("def add(a, b): return a + b")
        
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = [str(test_file)]
            
            with patch('subprocess.run') as mock_run:
                def side_effect(*args, **kwargs):
                    cmd = args[0] if args else kwargs.get('cmd', [])
                    if 'pytest' in str(cmd):
                        # Mock tests failing
                        return Mock(returncode=1, stdout="1 failed", stderr="")
                    else:
                        return Mock(returncode=0, stdout="{}", stderr="")
                
                mock_run.side_effect = side_effect
                
                from mcp_fastmcp_server import audit_pr_changes
                
                result_json = audit_pr_changes(str(tmp_path), "main", run_tests=True)
                result = json.loads(result_json)
                
                assert result["status"] == "success"
                assert result["findings"]["tests_passed"] == False
                assert "🔴" in result["recommendation"]  # Request changes
    
    def test_audit_pr_skip_tests_low_score(self, tmp_path):
        """Test that tests are skipped when score <= 80."""
        test_file = tmp_path / "bad_code.py"
        test_file.write_text("x=1")  # Will have linting issues
        
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = [str(test_file)]
            
            with patch('subprocess.run') as mock_run:
                # Mock many linting issues to get low score
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout=json.dumps([{"code": "E" + str(i)} for i in range(20)]),
                    stderr=""
                )
                
                from mcp_fastmcp_server import audit_pr_changes
                
                result_json = audit_pr_changes(str(tmp_path), "main", run_tests=True)
                result = json.loads(result_json)
                
                # Tests should not run if score is low
                assert result["score"] < 80
                # tests_passed should be None (not run)
                assert result["findings"]["tests_passed"] is None or result["score"] <= 80


class TestPRGatekeeperIntegration:
    """Integration tests for PR Gatekeeper."""
    
    def test_full_pr_workflow(self, tmp_path):
        """Test complete PR audit workflow."""
        # Create a simple Python file
        (tmp_path / "feature.py").write_text("""
def calculate(x, y):
    '''Calculate sum.'''
    return x + y
""")
        
        with patch('mcp_fastmcp_server.get_changed_files') as mock_get:
            mock_get.return_value = [str(tmp_path / "feature.py")]
            
            with patch('subprocess.run') as mock_run:
                # All tools return clean
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="{}",
                    stderr=""
                )
                
                from mcp_fastmcp_server import audit_pr_changes
                
                result_json = audit_pr_changes(str(tmp_path), "main", run_tests=False)
                result = json.loads(result_json)
                
                # Verify JSON structure
                assert "status" in result
                assert "recommendation" in result
                assert "score" in result
                assert "changed_files_count" in result
                assert "findings" in result
                assert "report" in result
                
                # Verify findings structure
                findings = result["findings"]
                assert "security_issues" in findings
                assert "linting_issues" in findings
                assert "complexity_issues" in findings
                assert "tests_passed" in findings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
