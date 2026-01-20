"""Fast comprehensive audit tool using Ruff.

This tool replaces multiple slow tools (Bandit, Radon, Isort) with a single
blazing-fast Ruff integration that provides:
- Security checks (Bandit rules)
- Complexity analysis (McCabe)
- Code quality (Pyflakes, pycodestyle, etc.)
- Import sorting
- Performance anti-patterns

Execution time: ~1-2 seconds vs 10+ minutes for old tools.
"""
from pathlib import Path
from typing import Dict, Any, List
import subprocess
import json
import logging
import sys

from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class FastAuditTool(BaseTool):
    """Comprehensive code audit using Ruff (replaces Bandit, Radon, Isort)."""
    
    @property
    def description(self) -> str:
        return "Fast comprehensive audit using Ruff (security, complexity, quality)"
    
    def analyze(self, project_path: Path) -> Dict[str, Any]:
        """
        Run comprehensive Ruff audit.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with categorized findings
        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}
        
        try:
            logger.info("FastAudit: Running Ruff comprehensive check...")
            
            # Run ruff check with JSON output
            cmd = [
                sys.executable, '-m', 'ruff', 'check',
                str(project_path),
                '--output-format', 'json',
                '--exit-zero'  # Don't fail on findings
            ]
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute max
            )
            
            if result.returncode != 0 and result.returncode != 1:
                # returncode 1 means findings were found (expected)
                # returncode 0 means no findings
                # anything else is an error
                logger.error(f"Ruff failed with code {result.returncode}: {result.stderr}")
                return {"error": f"Ruff execution failed: {result.stderr}"}
            
            # Parse JSON output
            if not result.stdout.strip():
                logger.info("FastAudit: No issues found!")
                return self._empty_result()
            
            try:
                findings = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Ruff output: {e}")
                return {"error": f"Failed to parse Ruff output: {e}"}
            
            # Categorize findings
            categorized = self._categorize_findings(findings)
            
            logger.info(f"FastAudit: Found {len(findings)} total issues")
            logger.info(f"  - Security: {len(categorized['security'])}")
            logger.info(f"  - Complexity: {len(categorized['complexity'])}")
            logger.info(f"  - Quality: {len(categorized['quality'])}")
            logger.info(f"  - Style: {len(categorized['style'])}")
            
            return categorized
            
        except subprocess.TimeoutExpired:
            logger.error("Ruff execution timed out after 60 seconds")
            return {"error": "Ruff execution timed out"}
        except Exception as e:
            logger.error(f"FastAudit failed: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _categorize_findings(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Categorize Ruff findings into security, complexity, quality, etc.
        
        Args:
            findings: List of Ruff findings
            
        Returns:
            Categorized findings dictionary
        """
        security = []
        complexity = []
        quality = []
        style = []
        imports = []
        performance = []
        
        for finding in findings:
            code = finding.get('code', '')
            
            # Categorize by rule code prefix
            if code.startswith('S'):
                # Security (Bandit rules)
                security.append(self._format_finding(finding, 'security'))
            elif code.startswith('C90'):
                # Complexity (McCabe)
                complexity.append(self._format_finding(finding, 'complexity'))
            elif code.startswith(('I', 'TID')):
                # Import sorting and organization
                imports.append(self._format_finding(finding, 'imports'))
            elif code.startswith(('PERF', 'UP')):
                # Performance and upgrades
                performance.append(self._format_finding(finding, 'performance'))
            elif code.startswith(('E', 'W', 'F', 'B', 'SIM', 'RUF')):
                # Code quality (Pyflakes, pycodestyle, bugbear, simplify)
                quality.append(self._format_finding(finding, 'quality'))
            else:
                # Style and other
                style.append(self._format_finding(finding, 'style'))
        
        # Calculate statistics
        total_issues = len(findings)
        files_with_issues = len(set(f.get('filename', '') for f in findings))
        
        return {
            'tool': 'ruff',
            'status': 'issues_found' if total_issues > 0 else 'clean',
            'total_issues': total_issues,
            'files_with_issues': files_with_issues,
            
            # Categorized findings
            'security': security,
            'complexity': complexity,
            'quality': quality,
            'style': style,
            'imports': imports,
            'performance': performance,
            
            # Statistics by category
            'stats': {
                'security_count': len(security),
                'complexity_count': len(complexity),
                'quality_count': len(quality),
                'style_count': len(style),
                'imports_count': len(imports),
                'performance_count': len(performance),
            },
            
            # Severity breakdown
            'by_severity': self._count_by_severity(findings),
        }
    
    def _format_finding(self, finding: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Format a Ruff finding into our standard structure."""
        location = finding.get('location', {})
        
        return {
            'category': category,
            'code': finding.get('code', 'UNKNOWN'),
            'message': finding.get('message', ''),
            'file': finding.get('filename', ''),
            'line': location.get('row', 0),
            'column': location.get('column', 0),
            'severity': self._map_severity(finding),
            'fix': finding.get('fix'),  # Ruff can suggest fixes
            'url': finding.get('url'),  # Link to rule documentation
        }
    
    def _map_severity(self, finding: Dict[str, Any]) -> str:
        """Map Ruff finding to severity level."""
        code = finding.get('code', '')
        
        # Security issues are high severity
        if code.startswith('S'):
            return 'HIGH'
        
        # Complexity issues are medium
        if code.startswith('C90'):
            return 'MEDIUM'
        
        # Errors are medium
        if code.startswith(('E', 'F')):
            return 'MEDIUM'
        
        # Warnings and style are low
        return 'LOW'
    
    def _count_by_severity(self, findings: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count findings by severity level."""
        from collections import Counter
        severities = [self._map_severity(f) for f in findings]
        return dict(Counter(severities))
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure when no issues found."""
        return {
            'tool': 'ruff',
            'status': 'clean',
            'total_issues': 0,
            'files_with_issues': 0,
            'security': [],
            'complexity': [],
            'quality': [],
            'style': [],
            'imports': [],
            'performance': [],
            'stats': {
                'security_count': 0,
                'complexity_count': 0,
                'quality_count': 0,
                'style_count': 0,
                'imports_count': 0,
                'performance_count': 0,
            },
            'by_severity': {},
        }
