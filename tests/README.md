# Test Suite Documentation

Comprehensive test coverage for the MCP Python Auditor project.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_scoring.py      # Scoring algorithm tests
│   └── test_dependencies.py # Dependency checking tests
├── integration/             # Integration tests
│   └── test_tools_integration.py  # Tool interaction tests
├── e2e/                     # End-to-end tests
│   └── test_audit_workflows.py    # Complete workflow tests
├── tools/                   # Individual tool tests
│   └── test_individual_tools.py   # Tests for all 12 tools
└── mcp/                     # MCP server tests
    └── test_mcp_server.py   # MCP integration tests
```

## Running Tests

### Using the Test Runner

```bash
# Run all tests
python run_tests.py all

# Run specific test category
python run_tests.py unit
python run_tests.py integration
python run_tests.py e2e
python run_tests.py tools
python run_tests.py mcp

# Run with coverage report
python run_tests.py coverage

# Quick tests (unit + tools, stop on first failure)
python run_tests.py quick
```

### Using Pytest Directly

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_scoring.py -v

# Run tests matching a pattern
pytest tests/ -k "scoring" -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test class
pytest tests/unit/test_scoring.py::TestScoringAlgorithm -v

# Run specific test method
pytest tests/unit/test_scoring.py::TestScoringAlgorithm::test_perfect_score -v
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)

Test individual components in isolation.

**test_scoring.py:**
- ✅ Perfect score calculation (100/100)
- ✅ Low coverage penalty (-40 for <20%)
- ✅ Duplicates penalty (capped at -15)
- ✅ Realistic project score (9% + 78 dupes = 45/100)
- ✅ Security penalties
- ✅ Secrets penalties

**test_dependencies.py:**
- ✅ All tools installed detection
- ✅ Missing tools detection
- ✅ Installation success/failure handling
- ✅ Installation timeout handling

### 2. Integration Tests (`tests/integration/`)

Test interactions between multiple components.

**test_tools_integration.py:**
- ✅ Structure + Architecture integration
- ✅ Tests + Coverage integration
- ✅ Dead code detection workflow
- ✅ Full audit workflow (all 12 tools)
- ✅ Report generation with real data
- ✅ Realistic score display in reports

### 3. E2E Tests (`tests/e2e/`)

Test complete user workflows from start to finish.

**test_audit_workflows.py:**
- ✅ Complete audit cycle (request → tools → report → save)
- ✅ Dry run to execution flow (auto-fix safety)
- ✅ Missing dependencies → install → retry workflow
- ✅ Report accessibility (generate → save → read)
- ✅ New user first audit journey
- ✅ Developer iterative improvement journey

### 4. Tool Tests (`tests/tools/`)

Test each of the 12 analysis tools individually.

**test_individual_tools.py:**
- ✅ Bandit (security scanner)
- ✅ Detect-secrets (credential detection)
- ✅ Ruff (linter)
- ✅ Structure analyzer
- ✅ Vulture (dead code)
- ✅ Radon (complexity)
- ✅ Duplication detector
- ✅ Cleanup scanner
- ✅ Git info analyzer
- ✅ Architecture visualizer
- ✅ Pytest coverage
- ✅ Pip-audit (vulnerabilities)
- ✅ Error handling (invalid paths, timeouts, missing tools)

### 5. MCP Tests (`tests/mcp/`)

Test MCP server integration and tool exposure.

**test_mcp_server.py:**
- ✅ MCP tool registration
- ✅ start_full_audit tool
- ✅ check_audit_status tool
- ✅ install_dependencies tool
- ✅ run_auto_fix tool
- ✅ Missing dependencies response
- ✅ Auto-fix dry run response
- ✅ Job status tracking
- ✅ Report format (markdown)
- ✅ Actionable insights in reports
- ✅ Error handling (invalid paths, malformed JSON)

## Test Coverage Goals

- **Unit Tests:** >90% coverage
- **Integration Tests:** >80% coverage
- **E2E Tests:** Critical paths covered
- **Overall:** >85% code coverage

## Current Coverage

Run `python run_tests.py coverage` to generate HTML coverage report:
```
htmlcov/index.html
```

## Writing New Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Unit Test

```python
def test_new_feature():
    """Test description."""
    # Arrange
    input_data = {...}
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected
```

### Example Integration Test

```python
def test_component_interaction():
    """Test two components working together."""
    component_a_result = run_component_a()
    component_b_result = run_component_b(component_a_result)
    
    assert component_b_result["status"] == "success"
```

### Example E2E Test

```python
def test_user_workflow():
    """Test complete user journey."""
    # Simulate user actions
    step1_result = user_action_1()
    step2_result = user_action_2(step1_result)
    step3_result = user_action_3(step2_result)
    
    # Verify end state
    assert step3_result["final_state"] == "expected"
```

## Continuous Integration

Tests are run automatically on:
- Every commit (quick tests)
- Pull requests (all tests + coverage)
- Releases (all tests + coverage + E2E)

## Troubleshooting

### Tests Failing Due to Missing Tools

```bash
# Install all audit dependencies
pip install bandit detect-secrets vulture radon ruff pip-audit pytest pytest-cov

# Verify installation
python verify_tools.py
```

### Import Errors

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Ensure you're in the project root
cd /path/to/mcp-python-auditor
```

### Coverage Report Not Generating

```bash
# Install coverage dependencies
pip install pytest-cov

# Run with explicit coverage
pytest tests/ --cov=. --cov-report=html
```

## Best Practices

1. **Test Isolation:** Each test should be independent
2. **Clear Names:** Test names should describe what they test
3. **Arrange-Act-Assert:** Follow AAA pattern
4. **Mock External Calls:** Use mocks for network/filesystem
5. **Fast Tests:** Unit tests should run in milliseconds
6. **Realistic Data:** Use real-world scenarios in tests

## Test Markers

Mark tests for selective execution:

```python
@pytest.mark.slow
def test_long_running_operation():
    pass

# Run: pytest -m "not slow"
```

---

**Last Updated:** January 2026  
**Test Count:** 50+ tests across 5 categories  
**Coverage Target:** 85%+
