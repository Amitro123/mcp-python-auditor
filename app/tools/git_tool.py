"""Git analysis tool - Track recent changes and commits."""
import subprocess
from pathlib import Path
from typing import Dict, Any
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class GitTool(BaseTool):
    """Analyze git repository for recent changes."""
    
    @property
    def description(self) -> str:
        return "Analyzes git repository for recent changes and commit history"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze git repository.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with git information
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            # Check if this is a git repository
            has_git = (project_path / ".git").exists()
            
            if not has_git:
                return {
                    "has_git": False,
                    "diff_stat": "",
                    "last_commit": "",
                    "message": "Not a git repository"
                }
            
            # Get diff stats
            diff_stat = self._get_diff_stat(project_path)
            
            # Get last commit details
            last_commit = self._get_last_commit(project_path)
            commit_hash = self._get_commit_hash(project_path)
            commit_author = self._get_commit_author(project_path)
            commit_date = self._get_commit_date(project_path)
            days_since = self._get_days_since_commit(project_path)
            
            # Get branch info
            branch = self._get_current_branch(project_path)
            
            # Check for uncommitted changes
            has_changes = self._has_uncommitted_changes(project_path)
            
            return {
                "has_git": True,
                "diff_stat": diff_stat,
                "last_commit": last_commit,
                "commit_hash": commit_hash,
                "commit_author": commit_author,
                "commit_date": commit_date,
                "days_since_commit": days_since,
                "branch": branch,
                "has_uncommitted_changes": has_changes,
                "status": "Clean" if not has_changes else "Uncommitted changes"
            }
        except Exception as e:
            logger.error(f"Git analysis failed: {e}")
            return {"error": str(e)}
    
    def _get_commit_hash(self, path: Path) -> str:
        """Get short commit hash."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=format:%h'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""
    
    def _get_commit_author(self, path: Path) -> str:
        """Get commit author."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=format:%an'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""
    
    def _get_commit_date(self, path: Path) -> str:
        """Get commit date (relative)."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=format:%ar'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""
    
    def _get_days_since_commit(self, path: Path) -> int:
        """Get days since last commit."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=format:%ct'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            if result.returncode == 0:
                import time
                timestamp = int(result.stdout.strip())
                days = int((time.time() - timestamp) / 86400)
                return days
            return 0
        except:
            return 0
    
    def _get_current_branch(self, path: Path) -> str:
        """Get current branch name."""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def _has_uncommitted_changes(self, path: Path) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            return len(result.stdout.strip()) > 0 if result.returncode == 0 else False
        except:
            return False
    
    def _get_diff_stat(self, path: Path) -> str:
        """Get git diff --stat output."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--stat'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=path
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return ""
        except subprocess.TimeoutExpired:
            logger.warning("git diff timed out")
            return ""
        except FileNotFoundError:
            logger.debug("git command not found")
            return ""
        except Exception as e:
            logger.debug(f"git diff failed: {e}")
            return ""
    
    def _get_last_commit(self, path: Path) -> str:
        """Get git log -1 output."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=format:%h - %an, %ar : %s'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=path
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return ""
        except subprocess.TimeoutExpired:
            logger.warning("git log timed out")
            return ""
        except FileNotFoundError:
            logger.debug("git command not found")
            return ""
        except Exception as e:
            logger.debug(f"git log failed: {e}")
            return ""
