#!/usr/bin/env python
"""
Quick Test Script for PR Gatekeeper

This script demonstrates the PR Gatekeeper tool functionality.
Run this in a git repository with some changes to see it in action.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_fastmcp_server import audit_pr_changes, get_changed_files


def test_get_changed_files():
    """Test the get_changed_files helper function."""
    print("=" * 60)
    print("TEST 1: Get Changed Files")
    print("=" * 60)
    
    current_dir = Path.cwd()
    changed_files = get_changed_files(current_dir, "main")
    
    print(f"📁 Project: {current_dir}")
    print(f"🔍 Changed files: {len(changed_files)}")
    
    if changed_files:
        print("\n📝 Files:")
        for f in changed_files[:10]:
            rel_path = Path(f).relative_to(current_dir) if Path(f).is_absolute() else f
            print(f"  - {rel_path}")
        if len(changed_files) > 10:
            print(f"  ... and {len(changed_files) - 10} more")
    else:
        print("  ✅ No Python files changed")
    
    print()


def test_audit_pr_changes():
    """Test the full PR audit."""
    print("=" * 60)
    print("TEST 2: Full PR Audit")
    print("=" * 60)
    
    current_dir = str(Path.cwd())
    
    print(f"📁 Project: {current_dir}")
    print(f"🌿 Base branch: main")
    print(f"🧪 Run tests: True")
    print("\n⏳ Running audit...\n")
    
    try:
        result_json = audit_pr_changes(
            path=current_dir,
            base_branch="main",
            run_tests=True
        )
        
        result = json.loads(result_json)
        
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Status: {result.get('status')}")
        print(f"Recommendation: {result.get('recommendation')}")
        print(f"Score: {result.get('score')}/100")
        print(f"Changed Files: {result.get('changed_files_count')}")
        
        findings = result.get('findings', {})
        print("\n📊 Findings:")
        print(f"  🔒 Security Issues: {findings.get('security_issues', 0)}")
        print(f"  📋 Linting Issues: {findings.get('linting_issues', 0)}")
        print(f"  🧮 Complexity Issues: {findings.get('complexity_issues', 0)}")
        
        tests_passed = findings.get('tests_passed')
        if tests_passed is not None:
            print(f"  ✅ Tests: {'PASSED' if tests_passed else 'FAILED'}")
        else:
            print(f"  ✅ Tests: SKIPPED")
        
        print("\n" + "=" * 60)
        print("MARKDOWN REPORT")
        print("=" * 60)
        print(result.get('report', 'No report generated'))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n🚦 PR GATEKEEPER TEST SUITE\n")
    
    # Check if we're in a git repository
    git_dir = Path.cwd() / ".git"
    if not git_dir.exists():
        print("⚠️  Warning: Not in a git repository!")
        print("   This test works best in a git repo with changes.\n")
    
    test_get_changed_files()
    test_audit_pr_changes()
    
    print("\n✅ Tests complete!\n")


if __name__ == "__main__":
    main()
