"""Jinja2-based report generator for audit results.

This module replaces manual string concatenation with professional template rendering.
Benefits:
- Eliminates "N/A" bugs through data normalization
- Cleaner separation of data and presentation
- Easier to maintain and extend
- Type-safe context building
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.report_context import build_report_context

logger = logging.getLogger(__name__)


class ReportGeneratorV2:
    """Generate comprehensive markdown reports using Jinja2 templates."""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent.parent / 'templates'
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['round'] = lambda x, decimals=2: round(float(x), decimals) if x else 0
        
        logger.info(f"✅ Jinja2 template engine initialized (templates: {template_dir})")
    
    def generate_report(
        self,
        report_id: str,
        project_path: str,
        score: int,
        tool_results: Dict[str, Any],
        timestamp: datetime,
        scanned_files: List[str] = None
    ) -> str:
        """
        Generate an audit report using Jinja2 template rendering.
        
        Args:
            report_id: Unique report identifier
            project_path: Path to the project being audited
            score: Overall audit score (0-100)
            tool_results: Raw results from all audit tools
            timestamp: Report generation timestamp
            scanned_files: Optional list of files that were scanned
            
        Returns:
            Path to the generated report file
        """
        try:
            # Step 1: Build normalized context
            logger.info("Building normalized report context...")
            context = build_report_context(
                raw_results=tool_results,
                project_path=project_path,
                score=score,
                report_id=report_id,
                timestamp=timestamp
            )
            
            # Step 2: Load template
            logger.info("Loading Jinja2 template...")
            template = self.env.get_template('audit_report.md.j2')
            
            # Step 3: Render report
            logger.info("Rendering report...")
            report_content = template.render(**context)
            
            # Step 4: Write to file
            report_path = self.reports_dir / f"{report_id}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # Step 5: Append integrity validation if scanned_files provided
            if scanned_files:
                self._append_integrity_validation(report_path, scanned_files)
            
            logger.info(f"✅ Report generated successfully: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}", exc_info=True)
            raise
    
    def _append_integrity_validation(self, report_path: Path, scanned_files: List[str]) -> None:
        """Append integrity validation section to the report."""
        try:
            from app.core.audit_validator import validate_report_integrity
            
            # Read the generated report
            with open(report_path, 'r', encoding='utf-8') as f:
                report_text = f.read()
            
            # Generate validation section
            validation_section = validate_report_integrity(report_text, scanned_files)
            
            # Append validation to report
            with open(report_path, 'a', encoding='utf-8') as f:
                f.write("\n\n---\n\n")
                f.write(validation_section)
            
            logger.info(f"✅ Integrity validation appended ({len(scanned_files)} files verified)")
            
        except ImportError:
            logger.warning("⚠️ audit_validator module not found, skipping integrity check")
        except Exception as e:
            logger.error(f"❌ Integrity validation failed: {e}")


# Backward compatibility: Keep old class name as alias
ReportGenerator = ReportGeneratorV2
