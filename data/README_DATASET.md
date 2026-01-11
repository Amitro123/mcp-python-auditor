# Audit Dataset v2.0 - False Positive Classifier

## 🎯 Purpose

This dataset trains the model to be a **false-positive classifier** for code audit findings, not a generic analysis tool.

The model learns to:
- ✅ Distinguish between REAL ISSUES and FALSE POSITIVES
- ✅ Provide specific verdicts with reasoning
- ✅ Give actionable recommendations only when needed

## 📊 Dataset Statistics

- **Total Examples**: 100
- **Format**: JSONL (one JSON object per line)
- **Distribution**:
  - Security (Bandit): 20 examples (10 real, 10 false positives)
  - Dead Code (Vulture): 20 examples (10 real, 10 false positives)
  - Duplication: 20 examples (10 refactor needed, 10 acceptable)
  - Architecture: 20 examples (15 real issues, 5 acceptable)
  - Test Coverage: 20 examples (varied severity levels)

## 🔄 Changes from v1.0

### ❌ OLD FORMAT (Generic Analysis)
```json
{
  "instruction": "Analyze the architecture of a FastAPI project with no routers/ directory",
  "output": "🏗️ Architecture Issues (1):\n\n🟡 **No routers/ directory in FastAPI app**\n   - Consider organizing endpoints in routers/\n   - Recommendation: Create app/routers/ for endpoint organization\n   - Impact: +15 points to score"
}
```

**Problems**:
- ❌ No specific context (File, Line, Code)
- ❌ No clear question
- ❌ Output doesn't start with verdict
- ❌ Generic recommendations instead of classification

### ✅ NEW FORMAT (False Positive Classifier)
```json
{
  "instruction": "Analyze this Bandit finding:\n\nFile: query.py\nLine: 42\nIssue: B608 SQL injection\nCode:\ncursor.execute(f'SELECT * FROM users WHERE id={user_id}')\n\nIs this a REAL ISSUE or FALSE POSITIVE?",
  "output": "REAL ISSUE: Direct string formatting in SQL query allows SQL injection. Recommendation: Use parameterized queries with placeholders."
}
```

**Improvements**:
- ✅ Specific context (File, Line, Code snippet)
- ✅ Clear classification question
- ✅ Verdict-first output format
- ✅ Concise reasoning and recommendation

## 📝 Format Requirements

### Instruction Format
Every instruction MUST include:
1. **Tool/Category**: "Analyze this [Bandit/dead-code/duplication/architecture/test coverage] finding:"
2. **Specific Context**:
   - File name and line number
   - Issue description or code snippet
   - Relevant metadata (decorators, similarity %, etc.)
3. **Clear Question**: "Is this a REAL ISSUE or FALSE POSITIVE?" (or similar)

### Output Format
Every output MUST:
1. **Start with Verdict** (in CAPS):
   - `REAL ISSUE`
   - `FALSE POSITIVE`
   - `ACCEPTABLE`
   - `REFACTOR NEEDED`
   - `WARNING`
2. **Provide Reasoning**: One sentence explaining why
3. **Optional Recommendation**: One sentence with specific action (if applicable)

### Example Templates

#### Security (Bandit)
```
Instruction:
Analyze this Bandit finding:

File: [filename]
Line: [line_number]
Issue: [bandit_code] [description]
Code:
[code_snippet]

Is this a REAL ISSUE or FALSE POSITIVE?

Output:
[VERDICT]: [reasoning]. [Optional: Recommendation: specific action].
```

#### Dead Code (Vulture)
```
Instruction:
Analyze this dead-code warning:

Function: [function_name]
File: [filename]
Line: [line_number]
[Optional: Decorator: @decorator_name]

Is this REAL dead code or FALSE POSITIVE?

Output:
[VERDICT]: [reasoning].
```

#### Duplication
```
Instruction:
Analyze this duplication finding:

Files: [file1], [file2]
Similarity: [percentage]%
Context: [description]

Should this be REFACTORED or is it ACCEPTABLE?

Output:
[VERDICT]: [reasoning]. [Optional: Recommendation: specific action].
```

#### Architecture
```
Instruction:
Analyze this architecture finding:

Framework: [FastAPI/Flask/Django]
Structure:
[project_structure]
Issue: [description]

Is this a REAL ISSUE or acceptable?

Output:
[VERDICT]: [reasoning]. [Optional: Recommendation: specific action].
```

#### Test Coverage
```
Instruction:
Analyze this test coverage report:

Files discovered: [count]
Executable tests: [count]
Coverage: [percentage]%
[Optional: Missing test types]

Is this a REAL ISSUE or acceptable?

Output:
[VERDICT]: [reasoning]. [Optional: Recommendation: specific action].
```

## 🎓 Training Examples Breakdown

### 1. Security (Bandit) - 20 examples

**Real Issues (10)**:
- SQL injection (string formatting)
- Hardcoded secrets
- Unsafe eval/exec
- Command injection (shell=True)
- Insecure hash functions (MD5 for passwords)
- Flask debug mode in production
- Insecure network binding
- XXE vulnerabilities
- Missing timeouts
- Insecure temp files

**False Positives (10)**:
- Parameterized queries
- Environment variables for secrets
- ast.literal_eval() usage
- Safe subprocess patterns
- MD5 for checksums (non-crypto)
- Debug mode in dev only
- Intentional 0.0.0.0 binding
- defusedxml usage
- Requests with timeout
- tempfile module usage

### 2. Dead Code (Vulture) - 20 examples

**Real Dead Code (10)**:
- Unused functions with no references
- Old implementations
- Legacy helpers
- Deprecated APIs
- Temporary debug code
- Experimental features
- Old backup logic

**False Positives (10)**:
- Decorator-registered functions (@register_handler, @app.route, @celery.task)
- Magic methods (__init__, __str__, __repr__, __eq__, __hash__)
- Framework signals (@receiver)
- Pydantic validators (@validator)

### 3. Duplication - 20 examples

**Refactor Needed (10)**:
- Duplicated CRUD logic
- Similar validation patterns
- Duplicated transaction processing
- Common parsing patterns
- Duplicated request handlers
- Similar string utilities
- Duplicated repository patterns
- Similar serialization logic
- Duplicated worker logic
- Similar filter patterns

**Acceptable (10)**:
- Test fixtures (setup/teardown)
- Environment configs (dev/prod)
- Test data factories
- Module imports (__init__.py)
- API version tests
- Middleware boilerplate
- Standalone scripts
- Constant definitions
- Documentation structure

### 4. Architecture - 20 examples

**Real Issues (15)**:
- Monolithic main.py (no routers)
- Circular imports
- Missing tests directory
- God object anti-pattern
- Single endpoints file
- Mutual imports
- User uploads in version control

**Acceptable (5)**:
- Proper router/model/schema separation
- Django app structure
- Clean layered architecture
- API versioning structure
- Proper dependency organization

### 5. Test Coverage - 20 examples

**Real Issues (7)**:
- No test files (0%)
- Very low coverage (<20%)
- Missing pytest-cov
- No testing infrastructure

**Warnings (3)**:
- Coverage 40-60%
- Missing integration tests

**Acceptable (10)**:
- Coverage >60% with proper organization
- Coverage >80% with all test types
- Good coverage for small codebases

## 🚀 Usage

### Validate Dataset
```bash
python validate_dataset.py data/audit_dataset_fixed.jsonl
```

Expected output:
```
✅ Dataset is valid!

📊 Statistics:
   - total_examples: 100
   - avg_instruction_length: [X] chars
   - avg_output_length: [X] chars

Status: PASS ✅
```

### Fine-tune on Kaggle
1. Upload `finetune/kaggle_finetune.ipynb`
2. Add dataset: `data/audit_dataset_fixed.jsonl`
3. Run notebook (~1 hour on T4 GPU)
4. Download model: `audit-classifier-v2`

### Use in Production
The fine-tuned model will:
- Analyze audit tool findings with specific context
- Classify as REAL ISSUE or FALSE POSITIVE
- Provide concise reasoning
- Give actionable recommendations only when needed

## 📋 Quality Checklist

✅ All examples have specific context (File, Line, Code)  
✅ All instructions end with clear classification question  
✅ All outputs start with verdict in CAPS  
✅ All outputs provide one-sentence reasoning  
✅ No emojis or formatting in outputs (plain text only)  
✅ Realistic filenames, line numbers, and code snippets  
✅ Balanced distribution (50/50 real vs false positive)  
✅ 100 total examples across 5 categories  
✅ JSONL format (one JSON object per line)  
✅ Passes validation script  

## 🎯 Expected Model Behavior

**Input**:
```
Analyze this Bandit finding:

File: auth.py
Line: 89
Issue: B303 Insecure hash function
Code:
password_hash = hashlib.md5(password.encode()).hexdigest()

Is this a REAL ISSUE or FALSE POSITIVE?
```

**Output**:
```
REAL ISSUE: MD5 is cryptographically broken for password hashing. Recommendation: Use bcrypt or argon2.
```

**Input**:
```
Analyze this dead-code warning:

Function: __init__
File: models.py
Line: 12

Is this REAL dead code or FALSE POSITIVE?
```

**Output**:
```
FALSE POSITIVE: Magic methods like __init__ are called automatically by Python runtime. This is not dead code.
```

## 📚 References

- Original dataset: `data/audit_dataset.jsonl` (deprecated)
- New dataset: `data/audit_dataset_fixed.jsonl` (v2.0)
- Validation script: `validate_dataset.py`
- Fine-tuning notebook: `finetune/kaggle_finetune.ipynb`

---

**Version**: 2.0  
**Date**: 2026-01-10  
**Total Examples**: 100  
**Format**: False Positive Classifier
