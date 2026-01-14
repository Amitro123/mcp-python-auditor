# 🌐 Remote Repository Auditing Guide

## Overview

The **Remote Repository Auditing** feature allows you to audit any public Git repository without manual cloning. Perfect for quick security assessments of dependencies, open-source projects, or evaluating code quality before adoption.

## Key Features

### ⚡ Zero Setup
- No manual cloning required
- Automatic temporary directory management
- Automatic cleanup (even on failures)

### 🔒 Safe & Isolated
- Uses Python's `tempfile.TemporaryDirectory`
- Complete isolation from your filesystem
- Automatic cleanup prevents disk bloat

### 🚀 Fast
- Shallow clone (`--depth 1`) for speed
- Only downloads latest commit
- Typical audit: 30-60 seconds

### 📊 Complete Analysis
- Runs all 13 analysis tools
- Same comprehensive report as local audits
- Includes score, findings, and recommendations

## Usage

### Via MCP (Claude/AI)

```
"Audit the requests library from GitHub"
"Check the security of https://github.com/psf/requests.git"
"Run audit on https://github.com/user/repo.git branch develop"
```

### Via Python API

```python
from mcp_fastmcp_server import audit_remote_repo

# Audit main branch (default)
result = audit_remote_repo("https://github.com/psf/requests.git")

# Audit specific branch
result = audit_remote_repo(
    repo_url="https://github.com/user/repo.git",
    branch="develop"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo_url` | str | Required | Git repository URL (HTTP/HTTPS/SSH) |
| `branch` | str | `"main"` | Branch to audit |

### Supported URL Formats

✅ **HTTPS**: `https://github.com/user/repo.git`  
✅ **HTTP**: `http://github.com/user/repo.git`  
✅ **SSH**: `git@github.com:user/repo.git`

## Output

### JSON Structure

```json
{
  "status": "success",
  "repo_url": "https://github.com/psf/requests.git",
  "branch": "main",
  "score": 85,
  "duration": "45.3s",
  "files_analyzed": 127,
  "summary": {
    "security_issues": 0,
    "secrets_found": 0,
    "test_coverage": 92,
    "duplicates": 3,
    "dead_code": 5,
    "high_complexity": 2
  },
  "report": "# 🕵️‍♂️ Project Audit Report: requests\n..."
}
```

### Fields Explained

| Field | Description |
|-------|-------------|
| `status` | `"success"`, `"error"`, or `"warning"` |
| `repo_url` | Repository URL that was audited |
| `branch` | Branch that was audited |
| `score` | Quality score (0-100) |
| `duration` | Total audit time |
| `files_analyzed` | Number of Python files found |
| `summary` | Quick overview of findings |
| `report` | Full markdown audit report |

## How It Works

### Step-by-Step Process

1. **Validation**
   - Validates URL format
   - Checks for required protocols

2. **Temporary Directory**
   - Creates isolated temp directory
   - Prefix: `audit_remote_XXXXXX`

3. **Shallow Clone**
   ```bash
   git clone --depth 1 -b {branch} {repo_url} {temp_path}
   ```
   - Only downloads latest commit
   - Faster than full clone
   - Timeout: 5 minutes

4. **Python File Check**
   - Verifies Python files exist
   - Returns warning if none found

5. **Full Audit**
   - Runs all 13 analysis tools
   - Same as local `start_full_audit()`
   - Generates comprehensive report

6. **Cleanup**
   - Captures report before cleanup
   - Temp directory automatically deleted
   - Works even if audit fails

## Error Handling

### Repository Not Found

```json
{
  "status": "error",
  "error": "Repository not found: https://github.com/user/nonexistent.git",
  "suggestion": "Check the URL and ensure the repository exists"
}
```

### Private Repository

```json
{
  "status": "error",
  "error": "Authentication failed - repository may be private",
  "suggestion": "This tool currently supports public repositories only. For private repos, clone manually and use start_full_audit()"
}
```

### Branch Not Found

```json
{
  "status": "error",
  "error": "Branch 'develop' not found",
  "suggestion": "Check the branch name. Common branches: main, master, develop"
}
```

### Clone Timeout

```json
{
  "status": "error",
  "error": "Clone operation timed out (>5 minutes)",
  "suggestion": "Repository may be too large. Try cloning manually."
}
```

### Git Not Installed

```json
{
  "status": "error",
  "error": "Git is not installed or not in PATH",
  "suggestion": "Install Git: https://git-scm.com/downloads"
}
```

### No Python Files

```json
{
  "status": "warning",
  "message": "Repository cloned successfully but contains no Python files",
  "repo_url": "https://github.com/user/repo.git",
  "branch": "main"
}
```

## Use Cases

### 1. Dependency Security Assessment

Before adding a new dependency:

```python
# Check security of a library
audit_remote_repo("https://github.com/psf/requests.git")
```

**Decision Criteria**:
- Score > 80: ✅ Safe to use
- Security issues > 0: 🔴 Review carefully
- Test coverage < 50%: ⚠️ Risky

### 2. Open Source Evaluation

Evaluating a project for contribution:

```python
# Check code quality
audit_remote_repo("https://github.com/user/project.git")
```

**Look For**:
- High complexity: Harder to contribute
- Good test coverage: Easier to refactor
- Clean architecture: Well-maintained

### 3. Fork Comparison

Comparing forks before choosing:

```python
# Original
audit_remote_repo("https://github.com/original/repo.git")

# Fork
audit_remote_repo("https://github.com/fork/repo.git")
```

**Compare**:
- Scores
- Security issues
- Code quality metrics

### 4. Branch Quality Check

Before merging a feature branch:

```python
# Check feature branch
audit_remote_repo(
    "https://github.com/user/repo.git",
    branch="feature/new-api"
)
```

### 5. CI/CD Integration

Automated dependency audits:

```yaml
# GitHub Actions
- name: Audit Dependency
  run: |
    python -c "
    from mcp_fastmcp_server import audit_remote_repo
    import json
    result = json.loads(audit_remote_repo('${{ matrix.dep_url }}'))
    if result['score'] < 70:
        exit(1)
    "
```

## Performance

### Typical Timings

| Repository Size | Clone Time | Audit Time | Total |
|----------------|------------|------------|-------|
| Small (<100 files) | 5s | 15s | ~20s |
| Medium (100-500 files) | 10s | 30s | ~40s |
| Large (500-1000 files) | 20s | 45s | ~65s |
| Very Large (>1000 files) | 30s+ | 60s+ | ~90s+ |

### Optimization Tips

1. **Use Shallow Clone**: Already enabled (`--depth 1`)
2. **Audit Specific Branch**: Only clone the branch you need
3. **Local Cache**: For repeated audits, clone manually once

## Limitations

### Current Limitations

❌ **Private Repositories**: Not supported (requires authentication)  
❌ **Large Repositories**: May timeout (>5 minutes clone time)  
❌ **Non-Git Repositories**: Only Git is supported  
❌ **Submodules**: Not cloned (shallow clone limitation)

### Workarounds

**Private Repos**:
```bash
# Manual clone with auth
git clone https://github.com/user/private-repo.git
cd private-repo
# Then use local audit
python -c "from mcp_fastmcp_server import start_full_audit; start_full_audit('.')"
```

**Large Repos**:
```bash
# Manual shallow clone
git clone --depth 1 https://github.com/user/large-repo.git
cd large-repo
# Then use local audit
```

## Security Considerations

### What Gets Executed?

✅ **Safe**:
- Static analysis only
- No code execution
- Read-only operations

❌ **Not Executed**:
- Setup scripts
- Install commands
- Test suites (unless explicitly run)

### Temporary Directory

- **Location**: System temp directory
- **Permissions**: User-level access only
- **Cleanup**: Automatic, even on failure
- **Isolation**: Completely isolated from project files

### Network Security

- **HTTPS**: Encrypted communication
- **SSH**: Requires local SSH keys
- **No Credentials**: Tool doesn't store/transmit credentials

## Best Practices

### ✅ Do

- Audit dependencies before adding them
- Check security score before using libraries
- Compare forks to find best-maintained version
- Use for quick quality assessments

### ❌ Don't

- Audit extremely large repos (may timeout)
- Rely solely on score (read the report!)
- Audit private repos (not supported)
- Use for production deployments (audit locally)

## Troubleshooting

### "Clone operation timed out"

**Cause**: Repository is too large  
**Solution**: Clone manually and use `start_full_audit()`

### "Git is not installed"

**Cause**: Git not in PATH  
**Solution**: Install Git from https://git-scm.com/downloads

### "Repository not found"

**Cause**: URL is incorrect or repo is private  
**Solution**: Verify URL and ensure repo is public

### "No Python files found"

**Cause**: Repository doesn't contain Python code  
**Solution**: This tool is for Python projects only

## Examples

### Example 1: Popular Library

```python
result = audit_remote_repo("https://github.com/psf/requests.git")
print(f"Score: {result['score']}/100")
print(f"Security Issues: {result['summary']['security_issues']}")
```

### Example 2: Specific Branch

```python
result = audit_remote_repo(
    "https://github.com/django/django.git",
    branch="stable/4.2.x"
)
```

### Example 3: Multiple Repos

```python
repos = [
    "https://github.com/psf/requests.git",
    "https://github.com/kennethreitz/requests.git",
]

for repo in repos:
    result = audit_remote_repo(repo)
    print(f"{repo}: {result['score']}/100")
```

## Related Features

- **`start_full_audit()`** - Audit local directories
- **`audit_pr_changes()`** - Audit only changed files
- **`generate_full_report()`** - Generate comprehensive reports

## Version History

- **v2.4** (2026-01-14): Initial release

---

**Made with ❤️ for secure dependency management**

*"Trust, but verify - audit before you adopt."*
