"""Secrets detection tool using detect-secrets with Smart Targeting."""
import subprocess
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SecretsTool(BaseTool):
    """Scans for secrets using detect-secrets (Smart Targeted)."""
    
    @property
    def description(self) -> str:
        return "Scans for secrets using detect-secrets (Smart Targeted)."

    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project for secrets using smart target discovery.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with detected secrets
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path", "status": "error"}
        
        target_path = Path(project_path).resolve()
        
        # --- SMART TARGETING (Same as Bandit) ---
        known_source_dirs = ["src", "app", "scripts", "lib", "core", "backend", "api"]
        scan_targets: List[str] = []
        
        for folder in known_source_dirs:
            p = target_path / folder
            if p.exists() and p.is_dir():
                scan_targets.append(str(p))
        
        # Determine paths to scan
        files_to_scan = scan_targets if scan_targets else [str(target_path)]
        
        logger.info(f"Secrets scan targets: {files_to_scan}")
        print(f"[SECRETS] Smart Scan Targets: {files_to_scan}", file=sys.stderr)
        
        # Build command: detect-secrets scan [path1] [path2] ...
        cmd = ["detect-secrets", "scan"] + files_to_scan
        
        # Exclusions (only needed if we fell back to root)
        if not scan_targets:
            cmd.extend([
                "--exclude-files", "node_modules",
                "--exclude-files", "external_libs",
                "--exclude-files", "venv",
                "--exclude-files", ".venv",
                "--exclude-files", "dist",
                "--exclude-files", "build",
                "--exclude-files", "__pycache__",
                "--exclude-files", ".git",
                "--exclude-files", "htmlcov",
                "--exclude-files", ".pytest_cache",
                "--exclude-files", "frontend/test-results",
                "--exclude-files", "playwright-report",
                "--exclude-files", "test-results"
            ])

        try:
            # 300 Seconds Timeout (5 Minutes)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                data = {"results": {}}

            secrets: List[Dict[str, Any]] = []
            
            # Extract and filter results
            for file_path, findings in data.get("results", {}).items():
                # Safety filter - skip unwanted paths
                if any(x in file_path for x in [
                    "node_modules", "external_libs", "tests", 
                    ".min.js", ".map", ".venv", "venv", "__pycache__",
                    "frontend/test-results", "playwright-report"
                ]):
                    continue
                
                for finding in findings:
                    secrets.append({
                        "file": file_path,
                        "line": finding.get('line_number', 0),
                        "type": finding.get('type', 'Unknown'),
                        "hashed_secret": finding.get('hashed_secret', '')[:16] + '...'
                    })

            return {
                "tool": "detect-secrets",
                "status": "issues_found" if secrets else "clean",
                "secrets": secrets,
                "total_secrets": len(secrets),
                "files_with_secrets": len(set(s['file'] for s in secrets)),
                "scan_targets": files_to_scan
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Secrets scan timed out (>300s) on targets: {files_to_scan}")
            return {
                "tool": "detect-secrets",
                "status": "error",
                "error": "Timeout: Secrets scan took too long (>300s).",
                "debug_targets": str(files_to_scan),
                "secrets": [],
                "total_secrets": 0
            }
        except FileNotFoundError:
            logger.warning("detect-secrets not installed")
            return {
                "status": "skipped",
                "error": "detect-secrets not installed. Run: pip install detect-secrets",
                "secrets": [],
                "total_secrets": 0
            }
        except Exception as e:
            logger.error(f"Secrets scan failed: {e}")
            return {
                "error": str(e), 
                "status": "error",
                "secrets": [],
                "total_secrets": 0
            }
