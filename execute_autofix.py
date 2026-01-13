"""
Execute Auto-Fix with confirm=True
Creates backup, cleans junk, fixes style, and commits to a new branch.
"""
import sys
import shutil
import subprocess
import datetime
from pathlib import Path
import zipfile

project_path = Path(r'c:\Users\USER\.gemini\antigravity\scratch\project-audit\mcp-python-auditor')
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
branch_name = f"auto-fix-{timestamp}"

print("=" * 60)
print("🚀 AUTO-FIX EXECUTION MODE")
print("=" * 60)
print(f"Target: {project_path}")
print(f"Confirm: True (EXECUTING CHANGES)")
print("=" * 60)
print()

fixes_applied = []
errors = []

# 1. CREATE BACKUP
print("1️⃣  Creating backup...")
backup_name = f"auto_fix_backup_{timestamp}"
backup_zip = project_path / f"{backup_name}.zip"

try:
    def ignore_patterns(dir, files):
        return {f for f in files if f in {'.venv', 'venv', 'node_modules', '__pycache__', '.git'}}
    
    with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in project_path.rglob('*'):
            if file.is_file() and '.venv' not in str(file) and 'node_modules' not in str(file):
                try:
                    zf.write(file, file.relative_to(project_path))
                except:
                    pass
    
    print(f"   ✅ Backup created: {backup_zip.name}")
    fixes_applied.append(f"Backup: Created {backup_zip.name}")
except Exception as e:
    print(f"   ❌ Backup failed: {e}")
    errors.append(f"Backup failed: {e}")
    sys.exit(1)

print()

# 2. CLEANUP
print("2️⃣  Cleaning junk files...")
cleanup_patterns = ["__pycache__", ".pytest_cache", ".mypy_cache", "htmlcov", ".coverage"]
deleted_count = 0

for pattern in cleanup_patterns:
    for item in project_path.rglob(pattern):
        # Skip .venv to avoid breaking the environment
        if '.venv' in str(item) or 'venv' in str(item):
            continue
        
        try:
            if item.is_dir():
                shutil.rmtree(item)
                deleted_count += 1
            elif item.is_file():
                item.unlink()
                deleted_count += 1
        except Exception as e:
            pass

# Also delete .pyc files
for pyc in project_path.rglob('*.pyc'):
    if '.venv' not in str(pyc):
        try:
            pyc.unlink()
            deleted_count += 1
        except:
            pass

print(f"   ✅ Deleted {deleted_count} items")
fixes_applied.append(f"Cleanup: Deleted {deleted_count} cache directories and files")
print()

# 3. STYLE FIXES (RUFF)
print("3️⃣  Running Ruff code style fixes...")
try:
    # Run ruff check with --fix
    result1 = subprocess.run(
        [sys.executable, "-m", "ruff", "check", ".", "--fix"],
        cwd=str(project_path),
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL
    )
    
    # Run ruff format
    result2 = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "."],
        cwd=str(project_path),
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL
    )
    
    print(f"   ✅ Ruff fixes applied")
    fixes_applied.append("Code Style: Ran 'ruff check --fix' and 'ruff format'")
except Exception as e:
    print(f"   ⚠️  Ruff partially completed: {e}")
    errors.append(f"Ruff fix warning: {e}")

print()

# 4. GIT COMMIT
print("4️⃣  Creating Git branch and committing...")
try:
    git_kwargs = {"cwd": str(project_path), "capture_output": True, "timeout": 30, "stdin": subprocess.DEVNULL, "text": True}
    
    # Create new branch
    result = subprocess.run(["git", "checkout", "-b", branch_name], **git_kwargs)
    if result.returncode != 0:
        print(f"   ℹ️  Branch might already exist or git error: {result.stderr}")
    
    # Stage all changes
    subprocess.run(["git", "add", "."], **git_kwargs)
    
    # Commit
    commit_msg = f"Auto-fix: {', '.join(fixes_applied[:3])}"
    result = subprocess.run(["git", "commit", "-m", commit_msg], **git_kwargs)
    
    if result.returncode == 0:
        print(f"   ✅ Created branch '{branch_name}' and committed changes")
        fixes_applied.append(f"Git: Created branch '{branch_name}' with commit")
    else:
        print(f"   ℹ️  Git commit status: {result.stderr}")
        
except Exception as e:
    print(f"   ⚠️  Git operation warning: {e}")
    errors.append(f"Git commit warning: {e}")

print()

# 5. GENERATE LOG
print("5️⃣  Writing log file...")
try:
    log_file = project_path / "FIX_LOG.md"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n## Auto-Fix {timestamp}\n")
        for fix in fixes_applied:
            f.write(f"- {fix}\n")
        if errors:
            f.write(f"\n**Errors/Warnings:**\n")
            for err in errors:
                f.write(f"- {err}\n")
    print(f"   ✅ Log written to FIX_LOG.md")
except Exception as e:
    print(f"   ⚠️  Log write warning: {e}")

print()
print("=" * 60)
print("✅ AUTO-FIX COMPLETED")
print("=" * 60)
print(f"📦 Backup: {backup_zip.name}")
print(f"🌿 Branch: {branch_name}")
print(f"📝 Changes: {len(fixes_applied)} actions applied")
if errors:
    print(f"⚠️  Warnings: {len(errors)}")
print("=" * 60)
