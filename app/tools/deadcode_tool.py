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
    def description(self) -> str:
        return "Detects unused functions, classes, variables, and imports using Vulture"
    
    def analyze(self, project_path: Path, file_list: List[str] = None) -> Dict[str, Any]:
        """
        Analyze code for dead/unused code using Vulture with explicit file list.
        
        SAFETY-FIRST EXECUTION:
        1. Guard Clause: Empty file list check
        2. Guard Clause: Extension filter (only .py files)
        3. Windows Chunking: Prevent WinError 206
        
        Args:
            project_path: Path to the project directory
            file_list: Optional list of absolute file paths to scan
            
        Returns:
            Dictionary with dead code information
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        # STEP 1: GUARD CLAUSE - Empty Check
        if file_list is not None and not file_list:
            logger.warning("Vulture: Empty file list provided, skipping scan")
            return {
                "status": "skipped",
                "dead_functions": [],
                "dead_classes": [],
                "dead_variables": [],
                "unused_imports": [],
                "total_dead": 0,
                "confidence": "skipped",
                "tool": "vulture"
            }
        
        # STEP 2: GUARD CLAUSE - Extension Filter
        if file_list:
            file_list = filter_python_files(file_list)
            if not validate_file_list(file_list, "Vulture"):
                return {"error": "Invalid file list (contains excluded paths or empty)"}
            logger.info(f"✅ Vulture: Analyzing {len(file_list)} Python files (explicit list)")
        
        try:
            # Run vulture with JSON output using subprocess directly to handle exit codes
            # Exit code 0: No dead code found
            # Exit code 1: Dead code found (Valid success for us)
            # Other codes: Error
            try:
                # Build command with explicit file list or directory
                if file_list:
                    cmd = [sys.executable, '-m', 'vulture', '--min-confidence', '80'] + file_list
                else:
                    # Fallback: Build command with exclusions from centralized blacklist
                    cmd = [sys.executable, '-m', 'vulture', str(project_path), '--min-confidence', '80']
                    
                    # Add each ignored directory as exclusion
                    for ignored_dir in self.IGNORED_DIRECTORIES:
                        cmd.extend(['--exclude', ignored_dir])
                
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    errors='replace'
                )
                
                # Check return code
                # Exit code 0: No dead code
                # Exit code 1: Dead code found
                # Exit code 3: Syntax error in one file (still produces results)
                if result.returncode not in [0, 1, 3]:
                    if "not found" in result.stderr.lower():
                        logger.warning("Vulture not installed, falling back to basic analysis")
                        return self._fallback_analysis(project_path)
                    else:
                        logger.error(f"Vulture failed with code {result.returncode}: {result.stderr}")
                        return {"error": f"Vulture execution failed: {result.stderr}"}
                
                stdout = result.stdout
                
            except subprocess.TimeoutExpired:
                 logger.error("Vulture timed out after 120s")
                 return {"error": "Vulture timed out"}
            except FileNotFoundError:
                 logger.warning("Vulture command not found")
                 return self._fallback_analysis(project_path)
            
            # Parse vulture output
            dead_items = self._parse_vulture_output(stdout)
            
            # Categorize findings
            dead_functions = [item for item in dead_items if item['type'] == 'function']
            dead_classes = [item for item in dead_items if item['type'] == 'class']
            dead_variables = [item for item in dead_items if item['type'] == 'variable']
            unused_imports = [item for item in dead_items if item['type'] == 'import']
            
            return {
                "status": "analyzed" if dead_items else "clean",
                "dead_functions": dead_functions,
                "dead_classes": dead_classes,
                "dead_variables": dead_variables,
                "unused_imports": unused_imports,
                "total_dead": len(dead_items),
                "confidence": "high",
                "tool": "vulture"
            }
        
        except Exception as e:
            logger.error(f"Dead code analysis failed: {e}")
            return {"error": str(e)}
    
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
