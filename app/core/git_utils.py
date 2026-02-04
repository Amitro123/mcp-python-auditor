"""Git utility functions for the audit system."""

import subprocess
from pathlib import Path


def get_pr_files(base: str = "origin/main") -> list[Path]:
    """Get Python files changed vs base branch.

    Args:
        base: Base branch to compare against (default: "origin/main")

    Returns:
        List of Path objects for changed Python files that exist
    """
    try:
        import shutil

        git_cmd = shutil.which("git") or "git"
        result = subprocess.run(
            [git_cmd, "diff", "--name-only", base],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return []

        # Filter for .py files that exist and convert to Path objects
        changed_files = []
        for filename in result.stdout.strip().split("\n"):
            if filename.endswith(".py"):
                file_path = Path(filename)
                if file_path.exists():
                    changed_files.append(file_path)

        return changed_files
    except Exception:
        return []
