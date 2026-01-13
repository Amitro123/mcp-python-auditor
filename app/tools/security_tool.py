"""Security scanning tool using Bandit with Smart Target Discovery."""
import json
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SecurityTool(BaseTool):
    """Scans code for security vulnerabilities using Bandit (Smart Targeting)."""
    
    @property
    def description(self) -> str:
        return "Scans code for security vulnerabilities using Bandit (Smart Targeting)."

    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project for security vulnerabilities using smart target discovery.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with security findings
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path", "status": "error"}
        
        target_path = Path(project_path).resolve()
        
        # --- STRATEGY: Smart Target Discovery ---
        # Instead of letting Bandit walk the whole tree and get stuck in node_modules,
        # we explicitly tell it which source folders to scan.
        
        known_source_dirs = ["src", "app", "scripts", "lib", "core", "backend", "api"]
        scan_targets: List[str] = []
        
        # Check which source folders actually exist
        for folder in known_source_dirs:
            p = target_path / folder
            if p.exists() and p.is_dir():
                scan_targets.append(str(p))
        
        # Prepare command arguments
        exclude_args: List[str] = []
        
        if scan_targets:
            # OPTION A: We found source folders. Scan ONLY them.
            # This is extremely fast because it bypasses root files and node_modules entirely.
            logger.info(f"Smart Scan Targets: {scan_targets}")
            print(f"[BANDIT] Smart Scan Targets: {scan_targets}", file=sys.stderr)
            targets = scan_targets
            # No exclude needed because we are pointing directly to clean folders
        else:
            # OPTION B: No standard folders found. Fallback to scanning root.
            # We must be very aggressive with exclusions here.
            logger.info("No source folders found. Scanning root with strict exclusions.")
            print("[BANDIT] No source folders found. Scanning root with strict exclusions.", file=sys.stderr)
            targets = [str(target_path)]
            exclude_dirs = [
                "node_modules", "external_libs", "venv", ".venv", "env",
                "tests", "test", ".git", "__pycache__", ".idea", ".vscode",
                "dist", "build", "coverage", "site-packages", "htmlcov",
                ".pytest_cache", ".mypy_cache", ".tox"
            ]
            exclude_args = ["-x", ",".join(exclude_dirs)]

        # Construct the Bandit command
        cmd = [
            sys.executable, "-m", "bandit",
            "-r", *targets,
            "-f", "json"
        ] + exclude_args
        
        logger.info(f"Running: {' '.join(cmd)}")

        try:
            # Run with a 300s timeout (5 minutes - Windows IO can be slow)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            try:
                data = json.loads(result.stdout)
                metrics = data.get("metrics", {})
                issues = data.get("results", [])
                
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
                    "scan_targets": targets,
                    "code_security": {
                        "files_scanned": total_files,
                        "issues": formatted_issues
                    }
                }
            except json.JSONDecodeError:
                # Bandit writes to stderr if it crashes, or stdout might be empty
                logger.warning(f"Bandit JSON decode error: {result.stdout[:200]}")
                return {
                    "status": "error", 
                    "error": "Bandit output parse failed", 
                    "raw_sample": result.stdout[:200] or result.stderr[:200],
                    "code_security": {"files_scanned": 0, "issues": []}
                }

        except subprocess.TimeoutExpired:
            logger.error(f"Bandit scan timed out (>60s) on targets: {targets}")
            return {
                "status": "error", 
                "error": "TIMEOUT: Bandit scan took too long (>60s).",
                "debug_targets": str(targets),
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
