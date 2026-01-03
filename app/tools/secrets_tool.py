"""Secrets detection tool using detect-secrets."""
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import json
from app.core.base_tool import BaseTool
import logging

logger = logging.getLogger(__name__)


class SecretsTool(BaseTool):
    """Detect potential secrets in code using detect-secrets."""
    
    @property
    def description(self) -> str:
        return "Detects potential secrets and credentials using detect-secrets library"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Analyze project for secrets.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with detected secrets
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            secrets = self._run_detect_secrets(project_path)
            
            return {
                "secrets": secrets,
                "total_secrets": len(secrets),
                "files_with_secrets": len(set(s['file'] for s in secrets))
            }
        except Exception as e:
            logger.error(f"Secrets detection failed: {e}")
            return {"error": str(e), "secrets": [], "total_secrets": 0}
    
    def _run_detect_secrets(self, project_path: Path) -> List[Dict[str, Any]]:
        """Run detect-secrets scan."""
        secrets = []
        
        try:
            # Run detect-secrets scan
            result = subprocess.run(
                ['detect-secrets', 'scan', '--all-files', str(project_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=project_path
            )
            
            if result.returncode == 0:
                # Parse JSON output
                try:
                    data = json.loads(result.stdout)
                    
                    # Extract secrets from results
                    if 'results' in data:
                        for file_path, findings in data['results'].items():
                            for finding in findings:
                                secrets.append({
                                    "file": file_path,
                                    "line": finding.get('line_number', 0),
                                    "type": finding.get('type', 'Unknown'),
                                    "hashed_secret": finding.get('hashed_secret', '')[:16] + '...'
                                })
                except json.JSONDecodeError:
                    logger.warning("Failed to parse detect-secrets output")
            else:
                logger.warning(f"detect-secrets exited with code {result.returncode}")
        
        except subprocess.TimeoutExpired:
            logger.error("detect-secrets scan timed out")
        except FileNotFoundError:
            logger.warning("detect-secrets not installed - skipping secrets scan")
        except Exception as e:
            logger.error(f"Error running detect-secrets: {e}")
        
        return secrets
