#!/usr/bin/env python3
"""
Repository Cleanup Script
Removes unnecessary files while preserving essential project files.
"""
import os
import shutil
from pathlib import Path

# Root directory
ROOT = Path(__file__).parent

# Files to delete (exact matches)
FILES_TO_DELETE = [
    # Session summaries and temporary docs
    "AUDIT_ACCURACY_ANALYSIS.md",
    "BUG_FIX_SUMMARY.md",
    "CHANGES_TRACKER.md",
    "EFFICIENCY_TOOL_FIX.md",
    "GIT_NATIVE_IMPLEMENTATION.md",
    "HOW_TO_AVOID_INACCURATE_AUDITS.md",
    "IMPLEMENTATION_COMPLETE.md",
    "JINJA2_DEPLOYED.md",
    "JINJA2_DEPLOYMENT.md",
    "JINJA2_IMPLEMENTATION_COMPLETE.md",
    "JINJA2_MIGRATION_GUIDE.md",
    "PRODUCTION_READY.md",
    "README_UPDATES.md",
    "ROADMAP_AND_REMOTE_AUDIT_COMPLETE.md",
    "RUFF_MIGRATION.md",
    "RUFF_MIGRATION_COMPLETE.md",
    "SAFETY_FIRST_IMPLEMENTATION.md",
    "SELF_AUDIT_REPORT.md",
    "SERVER_FIXED.md",
    "SESSION_SUMMARY.md",
    "TEST_SUMMARY.md",
    
    # Backup files
    "self_audit.py.bak",
    "app/main.py.bak",
    "app/core/report_generator.py.bak",
    "app/tools/cleanup_tool.py.bak",
    
    # OLD files
    "app/tools/cleanup_tool.py.OLD",
    "app/tools/complexity_tool.py.OLD",
    "app/tools/efficiency_tool.py.OLD",
    "app/tools/security_tool.py.OLD",
    
    # Debug/test files
    "debug_audit.txt",
    "test_jinja2.py",
    "test_pr_gatekeeper.py",
    "demo_autofix.py",
    "new_analyzers.py",
    "dataset_templates.py",
    "verify_tools.py",
    "ci_runner.py",
    
    # Coverage files
    ".coverage",
    "uv.lock",
]

# Directories to delete
DIRS_TO_DELETE = [
    ".venv_broken",
    "htmlcov",
    "fresh-install-test",
    "backups",
]

# Cache directories (will be regenerated)
CACHE_DIRS = [
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
]

def delete_file(filepath: Path):
    """Delete a single file."""
    if filepath.exists():
        filepath.unlink()
        print(f"✅ Deleted file: {filepath.relative_to(ROOT)}")
        return True
    return False

def delete_directory(dirpath: Path):
    """Delete a directory and all its contents."""
    if dirpath.exists() and dirpath.is_dir():
        shutil.rmtree(dirpath)
        print(f"✅ Deleted directory: {dirpath.relative_to(ROOT)}")
        return True
    return False

def find_and_delete_cache(root: Path, cache_name: str):
    """Recursively find and delete cache directories."""
    count = 0
    for cache_dir in root.rglob(cache_name):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            print(f"✅ Deleted cache: {cache_dir.relative_to(ROOT)}")
            count += 1
    return count

def main():
    print("🧹 Starting repository cleanup...\n")
    
    deleted_files = 0
    deleted_dirs = 0
    
    # Delete specific files
    print("📄 Removing unnecessary files...")
    for file_path in FILES_TO_DELETE:
        full_path = ROOT / file_path
        if delete_file(full_path):
            deleted_files += 1
    
    # Delete specific directories
    print("\n📁 Removing unnecessary directories...")
    for dir_path in DIRS_TO_DELETE:
        full_path = ROOT / dir_path
        if delete_directory(full_path):
            deleted_dirs += 1
    
    # Delete cache directories
    print("\n🗑️  Removing cache directories...")
    for cache_name in CACHE_DIRS:
        count = find_and_delete_cache(ROOT, cache_name)
        deleted_dirs += count
    
    print(f"\n✨ Cleanup complete!")
    print(f"   📄 Files deleted: {deleted_files}")
    print(f"   📁 Directories deleted: {deleted_dirs}")
    print(f"\n💡 Remember to run 'git status' to review changes before committing.")

if __name__ == "__main__":
    main()
