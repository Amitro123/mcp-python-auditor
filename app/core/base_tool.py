"""Base tool interface for analysis plugins."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Generator
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all analysis tools."""
    
    # Centralized blacklist - ALL tools MUST respect this
    IGNORED_DIRECTORIES = {
        "__pycache__", "venv", ".venv", "env", ".env", "test-venv",  # Virtual Envs
        "node_modules", "site-packages", "dist", "build", "htmlcov",  # Artifacts
        ".git", ".idea", ".vscode", ".gemini", "scratch", "antigravity",  # System
        "fresh-install-test", ".pytest_cache", "pytest_cache", ".mypy_cache", ".tox",  # Test cache
        "eggs", ".eggs", "lib", "lib64", "parts", "sdist", "wheels"  # More build artifacts
    }
    
    def __init__(self, config: Optional[Any] = None):
        self.name = self.__class__.__name__.replace('Tool', '').lower()
        self.version = "1.0.0"
        self.enabled = True
        self.config = config
    
    @abstractmethod
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Perform analysis on the project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary containing analysis results
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return tool description."""
        pass
    
    def validate_path(self, path: str | Path) -> bool:
        """
        Validate path and ensure it's not inside an ignored directory.
        
        Args:
            path: Path to validate (can be string or Path object)
            
        Returns:
            False if path is in an ignored directory, True otherwise
        """
        path = Path(path) if isinstance(path, str) else path
        
        # Check if path exists and is directory (for project roots)
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            return False
        
        # Check if any part of the path is in the ignored list
        parts = path.parts
        for part in parts:
            if part in self.IGNORED_DIRECTORIES:
                return False
        
        return True
    
    def walk_project_files(self, root_path: Path, extension: str = ".py") -> Generator[Path, None, None]:
        """
        Walk project files while respecting the centralized exclusion list.
        
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
            dirs[:] = [
                d for d in dirs 
                if d not in self.IGNORED_DIRECTORIES and not d.startswith('.')
            ]
            
            for file in files:
                if file.endswith(extension):
                    file_path = Path(root) / file
                    # Double-check the path is valid (belt and suspenders)
                    if self.validate_path(file_path):
                        yield file_path
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled
        }
