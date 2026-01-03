"""Configuration management for audit tools."""
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml
import logging

logger = logging.getLogger(__name__)


class AuditConfig:
    """Configuration for project audit."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from audit.yaml or pyproject.toml."""
        # Try audit.yaml first
        audit_yaml = self.project_path / "audit.yaml"
        if audit_yaml.exists():
            try:
                with open(audit_yaml, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    logger.info(f"Loaded config from {audit_yaml}")
                    return config.get('audit', config)
            except Exception as e:
                logger.warning(f"Failed to load audit.yaml: {e}")
        
        # Try pyproject.toml
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                # Python 3.11+ has tomllib built-in
                try:
                    import tomllib
                except ImportError:
                    # Fallback for Python < 3.11
                    try:
                        import tomli as tomllib
                    except ImportError:
                        tomllib = None
                
                if tomllib:
                    with open(pyproject, 'rb') as f:
                        data = tomllib.load(f)
                        config = data.get('tool', {}).get('audit', {})
                        if config:
                            logger.info(f"Loaded config from {pyproject}")
                            return config
            except Exception as e:
                logger.debug(f"Failed to load pyproject.toml: {e}")
        
        logger.info("No config file found, using defaults")
        return {}
    
    def get_exclude_paths(self) -> List[str]:
        """Get paths to exclude from analysis."""
        default_excludes = [
            '__pycache__',
            '.venv',
            'venv',
            'env',
            '.git',
            'node_modules',
            '.pytest_cache',
            '.mypy_cache',
            'migrations'
        ]
        
        custom_excludes = self.config_data.get('exclude', [])
        return default_excludes + custom_excludes
    
    def get_complexity_threshold(self) -> int:
        """Get cyclomatic complexity threshold."""
        return self.config_data.get('thresholds', {}).get('complexity', 10)
    
    def get_maintainability_threshold(self) -> int:
        """Get maintainability index threshold."""
        return self.config_data.get('thresholds', {}).get('maintainability', 20)
    
    def get_type_coverage_threshold(self) -> int:
        """Get type coverage threshold percentage."""
        return self.config_data.get('thresholds', {}).get('type_coverage', 50)
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check if a specific tool is enabled in config."""
        tools_config = self.config_data.get('tools', {})
        return tools_config.get(tool_name, {}).get('enabled', True)
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get configuration for a specific tool."""
        return self.config_data.get('tools', {}).get(tool_name, {})
    
    def should_exclude_path(self, path: Path) -> bool:
        """Check if a path should be excluded."""
        exclude_patterns = self.get_exclude_paths()
        path_str = str(path)
        
        for pattern in exclude_patterns:
            if pattern in path_str:
                return True
        
        return False
