"""Security analysis using Bandit and pip-audit."""
from pathlib import Path
from typing import Dict, Any, List
from app.core.base_tool import BaseTool
from app.core.subprocess_wrapper import SubprocessWrapper
from app.core.config import get_analysis_excludes_comma, get_analysis_excludes_regex
import logging
import json
import subprocess
import sys

logger = logging.getLogger(__name__)


class SecurityTool(BaseTool):
    """Comprehensive security analysis using multiple tools."""
    
    @property
    def description(self) -> str:
        return "Security analysis using Bandit (code), pip-audit (dependencies), and detect-secrets"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Perform comprehensive security analysis.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with security findings
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            # Run Bandit for code security issues
            bandit_results = self._run_bandit(project_path)
            
            # Run pip-audit for dependency vulnerabilities
            dependency_results = self._run_pip_audit(project_path)
            
            # Run detect-secrets for credential detection
            secrets_results = self._run_detect_secrets(project_path)
            
            # Aggregate results
            total_issues = (
                len(bandit_results.get('issues', [])) +
                len(dependency_results.get('vulnerabilities', [])) +
                len(secrets_results.get('secrets', []))
            )
            
            # Calculate severity counts
            severity_counts = self._count_severities(bandit_results, dependency_results)
            
            return {
                "code_security": bandit_results,
                "dependency_security": dependency_results,
                "secrets": secrets_results,
                "total_issues": total_issues,
                "severity_counts": severity_counts,
                "tools_used": ["bandit", "pip-audit", "detect-secrets"]
            }
        
        except Exception as e:
            logger.error(f"Security analysis failed: {e}")
            return {"error": str(e)}
    
    def _run_bandit(self, project_path: Path) -> Dict[str, Any]:
        """Run Bandit for code security analysis."""
        try:
            # Use centralized exclusion config
            excludes = get_analysis_excludes_comma()
            result = subprocess.run(
                [sys.executable, '-m', 'bandit', '-r', str(project_path), '-f', 'json', '--exclude', excludes, '-ll', '--quiet'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=600,
                errors='replace'
            )
            
            # Allow exit code 0 (clean) and 1 (issues found)
            if result.returncode not in [0, 1]:
                if "not found" in result.stderr.lower():
                    logger.warning("Bandit not installed")
                    return {"issues": [], "skipped": True, "message": "Bandit not installed"}
                logger.error(f"Bandit failed with code {result.returncode}: {result.stderr}")
                return {"issues": [], "error": result.stderr}
            
            stdout = result.stdout
            
        except subprocess.TimeoutExpired:
            logger.error("Bandit timed out")
            return {"issues": [], "error": "Bandit timed out"}
        except FileNotFoundError:
            logger.warning("Bandit command not found")
            return {"issues": [], "skipped": True, "message": "Bandit not installed"}
        
        try:
            data = json.loads(stdout)
            issues = []
            
            for result in data.get('results', []):
                issues.append({
                    "file": result.get('filename', ''),
                    "line": result.get('line_number', 0),
                    "severity": result.get('issue_severity', 'UNKNOWN'),
                    "confidence": result.get('issue_confidence', 'UNKNOWN'),
                    "issue": result.get('issue_text', ''),
                    "cwe": result.get('issue_cwe', {}).get('id', 'N/A')
                })
            
            return {
                "issues": issues,
                "total_issues": len(issues),
                "skipped": False
            }
        
        except json.JSONDecodeError:
            logger.error("Failed to parse Bandit output")
            return {"issues": [], "error": "Failed to parse output"}
    
    def _run_pip_audit(self, project_path: Path) -> Dict[str, Any]:
        """Run pip-audit for dependency vulnerability scanning."""
        # Check for requirements.txt
        requirements_file = project_path / "requirements.txt"
        if not requirements_file.exists():
            logger.info("No requirements.txt found, skipping pip-audit")
            return {
                "vulnerabilities": [],
                "skipped": True,
                "message": "No requirements.txt found"
            }
        
        try:
            result = subprocess.run(
                ['pip-audit', '-r', str(requirements_file), '--format', 'json'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300,
                errors='replace'
            )
            
            # Allow exit code 0 (clean) and 1 (issues found)
            if result.returncode not in [0, 1]:
                if "not found" in result.stderr.lower():
                    logger.warning("pip-audit not installed")
                    return {
                        "vulnerabilities": [],
                        "skipped": True,
                        "message": "pip-audit not installed"
                    }
                logger.error(f"pip-audit failed with code {result.returncode}: {result.stderr}")
                # Try to parse output anyway if it matches JSON
            
            stdout = result.stdout
            
        except subprocess.TimeoutExpired:
            logger.error("pip-audit timed out")
            return {"vulnerabilities": [], "error": "pip-audit timed out"}
        except FileNotFoundError:
            return {
                "vulnerabilities": [],
                "skipped": True,
                "message": "pip-audit not installed"
            }
        
        try:
            data = json.loads(stdout) if stdout else {"dependencies": []}
            vulnerabilities = []
            
            for dep in data.get('dependencies', []):
                for vuln in dep.get('vulns', []):
                    vulnerabilities.append({
                        "package": dep.get('name', 'unknown'),
                        "version": dep.get('version', 'unknown'),
                        "vulnerability_id": vuln.get('id', 'N/A'),
                        "description": vuln.get('description', ''),
                        "fix_versions": vuln.get('fix_versions', [])
                    })
            
            return {
                "vulnerabilities": vulnerabilities,
                "total_vulnerabilities": len(vulnerabilities),
                "skipped": False
            }
        
        except json.JSONDecodeError:
            logger.error("Failed to parse pip-audit output")
            return {"vulnerabilities": [], "error": "Failed to parse output"}
    
    def _run_detect_secrets(self, project_path: Path) -> Dict[str, Any]:
        """Run detect-secrets for credential detection."""
        # Use centralized exclusion config
        exclude_patterns = get_analysis_excludes_regex()
        
        cmd = ['detect-secrets', 'scan', '--all-files']
        for pattern in exclude_patterns:
            cmd.extend(['--exclude-files', pattern])
        cmd.append(str(project_path))
        
        success, stdout, stderr = SubprocessWrapper.run_command(
            cmd,
            cwd=project_path,
            timeout=300,
            check_venv=False
        )
        
        if not success:
            if "not found" in stderr.lower():
                return {"secrets": [], "skipped": True, "message": "detect-secrets not installed"}
            logger.error(f"detect-secrets failed: {stderr}")
            return {"secrets": [], "error": stderr}
        
        try:
            data = json.loads(stdout)
            secrets = []
            
            for file_path, findings in data.get('results', {}).items():
                for finding in findings:
                    secrets.append({
                        "file": file_path,
                        "line": finding.get('line_number', 0),
                        "type": finding.get('type', 'Unknown')
                    })
            
            return {
                "secrets": secrets,
                "total_secrets": len(secrets),
                "skipped": False
            }
        
        except json.JSONDecodeError:
            logger.error("Failed to parse detect-secrets output")
            return {"secrets": [], "error": "Failed to parse output"}
    
    def _count_severities(
        self,
        bandit_results: Dict[str, Any],
        dependency_results: Dict[str, Any]
    ) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        # Count Bandit severities
        for issue in bandit_results.get('issues', []):
            severity = issue.get('severity', 'UNKNOWN')
            if severity in counts:
                counts[severity] += 1
        
        # All dependency vulnerabilities are considered HIGH
        counts["HIGH"] += len(dependency_results.get('vulnerabilities', []))
        
        return counts
