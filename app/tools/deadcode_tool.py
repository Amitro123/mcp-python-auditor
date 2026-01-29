"""Dead code detection tool using Vulture with Safety-First Execution."""
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
from app.core.subprocess_wrapper import SubprocessWrapper
from app.core.command_chunker import run_tool_in_chunks, filter_python_files, validate_file_list
import logging
import json
import subprocess
import sys

logger = logging.getLogger(__name__)


class DeadcodeTool(BaseTool):
    """Detect unused code using Vulture library."""
    
    @property
    def name(self) -> str:
        return "deadcode"

    @property
    def description(self) -> str:
        return "Detects unused functions, classes, variables, and imports using Vulture"
    
    def analyze(self, project_path: Path, file_list: List[str] = None) -> Dict[str, Any]:
        """Analyze code for dead/unused code using Vulture."""
        try:
            # Run vulture with timeout
            # Note: Explicitly using project path scan instead of file list for simplicity
            excludes = "venv,.venv,dist,build,tests,.git,__pycache__,.gemini,node_modules"
            
            result = subprocess.run(
                [sys.executable, '-m', 'vulture', str(project_path), '--exclude', excludes],
                capture_output=True,
                text=True,
                timeout=120  # 2 min max
            )
            
            items = self._parse_vulture_output(result.stdout)
            
            return {
                'tool': 'deadcode',
                'status': 'pass' if len(items) == 0 else 'issues_found',
                'items': items,
                'total_items': len(items)
            }
        except subprocess.TimeoutExpired:
            logger.error("Vulture timeout")
            return {
                'tool': 'deadcode',
                'status': 'timeout',
                'items': [],
                'total_items': 0
            }
        except Exception as e:
            logger.error(f"Deadcode analysis failed: {e}")
            return {
                'tool': 'deadcode',
                'status': 'error',
                'error': str(e),
                'items': [],
                'total_items': 0
            }
    
    def _parse_vulture_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse vulture text output."""
        items = []
        
        for line in output.strip().split('\n'):
            if not line or line.startswith('#'):
                continue
            
            # Vulture output format: file:line: message
            parts = line.split(':', 2)
            if len(parts) >= 3:
                file_path = parts[0].strip()
                line_num = parts[1].strip()
                message = parts[2].strip()
                
                # Determine type from message
                item_type = 'unknown'
                if 'function' in message.lower():
                    item_type = 'function'
                elif 'class' in message.lower():
                    item_type = 'class'
                elif 'variable' in message.lower():
                    item_type = 'variable'
                elif 'import' in message.lower():
                    item_type = 'import'
                
                # Extract name
                name = self._extract_name_from_message(message)
                
                items.append({
                    "file": file_path,
                    "line": int(line_num) if line_num.isdigit() else 0,
                    "type": item_type,
                    "name": name,
                    "message": message
                })
        
        return items
    
    def _extract_name_from_message(self, message: str) -> str:
        """Extract item name from vulture message."""
        # Try to extract quoted name
        if "'" in message:
            parts = message.split("'")
            if len(parts) >= 2:
                return parts[1]
        
        # Fallback: take first word after 'unused'
        words = message.lower().split()
        if 'unused' in words:
            idx = words.index('unused')
            if idx + 2 < len(words):
                return words[idx + 2].strip("'\"")
        
        return "unknown"
    
    def _fallback_analysis(self, project_path: Path) -> Dict[str, Any]:
        """Fallback to basic analysis if vulture is not available."""
        logger.info("Using fallback dead code analysis")
        
        return {
            "status": "skipped",
            "dead_functions": [],
            "dead_classes": [],
            "dead_variables": [],
            "unused_imports": [],
            "total_dead": 0,
            "confidence": "skipped",
            "tool": "fallback",
            "message": "Vulture not installed - install with: pip install vulture"
        }
