import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Extensions to include
INCLUDE_EXTENSIONS = {".py"}

# Directories to strictly exclude in fallback mode
EXCLUDED_DIRS = {
    ".venv",
    "venv",
    "env",
    ".env",
    "test-venv",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    "htmlcov",
    ".git",
    ".idea",
    ".vscode",
    ".gemini",
    "scratch",
    "antigravity",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "eggs",
    ".eggs",
    "lib",
    "lib64",
    "parts",
    "sdist",
    "wheels",
}


def get_project_files(root_path: Path) -> list[str]:
    """Get all relevant project files using Git (primary) or os.walk (fallback).

    Args:
        root_path: The project root directory.

    Returns:
        List of absolute file paths.

    """
    root_path = root_path.resolve()

    # Strategy 1: Git-Native Discovery
    try:
        # Check if it's a git repo
        if (root_path / ".git").exists() or _is_inside_git_work_tree(root_path):
            files = _get_git_files(root_path)
            if files:
                logger.info(f"✅ Discovered {len(files)} files using Git.")
                return files
    except Exception as e:
        logger.warning(f"Git discovery failed: {e}. Falling back to os.walk.")

    # Strategy 2: Strict os.walk Fallback
    logger.info("Falling back to strict os.walk discovery.")
    return _get_files_fallback(root_path)


def _is_inside_git_work_tree(path: Path) -> bool:
    """Check if path is inside a git working tree."""
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(path),
            check=True,
            capture_output=True,
        )  # nosec
        return True
    except subprocess.CalledProcessError:
        return False


def _get_git_files(root_path: Path) -> list[str]:
    """Get files using git ls-files."""
    # List cached (tracked) and others (untracked but not ignored)
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]

    result = subprocess.run(cmd, cwd=str(root_path), capture_output=True, text=True, check=True)

    files = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue

        file_path = root_path / line.strip()

        # Filter by extension
        if file_path.suffix in INCLUDE_EXTENSIONS and file_path.exists():
            files.append(str(file_path.resolve()))

    return files


def _get_files_fallback(root_path: Path) -> list[str]:
    """Get files using strict os.walk."""
    discovered_files = []

    for root, dirs, files in os.walk(root_path):
        # Strict exclusion of directories
        # Modify dirs in-place to prevent recursion
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in INCLUDE_EXTENSIONS:
                discovered_files.append(str(file_path.resolve()))

    return discovered_files
