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
from app.core.scoring_engine import ScoringEngine, ScoreBreakdown
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

        Handles multiple formats:
        - execution_time_ms: milliseconds (from JSON-first architecture)
        - duration_s: seconds (from parallel audit)
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
        Generate an audit report using Jinja2 template rendering with pre-calculated scores.
        
        Args:
            report_id: Unique report identifier
            project_path: Path to the project being audited
            score: Overall audit score (0-100) - DEPRECATED, will be calculated
            tool_results: Raw results from all audit tools
            timestamp: Report generation timestamp
            scanned_files: Optional list of files that were scanned
            
        Returns:
            Path to the generated report file
        """
        try:
            # Step 1: Calculate scores using deterministic engine (NOT LLM!)
            logger.info("Calculating scores using ScoringEngine...")
            score_breakdown = ScoringEngine.calculate_score(tool_results)
            logger.info(f"Score calculated: {score_breakdown.final_score}/100 ({score_breakdown.grade})")
            
            # Step 2: Build normalized context
            logger.info("Building normalized report context...")
            
            # Extract duration from tool_results if available
            duration = tool_results.get('duration_seconds') or tool_results.get('duration')
            if isinstance(duration, str):
                # Try to parse string duration (e.g., "12.34s")
                try:
                    duration = float(duration.rstrip('s'))
                except (ValueError, AttributeError):
                    duration = None

            # If no duration at root, calculate from individual tool execution times
            if duration is None:
                duration = self._calculate_total_duration(tool_results)
            
            context = build_report_context(
                raw_results=tool_results,
                project_path=project_path,
                score=score_breakdown.final_score,  # Use calculated score
                report_id=report_id,
                timestamp=timestamp,
                duration=duration  # ADDED: pass duration parameter
            )
            
            
            # Debug logging to identify data structure issues
            logger.debug(f"tool_results keys: {list(tool_results.keys())}")
            if 'tests' in tool_results:
                logger.debug(f"tests type: {type(tool_results.get('tests'))}")
            
            # Safe extraction with type validation
            tests_data = tool_results.get("tests", {})
            if isinstance(tests_data, dict):
                coverage = tests_data.get("coverage_percent", 0)
            else:
                coverage = 0
                logger.warning(f"Tests data is not a dict: {type(tests_data)}")

            bandit_data = tool_results.get("bandit", {})
            if isinstance(bandit_data, dict):
                bandit_issues = bandit_data.get("total_issues", 0)
            else:
                bandit_issues = 0
                logger.warning(f"Bandit data is not a dict: {type(bandit_data)}")

            secrets_data = tool_results.get("secrets", {})
            if isinstance(secrets_data, dict):
                secrets_count = secrets_data.get("total_secrets", 0)
            else:
                secrets_count = 0
                logger.warning(f"Secrets data is not a dict: {type(secrets_data)}")

            # Pre-classified severities (prevent hallucination)
            context.update({
                # Calculated scores - these WON'T change!
                "score": score_breakdown.final_score,
                "grade": score_breakdown.grade,
                "security_penalty": score_breakdown.security_penalty,
                "quality_penalty": score_breakdown.quality_penalty,
                "testing_penalty": score_breakdown.testing_penalty,
                
                "coverage_severity": _get_coverage_severity(coverage),
                "security_severity": _get_security_severity(bandit_issues, secrets_count),
                
                # Template-specific fields
                "repo_name": Path(project_path).resolve().name,
                "repo_name": Path(project_path).resolve().name,
                # "duration": "PRESERVED_FROM_CONTEXT", # Don't overwrite correct duration from build_report_context
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                
                # Raw results for template access
                "raw_results": tool_results,
            })
            
            # Step 4: Load template
            logger.info("Loading Jinja2 template...")
            template = self.env.get_template('audit_report_v3.md.j2')  # Use new template
            
            # Step 5: Render report
            logger.info("Rendering report...")
            report_content = template.render(**context)
            
            # Step 6: Validation
            validator = ReportValidator()
            errors = validator.validate_consistency(tool_results, report_content, score_breakdown)
            if errors:
                logger.warning(f"⚠️ Report inconsistencies detected: {errors}")
                # Append warning to report
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
