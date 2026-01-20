# 🚀 Quick Reference Guide - Improved Reporting System

## For Developers

### Using the ScoringEngine

```python
from app.core.scoring_engine import ScoringEngine

# Your audit results from MCP tools
audit_results = {
    "bandit": {"total_issues": 5},
    "secrets": {"total_secrets": 2},
    "tests": {"coverage_percent": 45.5},
    "dead_code": {"total_dead": 10},
    "duplication": {"duplicates": [...]}
}

# Calculate score (deterministic, no LLM)
breakdown = ScoringEngine.calculate_score(audit_results)

# Access results
print(f"Final Score: {breakdown.final_score}/100")
print(f"Grade: {breakdown.grade}")
print(f"Security Penalty: {breakdown.security_penalty}")
print(f"Testing Penalty: {breakdown.testing_penalty}")
print(f"Quality Penalty: {breakdown.quality_penalty}")
```

### Using the ReportValidator

```python
from app.core.report_validator import ReportValidator
from app.core.scoring_engine import ScoreBreakdown

validator = ReportValidator()

# Validate report consistency
errors = validator.validate_consistency(
    json_data=audit_results,
    markdown_report=report_content,
    score_breakdown=breakdown
)

if errors:
    print("⚠️ Inconsistencies found:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✅ Report is consistent")
```

### Generating Reports

```python
from app.core.report_generator_v2 import ReportGeneratorV2
from pathlib import Path
from datetime import datetime

# Initialize generator
generator = ReportGeneratorV2(reports_dir=Path("./reports"))

# Generate report (score is calculated automatically)
report_path = generator.generate_report(
    report_id="audit_20260120",
    project_path="/path/to/project",
    score=0,  # Ignored - calculated automatically
    tool_results=audit_results,
    timestamp=datetime.now(),
    scanned_files=["file1.py", "file2.py"]  # Optional
)

print(f"Report generated: {report_path}")
```

## Scoring Algorithm Quick Reference

### Security Penalties
| Issue Type | Formula | Max Penalty |
|------------|---------|-------------|
| Bandit Issues | `count × 5` | 30 |
| Secrets | `count × 10` | 40 |

### Testing Penalties
| Coverage Range | Penalty | Severity |
|----------------|---------|----------|
| 0% | 50 | ❌ Critical |
| < 10% | 40 | ❌ Critical |
| < 30% | 30 | 🔴 Very Low |
| < 50% | 20 | 🟡 Low |
| < 70% | 10 | 🟢 Moderate |
| ≥ 70% | 0 | ✅ Good |

### Quality Penalties
| Issue Type | Formula | Max Penalty |
|------------|---------|-------------|
| Dead Code | `count × 2` | 20 |
| Duplication | `(exact_dups - 10)` | 15 |

*Note: Duplication only counts items with >95% similarity*

### Grade Boundaries
| Score Range | Grade |
|-------------|-------|
| 95-100 | A+ |
| 90-94 | A |
| 80-89 | B |
| 70-79 | C |
| 60-69 | D |
| 0-59 | F |

## Common Use Cases

### 1. Calculate Score Only
```python
from app.core.scoring_engine import ScoringEngine

score = ScoringEngine.calculate_score(audit_results)
print(f"{score.final_score}/100 ({score.grade})")
```

### 2. Get Coverage Severity
```python
from app.core.report_generator_v2 import _get_coverage_severity

severity = _get_coverage_severity(45.5)
print(severity["label"])  # "🟡 Low"
print(severity["recommendation"])  # "Aim for 70%+ coverage"
```

### 3. Get Security Severity
```python
from app.core.report_generator_v2 import _get_security_severity

severity = _get_security_severity(
    bandit_issues=5,
    secrets=2
)
print(severity["label"])  # "🟠 Moderate" or similar
print(severity["count"])  # Total weighted count
```

### 4. Validate Existing Report
```python
from app.core.report_validator import ReportValidator
from app.core.scoring_engine import ScoringEngine

# Calculate expected score
breakdown = ScoringEngine.calculate_score(audit_results)

# Read existing report
with open("report.md", "r") as f:
    report = f.read()

# Validate
validator = ReportValidator()
errors = validator.validate_consistency(audit_results, report, breakdown)

if not errors:
    print("✅ Report is accurate")
```

## Testing

### Run All New Tests
```bash
pytest tests/test_scoring_engine.py tests/test_report_validator.py -v
```

### Run Specific Test Suite
```bash
# Scoring engine tests only
pytest tests/test_scoring_engine.py -v

# Validator tests only
pytest tests/test_report_validator.py -v
```

### Run Single Test
```bash
pytest tests/test_scoring_engine.py::TestScoringEngine::test_perfect_score -v
```

### Check Test Coverage
```bash
pytest tests/test_scoring_engine.py tests/test_report_validator.py --cov=app.core --cov-report=term-missing
```

## Troubleshooting

### Issue: Score doesn't match expected value

**Check**:
1. Verify input data structure matches expected format
2. Check penalty caps (security: 30+40, quality: 20+15, testing: 50)
3. Run unit tests to ensure algorithm is correct

```python
# Debug score calculation
breakdown = ScoringEngine.calculate_score(audit_results)
print(f"Base: {breakdown.base_score}")
print(f"Security: -{breakdown.security_penalty}")
print(f"Testing: -{breakdown.testing_penalty}")
print(f"Quality: -{breakdown.quality_penalty}")
print(f"Final: {breakdown.final_score}")
```

### Issue: Validation errors in report

**Check**:
1. Ensure template uses exact values from context
2. Check for markdown formatting issues
3. Verify regex patterns in validator

```python
# Test extraction
from app.core.report_validator import ReportValidator

validator = ReportValidator()
print(validator._extract_score("Overall Score: 85/100"))
print(validator._extract_coverage("Coverage: 45.5%"))
```

### Issue: Import errors

**Check**:
1. Ensure all files are in correct locations
2. Verify Python version (3.9+)
3. Check for circular imports

```bash
# Test imports
python -c "from app.core.scoring_engine import ScoringEngine; print('✅ OK')"
python -c "from app.core.report_validator import ReportValidator; print('✅ OK')"
```

## Best Practices

### ✅ DO
- Always use `ScoringEngine.calculate_score()` for score calculation
- Validate reports after generation
- Use pre-calculated severity classifications
- Write tests for custom validators
- Document any algorithm changes

### ❌ DON'T
- Don't calculate scores manually
- Don't modify scores in templates
- Don't use LLM for numeric calculations
- Don't skip validation
- Don't hardcode penalty values

## Migration Checklist

If migrating from old reporting system:

- [ ] Import new modules
- [ ] Replace manual score calculation with `ScoringEngine`
- [ ] Add severity classifications
- [ ] Add report validation
- [ ] Update templates to use pre-calculated values
- [ ] Run tests to verify accuracy
- [ ] Update documentation

## Support

For questions or issues:
1. Check `docs/IMPROVED_REPORTING_SYSTEM.md` for detailed architecture
2. Review unit tests for usage examples
3. Run validation to identify specific issues
4. Check logs for detailed error messages

---

**Quick Test**:
```bash
python -c "from app.core.scoring_engine import ScoringEngine; print('✅ System ready')"
pytest tests/test_scoring_engine.py tests/test_report_validator.py -q
```

Expected: ✅ System ready + 39 passed
