"""Git analysis tool - Track recent changes and commits."""
import logging
import subprocess
from pathlib import Path
from typing import Any

from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class GitTool(BaseTool):
    """Analyze git repository for recent changes."""

    @property
    def description(self) -> str:
        return "Analyzes git repository for recent changes and commit history"

    def analyze(self, project_path: Path) -> dict[str, Any]:
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

            # Check for uncommitted changes (Fastest check first)
            has_changes = self._has_uncommitted_changes(project_path)

            # Get diff stats only if changes exist
            diff_stat = self._get_diff_stat(project_path) if has_changes else ""

            # Get last commit details
            last_commit = self._get_last_commit(project_path)
            commit_hash = self._get_commit_hash(project_path)
            commit_author = self._get_commit_author(project_path)
            commit_date = self._get_commit_date(project_path)
            days_since = self._get_days_since_commit(project_path)

            # Get branch info
            branch = self._get_current_branch(project_path)

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

    def _run_git_log_format(self, path: Path, format_str: str, default: str = "") -> str:
        """Run git log with a format string - eliminates duplication."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", f"--pretty=format:{format_str}"],  # nosec B607 - git is a trusted system command
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            return result.stdout.strip() if result.returncode == 0 else default
        except Exception:
            return default

    def _get_commit_hash(self, path: Path) -> str:
        """Get short commit hash."""
        return self._run_git_log_format(path, "%h")

    def _get_commit_author(self, path: Path) -> str:
        """Get commit author."""
        return self._run_git_log_format(path, "%an")

    def _get_commit_date(self, path: Path) -> str:
        """Get commit date (relative)."""
        return self._run_git_log_format(path, "%ar")

    def _get_days_since_commit(self, path: Path) -> int:
        """Get days since last commit."""
        try:
            timestamp_str = self._run_git_log_format(path, "%ct")
            if timestamp_str:
                import time
                timestamp = int(timestamp_str)
                return int((time.time() - timestamp) / 86400)
            return 0
        except Exception:
            return 0

    def _get_current_branch(self, path: Path) -> str:
        """Get current branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],  # nosec B607 - git is a trusted system command
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
            return "unknown"
        except Exception:
            return "unknown"

    def _has_uncommitted_changes(self, path: Path) -> bool:
        """Check if there are uncommitted changes."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],  # nosec B607 - git is a trusted system command
                capture_output=True,
                text=True,
                timeout=5,
                cwd=path
            )
            return len(result.stdout.strip()) > 0 if result.returncode == 0 else False
        except Exception:
            return False

    def _get_diff_stat(self, path: Path) -> str:
        """Get git diff --stat output."""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],  # nosec B607 - git is a trusted system command
                capture_output=True,
                text=True,
                timeout=10,
                cwd=path
            )

            if result.returncode == 0:
                return result.stdout.strip()
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
                ["git", "log", "-1", "--pretty=format:%h - %an, %ar : %s"],  # nosec B607 - git is a trusted system command
                capture_output=True,
                text=True,
                timeout=10,
                cwd=path
            )

            if result.returncode == 0:
                return result.stdout.strip()
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
