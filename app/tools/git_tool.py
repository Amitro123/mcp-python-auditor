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
            
            # Get last commit
            last_commit = self._get_last_commit(project_path)
            
            return {
                "has_git": True,
                "diff_stat": diff_stat,
                "last_commit": last_commit
            }
        except Exception as e:
            logger.error(f"Git analysis failed: {e}")
            return {"error": str(e)}
    
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
