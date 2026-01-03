"""Base tool interface for analysis plugins."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """Base class for all analysis tools."""
    
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
    
    def validate_path(self, path: Path) -> bool:
        """Validate that the path exists and is accessible."""
        if not path.exists():
            logger.error(f"Path does not exist: {path}")
            return False
        if not path.is_dir():
            logger.error(f"Path is not a directory: {path}")
            return False
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled
        }
