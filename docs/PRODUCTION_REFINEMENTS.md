"""Updated README with production refinements."""

# See the main README.md for full documentation

## Production Refinements (v2.0)

### Library Integration

Instead of custom AST parsers, we now use industry-standard tools:

- **Vulture** - Dead code detection with confidence scoring
- **Radon** - Cyclomatic complexity and maintainability index
- **Bandit** - AST-based security vulnerability detection  
- **pip-audit** - Dependency vulnerability scanning
- **detect-secrets** - Credential detection

### Configuration Support

Create `audit.yaml` in your project root:

```yaml
audit:
  exclude:
    - "migrations/"
    - "legacy/"
  
  thresholds:
    complexity: 10
    maintainability: 20
    type_coverage: 50
  
  tools:
    deadcode:
      enabled: true
      min_confidence: 80
```

Or use `pyproject.toml`:

```toml
[tool.audit]
exclude = ["migrations/", "legacy/"]

[tool.audit.thresholds]
complexity = 10
maintainability = 20
```

### Safe Subprocess Execution

All external tools run through a safe wrapper:
- Timeout protection (60-120s)
- Graceful fallbacks if tools not installed
- No crashes on missing dependencies
- Clear error messages in reports

### Enhanced Metrics

Reports now include:
- **Maintainability Index** (A-F grade)
- **Type Coverage %** (typed vs untyped functions)
- **Cyclomatic Complexity** per function
- **Security Severity Breakdown** (HIGH/MEDIUM/LOW)

### New Tools

1. **complexity_tool.py** - Radon integration for CC and MI
2. **security_tool.py** - Bandit + pip-audit + detect-secrets
3. **typing_tool.py** - Type hint coverage analysis

### Installation

```bash
pip install -r requirements.txt
```

New dependencies:
- vulture==2.11
- radon==6.0.1
- bandit==1.7.10
- pip-audit==2.7.3
- pyyaml==6.0.2
