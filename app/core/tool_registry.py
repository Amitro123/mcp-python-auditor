"""Dynamic tool registry for loading analysis plugins."""
import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Type, Optional
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for dynamically loading and managing analysis tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
    
    def discover_tools(self, tools_dir: Path) -> None:
        """
        Discover and load all tools from the tools directory.
        
        Args:
            tools_dir: Path to the tools directory
        """
        if not tools_dir.exists():
            logger.warning(f"Tools directory does not exist: {tools_dir}")
            return
        
        # Find all Python files in tools directory
        tool_files = [f for f in tools_dir.glob("*_tool.py") if f.is_file()]
        
        for tool_file in tool_files:
            try:
                self._load_tool_from_file(tool_file)
            except Exception as e:
                logger.error(f"Failed to load tool from {tool_file}: {e}")
    
    def _load_tool_from_file(self, tool_file: Path) -> None:
        """Load a tool from a Python file."""
        module_name = f"app.tools.{tool_file.stem}"
        
        try:
            # Import the module
            module = importlib.import_module(module_name)
            
            # Find all BaseTool subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool:
                    # Instantiate the tool
                    tool_instance = obj()
                    self._tools[tool_instance.name] = tool_instance
                    self._tool_classes[tool_instance.name] = obj
                    logger.info(f"Loaded tool: {tool_instance.name}")
        
        except Exception as e:
            logger.error(f"Error loading module {module_name}: {e}")
            raise
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool instance by name."""
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_enabled_tools(self) -> Dict[str, BaseTool]:
        """Get all enabled tools."""
        return {name: tool for name, tool in self._tools.items() if tool.enabled}
    
    def list_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())
    
    def enable_tool(self, tool_name: str) -> bool:
        """Enable a specific tool."""
        tool = self._tools.get(tool_name)
        if tool:
            tool.enabled = True
            return True
        return False
    
    def disable_tool(self, tool_name: str) -> bool:
        """Disable a specific tool."""
        tool = self._tools.get(tool_name)
        if tool:
            tool.enabled = False
            return True
        return False


# Global registry instance
registry = ToolRegistry()
