# 🔍 Python Audit Report

**Generated**: 2026-01-22 10:29:00  
**Repository**: mcp-python-auditor  
**Duration**: 65.45s

---

## 📊 Overall Score: 40/100 (F)

### Score Breakdown
| Component | Penalty | Details |
|-----------|---------|---------|
| 🔒 Security | -30 | 1 issues, 0 secrets |
| ✅ Testing | -30 | 10% coverage |
| 🧹 Quality | -0 | 0 dead code items |
| **Final** | **40** | Grade: F |

---

## 🔒 Security Analysis

**Status**: 🔴 Critical  
**Issues Found**: 1  
**Secrets Detected**: 0

### 🛡️ Security Issues

- **MEDIUM**: Test issue (`:10`)



---

## 🧪 Test Coverage

**Coverage**: 10%  
**Assessment**: 🔴 Very Low  
**Status**: Insufficient test coverage (10%)

**Recommendation**: Add tests for critical paths

**Test Breakdown**:
- Unit Tests: 1
- Integration Tests: 1
- E2E Tests: 0

⚠️ **Warning**: ⚠️ Test files found but no tests executed.


---

## 📂 Project Structure

**Python Files**: 67  
**Total Lines**: 13900  
**Top Directories**: app, docs

### Directory Tree
```
...
```

---

## 🧹 Code Quality

### Linting Issues
0 issues found

✅ No linting issues detected

### Dead Code
0 items found

✅ No dead code detected

### Code Duplication
0 similar code blocks found

✅ No significant code duplication detected

---

## 📊 Detailed Findings

### Architecture Overview
Architecture analysis not available

### Efficiency Analysis
✅ No high-complexity functions detected (all under threshold)

### Cleanup Recommendations
**Cleanup Available**: 10.9MB

**Targets**:
- __pycache__: 122 directories
- .pytest_cache: 1 directories
- .ruff_cache: 1 directories

**Items**:
- file1
- file2

---

## 💡 Recommendations

**Based on the calculated score of 40/100:**

1. **🔴 CRITICAL - Test Coverage**: Add tests for critical paths

2. **🔴 CRITICAL - Security**: Address 1 security findings immediately


4. **Overall**: Current grade (F) indicates significant technical debt. Prioritize above items.

---

## 🔧 Tools Executed

- **📁 Structure**: ℹ️ Info (0.00s)
- **🏗️ Architecture**: ⚠️ Skip (0.00s)
- **📝 Type Coverage**: ⚠️ Skip (0.00s)
- **🧮 Complexity**: ⚠️ Skip (0.00s)
- **🎭 Duplication**: ⚠️ Skip (0.00s)
- **☠️ Dead Code**: ⚠️ Skip (0.00s)
- **⚡ Efficiency**: ⚠️ Skip (0.00s)
- **🧹 Cleanup**: ℹ️ Info (0.00s)
- **🔒 Security (Bandit)**: ⚠️ Issues (0.00s)
- **🔐 Secrets**: ✅ Pass (0.00s)
- **🧹 Code Quality (Ruff)**: ✅ Pass (0.00s)
- **✅ Tests**: ℹ️ Info (0.00s)
- **📋 Gitignore**: ⚠️ Skip (0.00s)
- **📝 Git Status**: ℹ️ Info (0.00s)

---

*This report uses pre-calculated scores based on the algorithm in README.md. All numeric values are deterministic and not subject to interpretation.*

## 🛡️ Report Integrity Check
**Status:** ✅ Complete

---

## ⚠️ Report Validation Warnings

- Security count mismatch: JSON=32, Report=1
