"""Base tool interface for analysis plugins."""

import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Generator
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all analysis tools."""

    # Centralized blacklist - ALL tools MUST respect this
    # NOTE: Only include directories that should NEVER be scanned inside a project
    # Do NOT include workspace directories like .gemini, scratch, etc.
    IGNORED_DIRECTORIES = {
        "__pycache__",
        "venv",
        ".venv",
        "env",
        ".env",
        "test-venv",  # Virtual Envs
        "node_modules",
        "site-packages",
        "dist",
        "build",
        "htmlcov",  # Artifacts
        ".git",
        ".idea",
        ".vscode",  # IDE/VCS (not workspace dirs)
        ".pytest_cache",
        "pytest_cache",
        ".mypy_cache",
        ".tox",  # Test cache
        "eggs",
        ".eggs",
        "lib",
        "lib64",
        "parts",
        "sdist",
        "wheels",  # Build artifacts
        ".ruff_cache",
        ".coverage",
        "reports",
        "backups",  # Tool outputs
    }

    def __init__(self, config: Any | None = None):
        self.name = self.__class__.__name__.replace("Tool", "").lower()
        self.version = "1.0.0"
        self.enabled = True
        self.config = config

    @abstractmethod
    def analyze(self, project_path: Path) -> dict[str, Any]:
        """Perform analysis on the project.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary containing analysis results

        """

    @property
    @abstractmethod
    def description(self) -> str:
        """Return tool description."""

    def validate_path(self, path: str | Path, project_root: Path | None = None) -> bool:
        """Validate path and ensure it's not inside an ignored directory.

        IMPORTANT: This only checks for ignored directories WITHIN the project,
        not in the absolute path TO the project. This allows projects to be
        located in system directories like .gemini/scratch.

        Args:
            path: Path to validate (can be string or Path object)
            project_root: Optional project root to check relative paths

        Returns:
            False if path is in an ignored directory, True otherwise

        """
        path = Path(path) if isinstance(path, str) else path

        # Check if path exists
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            return False

        # If we have a project root, only check parts AFTER the root
        if project_root:
            try:
                # Get the relative path from project root
                rel_path = path.relative_to(project_root)
                parts_to_check = rel_path.parts
            except ValueError:
                # Path is not relative to project_root, check all parts
                parts_to_check = path.parts
        else:
            # No project root specified, this is likely the project root itself
            # Only reject if it's a directory that should never be scanned
            # (but allow the project to BE in a system directory)
            return True

        # Check if any part of the RELATIVE path is in the ignored list
        ignored_lower = {d.lower() for d in self.IGNORED_DIRECTORIES}
        for part in parts_to_check:
            if part.lower() in ignored_lower:
                return False

        return True

    def walk_project_files(self, root_path: Path, extension: str = ".py") -> Generator[Path, None, None]:
        """Walk project files while respecting the centralized exclusion list.

        This is the REQUIRED method for all tools to iterate over files.
        It prevents recursion into blacklisted directories.

        Args:
            root_path: Root directory to walk
            extension: File extension to match (default: ".py")

        Yields:
            Path objects for valid files

        """
        for root, dirs, files in os.walk(root_path):
            # CRITICAL: Modify dirs IN-PLACE to prevent os.walk from descending into them
            # Use case-insensitive comparison for Windows compatibility
            ignored_lower = {d.lower() for d in self.IGNORED_DIRECTORIES}
            dirs[:] = [d for d in dirs if d.lower() not in ignored_lower and not d.startswith(".")]

            for file in files:
                if file.endswith(extension):
                    file_path = Path(root) / file
                    # Double-check the path is valid (belt and suspenders)
                    if self.validate_path(file_path):
                        yield file_path

    def get_info(self) -> dict[str, Any]:
        """Get tool information."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
        }
