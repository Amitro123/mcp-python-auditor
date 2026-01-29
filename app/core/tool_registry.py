"""Static tool registry for loading essential analysis tools."""
from typing import List
import logging
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for essential analysis tools."""
    
    @staticmethod
    def discover_tools() -> List[BaseTool]:
        """Return only essential code quality tools"""
        from app.tools.bandit_tool import BanditTool
        from app.tools.secrets_tool import SecretsTool
        from app.tools.tests_tool import TestsTool
        from app.tools.duplication_tool import DuplicationTool
        from app.tools.deadcode_tool import DeadcodeTool
        from app.tools.cleanup_tool import CleanupTool
        from app.tools.fast_audit_tool import FastAuditTool  # Ruff
        
        return [
            BanditTool(),
            SecretsTool(),
            TestsTool(),
            DuplicationTool(),
            DeadcodeTool(),
            CleanupTool(),
            FastAuditTool(),
        ]
        
registry = ToolRegistry()
