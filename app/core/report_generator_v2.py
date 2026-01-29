"""Jinja2-based report generator for audit results.
"""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.report_context import build_report_context
from app.core.scoring_engine import ScoringEngine
from app.core.report_validator import ReportValidator

logger = logging.getLogger(__name__)


def _get_coverage_severity(coverage: float) -> dict:
    """Returns object with severity + structured explanation"""
    if coverage == 0:
        return {
            "level": "critical",
            "label": "❌ Critical",
            "description": "No test coverage detected",
            "recommendation": "Add unit tests immediately"
        }
    elif coverage < 10:
        return {
            "level": "critical", 
            "label": "❌ Critical",
            "description": f"Virtually no test coverage ({coverage}%)",
            "recommendation": "Increase coverage to at least 30%"
        }
    elif coverage < 30:
        return {
            "level": "high",
            "label": "🔴 Very Low", 
            "description": f"Insufficient test coverage ({coverage}%)",
            "recommendation": "Add tests for critical paths"
        }
    elif coverage < 50:
        return {
            "level": "medium",
            "label": "🟡 Low",
            "description": f"Below recommended coverage ({coverage}%)",
            "recommendation": "Aim for 70%+ coverage"
        }
    elif coverage < 70:
        return {
            "level": "low",
            "label": "🟢 Moderate",
            "description": f"Acceptable coverage ({coverage}%)",
            "recommendation": "Continue improving to 80%+"
        }
    else:
        return {
            "level": "info",
            "label": "✅ Good",
            "description": f"Good test coverage ({coverage}%)",
            "recommendation": "Maintain current standards"
        }


def _get_security_severity(bandit_issues: int, secrets: int) -> dict:
    """Returns object with security severity classification"""
    total = bandit_issues + (secrets * 2)  # secrets are more severe
    
    if total == 0:
        return {"level": "info", "label": "✅ Clean", "count": 0}
    elif total <= 3:
        return {"level": "low", "label": "🟡 Minor", "count": total}
    elif total <= 10:
        return {"level": "medium", "label": "🟠 Moderate", "count": total}
    else:
        return {"level": "high", "label": "🔴 Critical", "count": total}


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

    def _calculate_total_duration(self, tool_results: Dict[str, Any]) -> float | None:
        """
        Calculate total duration from individual tool execution times.
        """
        total_ms = 0
        found_any = False

        for key, value in tool_results.items():
            if not isinstance(value, dict):
                continue

            # Check for execution_time_ms (JSON-first format)
            if 'execution_time_ms' in value:
                total_ms += value['execution_time_ms']
                found_any = True
            # Check for duration_s (parallel audit format)
            elif 'duration_s' in value:
                try:
                    duration_s = float(value['duration_s'])
                    total_ms += duration_s * 1000
                    found_any = True
                except (ValueError, TypeError):
                    pass

        if found_any:
            return total_ms / 1000.0  # Convert to seconds
        return None

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
        """
        try:
            # Step 1: Calculate scores using deterministic engine (NOT LLM!)
            logger.info("Calculating scores using ScoringEngine...")
            score_data = ScoringEngine.calculate_score(tool_results)
            final_score = score_data['total_score']
            grade = score_data['grade']
            logger.info(f"Score calculated: {final_score}/100 ({grade})")
            
            # Step 2: Build normalized context
            logger.info("Building normalized report context...")
            
            # Extract duration from tool_results if available
            duration = tool_results.get('duration_seconds') or tool_results.get('duration')
            if isinstance(duration, str):
                try:
                    duration = float(duration.rstrip('s'))
                except (ValueError, AttributeError):
                    duration = None

            context = build_report_context(
                raw_results=tool_results,
                project_path=project_path,
                score=final_score,  # Use calculated score
                report_id=report_id,
                timestamp=timestamp,
                duration=duration
            )
            
            # Add raw results for template access
            context["raw_results"] = tool_results
            
            # VALIDATION STEP
            try:
                from app.core.report_models import TemplateContext
                validated = TemplateContext(**context)
                context = validated.model_dump()
                logger.info("✅ Report context validated successfully against schema")
            except Exception as e:
                logger.error(f"❌ Template validation failed: {e}")
                # Save raw context for debugging
                debug_path = self.reports_dir / f"debug_context_{report_id}.json"
                import json
                with open(debug_path, 'w', encoding='utf-8') as f:
                    json.dump(context, f, indent=2, default=str)
                logger.error(f"Dumped invalid context to {debug_path}")
                raise

            
            # Step 4: Load template
            logger.info("Loading Jinja2 template...")
            template = self.env.get_template('audit_report_v3.md.j2')
            
            # Step 5: Render report
            logger.info("Rendering report...")
            report_content = template.render(**context)
            
            # Step 6: Validation
            validator = ReportValidator()
            errors = validator.validate_consistency(tool_results, report_content, score_data)
            if errors:
                logger.warning(f"⚠️ Report inconsistencies detected: {errors}")
                report_content += "\n\n---\n\n## ⚠️ Report Validation Warnings\n\n"
                for error in errors:
                    report_content += f"- {error}\n"
            else:
                logger.info("✅ Report validation passed - no inconsistencies detected")
            
            # Step 7: Write to file
            report_path = self.reports_dir / f"{report_id}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # Step 8: Append integrity validation if scanned_files provided
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
            
            with open(report_path, 'r', encoding='utf-8') as f:
                report_text = f.read()
            
            validation_section = validate_report_integrity(report_text, scanned_files)
            
            with open(report_path, 'a', encoding='utf-8') as f:
                f.write("\n\n---\n\n")
                f.write(validation_section)
            
            logger.info(f"✅ Integrity validation appended ({len(scanned_files)} files verified)")
            
        except ImportError:
            logger.warning("⚠️ audit_validator module not found, skipping integrity check")
        except Exception as e:
            logger.error(f"❌ Integrity validation failed: {e}")


    def generate_html_report(
        self,
        report_id: str,
        project_path: str,
        score: int,
        tool_results: Dict[str, Any],
        timestamp: datetime,
        scanned_files: List[str] = None
    ) -> str:
        """
        Generate an HTML audit report with styling.
        """
        try:
            import markdown

            # First generate the markdown report
            md_report_path = self.generate_report(
                report_id=report_id,
                project_path=project_path,
                score=score,
                tool_results=tool_results,
                timestamp=timestamp,
                scanned_files=scanned_files
            )

            # Read the markdown content
            with open(md_report_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            # Convert to HTML
            html_body = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'toc']
            )

            # Calculate score for styling
            score_data = ScoringEngine.calculate_score(tool_results)
            score = score_data['total_score']
            grade = score_data['grade']

            # Determine score color
            if score >= 90:
                score_color = "#22c55e"  # green
            elif score >= 70:
                score_color = "#f59e0b"  # amber
            elif score >= 50:
                score_color = "#f97316"  # orange
            else:
                score_color = "#ef4444"  # red

            # Wrap in HTML template
            html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audit Report - {Path(project_path).name}</title>
    <style>
        :root {{
            --primary: #3b82f6;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #1e3a8a, #3b82f6);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .score-badge {{
            background: {score_color};
            color: white;
            font-size: 2.5rem;
            font-weight: bold;
            width: 100px;
            height: 100px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        .grade {{ font-size: 1rem; margin-top: 0.25rem; }}
        .content {{
            background: var(--card-bg);
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{ color: var(--text); margin: 1.5rem 0 1rem; }}
        h1 {{ font-size: 1.75rem; }}
        h2 {{ font-size: 1.5rem; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; }}
        h3 {{ font-size: 1.25rem; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background: var(--bg); font-weight: 600; }}
        tr:hover {{ background: var(--bg); }}
        code {{
            background: var(--bg);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Fira Code', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
        }}
        pre code {{ background: none; color: inherit; }}
        ul, ol {{ margin: 1rem 0; padding-left: 2rem; }}
        li {{ margin: 0.5rem 0; }}
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-top: 2rem;
        }}
        @media (max-width: 768px) {{
            body {{ padding: 1rem; }}
            .header {{ flex-direction: column; text-align: center; gap: 1rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Python Audit Report</h1>
                <p>{Path(project_path).name}</p>
                <p style="opacity: 0.8; font-size: 0.9rem;">{timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
            <div class="score-badge">
                {score}
                <div class="grade">{grade}</div>
            </div>
        </div>
        <div class="content">
            {html_body}
        </div>
        <div class="footer">
            Generated by Python Auditor MCP Server <br>
            <small>Simplification Mode Active</small>
        </div>
    </div>
</body>
</html>'''

            # Write HTML file
            html_path = self.reports_dir / f"{report_id}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"HTML report generated: {html_path}")
            return str(html_path)

        except ImportError:
            logger.warning("markdown package not installed, falling back to markdown-only")
            return self.generate_report(
                report_id, project_path, score, tool_results, timestamp, scanned_files
            )
        except Exception as e:
            logger.error(f"HTML report generation failed: {e}", exc_info=True)
            raise


# Backward compatibility: Keep old class name as alias
ReportGenerator = ReportGeneratorV2
