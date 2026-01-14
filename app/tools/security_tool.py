"""Security scanning tool using Bandit with Safety-First Execution."""
import json
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
from app.core.command_chunker import run_tool_in_chunks, filter_python_files, validate_file_list

logger = logging.getLogger(__name__)


class SecurityTool(BaseTool):
    """Scans code for security vulnerabilities using Bandit (Smart Targeting)."""
    
    @property
    def description(self) -> str:
        return "Scans code for security vulnerabilities using Bandit (Smart Targeting)."

    def analyze(self, project_path: Path, file_list: List[str] = None) -> Dict[str, Any]:
        """
        Analyze project for security vulnerabilities using explicit file list.
        
        SAFETY-FIRST EXECUTION:
        1. Guard Clause: Empty file list check
        2. Guard Clause: Extension filter (only .py files)
        3. Windows Chunking: Prevent WinError 206
        
        Args:
            project_path: Path to the project directory
            file_list: Optional list of absolute file paths to scan (from Git discovery)
            
        Returns:
            Dictionary with security findings
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path", "status": "error"}
        
        # STEP 1: GUARD CLAUSE - Empty Check
        if file_list is not None and not file_list:
            logger.warning("Bandit: Empty file list provided, skipping scan")
            return {
                "tool": "bandit",
                "status": "skipped",
                "message": "No files to scan",
                "files_scanned": 0,
                "total_issues": 0,
                "issues": [],
                "code_security": {"files_scanned": 0, "issues": []}
            }
        
        # STEP 2: GUARD CLAUSE - Extension Filter
        if file_list:
            file_list = filter_python_files(file_list)
            if not validate_file_list(file_list, "Bandit"):
                return {
                    "tool": "bandit",
                    "status": "error",
                    "error": "Invalid file list (contains excluded paths or empty)",
                    "files_scanned": 0,
                    "code_security": {"files_scanned": 0, "issues": []}
                }
            logger.info(f"✅ Bandit: Scanning {len(file_list)} Python files (explicit list)")
        
        # Build base command
        base_cmd = [sys.executable, "-m", "bandit", "-f", "json"]
        
        try:
            # STEP 3: WINDOWS CHUNKING
            if file_list:
                # Use chunking to prevent WinError 206
                result = run_tool_in_chunks(
                    base_cmd=base_cmd,
                    files=file_list,
                    chunk_size=50,
                    merge_json=True,
                    timeout=300
                )
            else:
                # Fallback: Directory scanning (not recommended)
                logger.warning("⚠️ Bandit: No file list provided, using fallback directory scan")
                target_path = Path(project_path).resolve()
                known_source_dirs = ["src", "app", "scripts", "lib", "core", "backend", "api"]
                scan_targets = []
                
                for folder in known_source_dirs:
                    p = target_path / folder
                    if p.exists() and p.is_dir():
                        scan_targets.append(str(p))
                
                targets = scan_targets if scan_targets else [str(target_path)]
                cmd = base_cmd + ["-r"] + targets
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            # Parse results
            try:
                data = json.loads(result.stdout)
                metrics = data.get("metrics", {})
                issues = data.get("results", [])
                
                # Calculate files scanned
                if file_list:
                    total_files = len(file_list)
                else:
                    total_files = sum(m.get("loc", 0) for m in metrics.values()) if metrics else 0
                
                # Format issues for report
                formatted_issues = []
                for issue in issues[:20]:  # Limit to 20
                    formatted_issues.append({
                        "file": issue.get("filename", ""),
                        "line": issue.get("line_number", 0),
                        "severity": issue.get("issue_severity", "UNKNOWN"),
                        "confidence": issue.get("issue_confidence", "UNKNOWN"),
                        "type": issue.get("test_id", ""),
                        "description": issue.get("issue_text", "")
                    })
                
                return {
                    "tool": "bandit",
                    "status": "issues_found" if issues else "clean",
                    "files_scanned": total_files,
                    "total_issues": len(issues),
                    "issues": formatted_issues,
                    "code_security": {
                        "files_scanned": total_files,
                        "issues": formatted_issues
                    }
                }
            except json.JSONDecodeError:
                logger.warning(f"Bandit JSON decode error: {result.stdout[:200]}")
                return {
                    "status": "error", 
                    "error": "Bandit output parse failed", 
                    "raw_sample": result.stdout[:200] or result.stderr[:200],
                    "code_security": {"files_scanned": 0, "issues": []}
                }

        except subprocess.TimeoutExpired:
            logger.error("Bandit scan timed out (>300s)")
            return {
                "status": "error", 
                "error": "TIMEOUT: Bandit scan took too long (>300s).",
                "code_security": {"files_scanned": 0, "issues": []}
            }
        except FileNotFoundError:
            logger.warning("Bandit not installed")
            return {
                "status": "skipped",
                "error": "Bandit not installed. Run: pip install bandit",
                "code_security": {"files_scanned": 0, "issues": []}
            }
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return {
                "error": str(e), 
                "status": "error",
                "code_security": {"files_scanned": 0, "issues": []}
            }
